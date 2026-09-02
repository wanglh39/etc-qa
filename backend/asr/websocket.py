import asyncio
import json
import time
from collections import deque

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from asr.service import _apply_corrections, _load_corrections
from asr.ws_helpers import (
    _CORRECTION_PATTERNS,
    _GREETING_PATTERNS,
    _PRONOUN_PATTERNS,
    _char_overlap_ratio,
    _do_diarize_segment,
    _do_query,
    _extract_channel,
    _get_recent_audio,
    _has_pronoun,
    _identify_speaker,
    _is_correction,
    _is_greeting,
)
from asr.ws_state import (
    ContextWindow,
    QueryAccumulator,
    QueryCache,
    SessionState,
    VADSilenceDetector,
)
from utils.config import get_config
from utils.logger import get_logger

logger = get_logger("asr.websocket")

router = APIRouter()


@router.websocket("/ws/asr/stream")
async def asr_stream(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket流式ASR连接建立")

    cfg = get_config().get("asr", {}).get("streaming", {})
    if not cfg.get("enabled", False):
        await websocket.send_json({"type": "error", "message": "流式ASR未启用"})
        await websocket.close()
        return

    auto_query = cfg.get("auto_query", False)
    min_query_length = cfg.get("min_query_length", 4)
    filter_greeting = cfg.get("filter_greeting", True)
    speaker_filter = cfg.get("speaker_filter", "")
    speaker_mode = cfg.get("speaker_mode", "none")
    channel_customer_side = cfg.get("channel_customer_side", "left")
    accumulate_mode = cfg.get("accumulate_mode", "sentence")
    accumulate_max = cfg.get("accumulate_max_sentences", 3)
    accumulate_silence = cfg.get("accumulate_silence_timeout", 2.0)
    dedup_enabled = cfg.get("dedup_enabled", True)
    dedup_similarity = cfg.get("dedup_similarity", 0.8)
    dedup_min_interval = cfg.get("dedup_min_interval", 5.0)
    correction_enabled = cfg.get("correction_enabled", True)
    coreference_enabled = cfg.get("coreference_enabled", True)
    context_window_size = cfg.get("context_window_size", 3)
    vad_trigger_enabled = cfg.get("vad_trigger_enabled", False)
    vad_silence_threshold = cfg.get("vad_silence_threshold", 2.0)
    diarize_trigger_enabled = cfg.get("diarize_trigger_enabled", False)
    diarize_audio_window = cfg.get("diarize_audio_window", 5.0)
    diarize_default_customer = cfg.get("diarize_default_customer", "SPEAKER_00")
    category_l1 = None
    text_corrections = _load_corrections()

    session = {"state": SessionState.IDLE}

    def _set_state(new_state):
        if session["state"] != new_state:
            logger.info(f"状态转换: {session['state'].value} -> {new_state.value}")
            session["state"] = new_state
            try:
                asyncio.run_coroutine_threadsafe(
                    websocket.send_json({"type": "state_change", "state": new_state.value}), loop
                )
            except Exception:
                pass

    from asr.streaming import StreamingCallback, get_streaming_service

    service = get_streaming_service()
    loop = asyncio.get_event_loop()

    def _emit(coro):
        asyncio.run_coroutine_threadsafe(coro, loop)

    final_texts = []
    audio_chunks: deque[bytes] = deque(maxlen=500)
    sample_rate = cfg.get("sample_rate", 16000)
    speaker_map: dict[str, str] = {}
    accumulator = QueryAccumulator(
        max_sentences=accumulate_max,
        silence_timeout=accumulate_silence,
    )
    query_cache = QueryCache(
        similarity_threshold=dedup_similarity,
        min_interval=dedup_min_interval,
    )
    context_window = ContextWindow(max_size=context_window_size)
    vad_detector = VADSilenceDetector(silence_threshold=vad_silence_threshold)
    if vad_trigger_enabled:
        await vad_detector._load_model()

    class WSCallback(StreamingCallback):
        def on_partial(self, text: str):
            try:
                asyncio.run_coroutine_threadsafe(websocket.send_json({"type": "partial", "text": text}), loop)
            except Exception:
                pass

        def on_final(self, text: str, is_end: bool = False):
            if text and text_corrections:
                text = _apply_corrections(text, text_corrections)
            if text:
                final_texts.append(text)
            try:
                _emit(
                    websocket.send_json(
                        {
                            "type": "final",
                            "text": text,
                            "is_end": is_end,
                            "full_text": "".join(final_texts),
                        }
                    )
                )

                if not auto_query or not text.strip():
                    return

                if correction_enabled and _is_correction(text):
                    popped = accumulator.pop_last() or (final_texts.pop() if len(final_texts) > 1 else None)
                    _set_state(SessionState.LISTENING)
                    _emit(
                        websocket.send_json(
                            {
                                "type": "corrected",
                                "correction_phrase": text,
                                "removed": popped,
                            }
                        )
                    )
                    return

                if filter_greeting and _is_greeting(text):
                    _emit(
                        websocket.send_json(
                            {
                                "type": "filtered",
                                "reason": "greeting",
                                "text": text,
                            }
                        )
                    )
                    return

                if len(text.strip()) < min_query_length:
                    _emit(
                        websocket.send_json(
                            {
                                "type": "filtered",
                                "reason": "too_short",
                                "text": text,
                                "min_length": min_query_length,
                            }
                        )
                    )
                    return

                query_text = text
                if coreference_enabled and _has_pronoun(text):
                    resolved = context_window.resolve_pronoun(text)
                    if resolved != text:
                        query_text = resolved
                        _emit(
                            websocket.send_json(
                                {
                                    "type": "coreference_resolved",
                                    "original": text,
                                    "resolved": resolved,
                                    "context": context_window.get_context(),
                                }
                            )
                        )

                if dedup_enabled and query_cache.should_skip(query_text):
                    _emit(
                        websocket.send_json(
                            {
                                "type": "filtered",
                                "reason": "duplicate",
                                "text": query_text,
                            }
                        )
                    )
                    return

                if speaker_filter and speaker_map:
                    speaker = _identify_speaker(text, final_texts, speaker_map)
                    if speaker and speaker != speaker_filter:
                        _emit(
                            websocket.send_json(
                                {
                                    "type": "filtered",
                                    "reason": "speaker_mismatch",
                                    "text": text,
                                    "speaker": speaker,
                                    "expected": speaker_filter,
                                }
                            )
                        )
                        return

                _set_state(SessionState.QUERY_READY)
                if accumulate_mode == "accumulate":
                    ready = accumulator.add(text)
                    if ready is not None:
                        combined = "".join(ready)
                        _emit(
                            _send_query_result(
                                websocket,
                                combined,
                                category_l1,
                                query_cache,
                                on_sent=lambda: _set_state(SessionState.CANDIDATES_SHOWN),
                            )
                        )
                        context_window.add(combined)
                    else:
                        _emit(
                            websocket.send_json(
                                {
                                    "type": "accumulating",
                                    "pending_count": accumulator.pending_count,
                                }
                            )
                        )
                else:
                    _emit(
                        _send_query_result(
                            websocket,
                            query_text,
                            category_l1,
                            query_cache,
                            on_sent=lambda: _set_state(SessionState.CANDIDATES_SHOWN),
                        )
                    )
                    context_window.add(text)

            except Exception:
                pass

        def on_error(self, error: str):
            try:
                _emit(websocket.send_json({"type": "error", "message": error}))
            except Exception:
                pass

    callback = WSCallback()

    try:
        service.start_stream(callback)
        await websocket.send_json(
            {
                "type": "ready",
                "mode": service.mode,
                "auto_query": auto_query,
                "state": session["state"].value,
                "filters": {
                    "min_query_length": min_query_length,
                    "filter_greeting": filter_greeting,
                    "speaker_filter": speaker_filter,
                    "speaker_mode": speaker_mode,
                    "accumulate_mode": accumulate_mode,
                    "dedup_enabled": dedup_enabled,
                    "correction_enabled": correction_enabled,
                    "coreference_enabled": coreference_enabled,
                    "vad_trigger_enabled": vad_trigger_enabled,
                    "diarize_trigger_enabled": diarize_trigger_enabled,
                },
            }
        )

        while True:
            msg = await websocket.receive()
            if "text" in msg:
                try:
                    ctrl = json.loads(msg["text"])
                    if ctrl.get("type") == "config":
                        category_l1 = ctrl.get("category_l1")
                        new_speaker = ctrl.get("speaker_filter")
                        if new_speaker is not None:
                            speaker_filter = new_speaker
                        continue
                    elif ctrl.get("type") == "flush":
                        ready = accumulator.flush()
                        if ready:
                            combined = "".join(ready)
                            await _send_query_result(websocket, combined, category_l1, query_cache)
                            context_window.add(combined)
                        continue
                    elif ctrl.get("type") == "label_speaker":
                        speaker = ctrl.get("speaker", "")
                        label = ctrl.get("label", "customer")
                        if speaker:
                            speaker_map[speaker] = label
                            await websocket.send_json(
                                {
                                    "type": "speaker_labeled",
                                    "speaker": speaker,
                                    "label": label,
                                }
                            )
                        continue
                    elif ctrl.get("type") == "clear_cache":
                        query_cache.clear()
                        await websocket.send_json({"type": "cache_cleared"})
                        continue
                    elif ctrl.get("type") == "clear_context":
                        context_window.clear()
                        await websocket.send_json({"type": "context_cleared"})
                        continue
                    elif ctrl.get("type") == "select_answer":
                        _set_state(SessionState.RESOLVED)
                        await websocket.send_json(
                            {
                                "type": "answer_selected",
                                "qa_id": ctrl.get("qa_id"),
                            }
                        )
                        continue
                    elif ctrl.get("type") == "reset":
                        _set_state(SessionState.IDLE)
                        context_window.clear()
                        query_cache.clear()
                        final_texts.clear()
                        await websocket.send_json({"type": "reset_done"})
                        continue
                except (json.JSONDecodeError, KeyError):
                    pass
            if "bytes" in msg:
                audio_data = msg["bytes"]

                if session["state"] in (SessionState.IDLE, SessionState.RESOLVED, SessionState.CANDIDATES_SHOWN):
                    _set_state(SessionState.LISTENING)

                if speaker_mode == "channel":
                    audio_data = _extract_channel(audio_data, channel_customer_side)

                audio_chunks.append(audio_data)
                service.send_audio(audio_data)

                if accumulate_mode == "accumulate" and not vad_trigger_enabled:
                    ready = accumulator.check_timeout()
                    if ready:
                        combined = "".join(ready)
                        _set_state(SessionState.QUERY_READY)
                        await _send_query_result(
                            websocket,
                            combined,
                            category_l1,
                            query_cache,
                            on_sent=lambda: _set_state(SessionState.CANDIDATES_SHOWN),
                        )
                        context_window.add(combined)

                if vad_trigger_enabled:
                    vad_detector.feed_audio(audio_data)
                    if vad_detector.check_silence() and accumulator.pending_count > 0:
                        should_query = True

                        if diarize_trigger_enabled and audio_chunks:
                            window_chunks = _get_recent_audio(audio_chunks, diarize_audio_window, sample_rate)
                            audio_bytes = b"".join(window_chunks)

                            segments = await loop.run_in_executor(None, _do_diarize_segment, audio_bytes, sample_rate)
                            if segments:
                                last_speaker = segments[-1]["speaker"]
                                if speaker_map:
                                    is_customer = speaker_map.get(last_speaker) == "customer"
                                else:
                                    is_customer = last_speaker == diarize_default_customer
                                if not is_customer:
                                    should_query = False
                                    await websocket.send_json(
                                        {
                                            "type": "filtered",
                                            "reason": "speaker_mismatch",
                                            "speaker": last_speaker,
                                        }
                                    )

                        ready = accumulator.flush()
                        if ready and should_query:
                            combined = "".join(ready)
                            await _send_query_result(websocket, combined, category_l1, query_cache)
                            context_window.add(combined)
                        vad_detector.reset()

    except WebSocketDisconnect:
        logger.info("WebSocket流式ASR连接断开")
    except Exception as e:
        logger.error(f"WebSocket流式ASR错误: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        service.stop_stream()


async def _send_query_result(
    websocket: WebSocket,
    text: str,
    category_l1: str | None = None,
    cache: QueryCache | None = None,
    on_sent=None,
):
    if cache is not None:
        cached = cache.get_recent(text)
        if cached is not None:
            try:
                await websocket.send_json(
                    {
                        "type": "query_result",
                        "query_text": text,
                        "data": cached,
                        "from_cache": True,
                    }
                )
            except Exception:
                pass
            if on_sent:
                on_sent()
            return

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _do_query, text, category_l1)
    if result is not None:
        if cache is not None:
            cache.record(text, result)
        try:
            await websocket.send_json(
                {
                    "type": "query_result",
                    "query_text": text,
                    "data": result,
                    "from_cache": False,
                }
            )
        except Exception:
            pass
    if on_sent:
        on_sent()
