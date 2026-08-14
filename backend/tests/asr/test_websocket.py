import asyncio
import json
import sys
import time
from unittest.mock import AsyncMock, MagicMock, patch

if asyncio.get_event_loop_policy().__class__.__name__ != "WindowsSelectorEventLoopPolicy":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import pytest

pytestmark = pytest.mark.filterwarnings(
    "ignore::pytest.PytestUnraisableExceptionWarning"
)

from fastapi import WebSocketDisconnect

from asr.streaming import StreamingCallback
from asr.service import _apply_corrections
from asr.websocket import (
    ContextWindow,
    QueryAccumulator,
    QueryCache,
    SessionState,
    VADSilenceDetector,
    _do_query,
    _has_pronoun,
    _is_correction,
    _is_greeting,
    _send_query_result,
    asr_stream,
)

_shared_loop = None


def _run_async(coro):
    global _shared_loop
    if _shared_loop is None or _shared_loop.is_closed():
        _shared_loop = asyncio.new_event_loop()
    return _shared_loop.run_until_complete(coro)


def _get_loop():
    global _shared_loop
    if _shared_loop is None or _shared_loop.is_closed():
        _shared_loop = asyncio.new_event_loop()
    return _shared_loop


def _clean_pending(loop):
    pending = [t for t in asyncio.all_tasks(loop) if not t.done()]
    for t in pending:
        t.cancel()
    if pending:
        try:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception:
            pass


class TestWebSocketControlMessage:
    def test_config_with_category(self):
        ctrl = json.loads('{"type": "config", "category_l1": "ETC业务"}')
        assert ctrl["type"] == "config"
        assert ctrl["category_l1"] == "ETC业务"

    def test_config_with_speaker_filter(self):
        ctrl = json.loads('{"type": "config", "speaker_filter": "SPEAKER_00"}')
        assert ctrl["speaker_filter"] == "SPEAKER_00"

    def test_flush_command(self):
        ctrl = json.loads('{"type": "flush"}')
        assert ctrl["type"] == "flush"

    def test_label_speaker_command(self):
        ctrl = json.loads('{"type": "label_speaker", "speaker": "SPEAKER_01", "label": "customer"}')
        assert ctrl["speaker"] == "SPEAKER_01"
        assert ctrl["label"] == "customer"

    def test_clear_cache_command(self):
        ctrl = json.loads('{"type": "clear_cache"}')
        assert ctrl["type"] == "clear_cache"

    def test_clear_context_command(self):
        ctrl = json.loads('{"type": "clear_context"}')
        assert ctrl["type"] == "clear_context"


class TestWSCallback:
    def test_on_final_collects_text(self):
        collected = []

        class TestCallback(StreamingCallback):
            def on_partial(self, text: str):
                pass

            def on_final(self, text: str, is_end: bool = False):
                if text:
                    collected.append(text)

            def on_error(self, error: str):
                pass

        cb = TestCallback()
        cb.on_final("第一句")
        cb.on_final("第二句")
        assert collected == ["第一句", "第二句"]

    def test_on_final_empty_skipped(self):
        collected = []

        class TestCallback(StreamingCallback):
            def on_partial(self, text: str):
                pass

            def on_final(self, text: str, is_end: bool = False):
                if text:
                    collected.append(text)

            def on_error(self, error: str):
                pass

        cb = TestCallback()
        cb.on_final("")
        cb.on_final("有内容")
        assert collected == ["有内容"]

    def test_on_error(self):
        errors = []

        class TestCallback(StreamingCallback):
            def on_partial(self, text: str):
                pass

            def on_final(self, text: str, is_end: bool = False):
                pass

            def on_error(self, error: str):
                errors.append(error)

        cb = TestCallback()
        cb.on_error("连接超时")
        assert errors == ["连接超时"]


class TestFilterPipeline:
    def test_greeting_then_query(self):
        texts = ["你好", "ETC怎么办理"]
        results = []
        cache = QueryCache(similarity_threshold=0.8, min_interval=5.0)
        for t in texts:
            if _is_greeting(t):
                results.append(("filtered", "greeting"))
            elif cache.should_skip(t):
                results.append(("filtered", "duplicate"))
            else:
                cache.record(t, {"q": t})
                results.append(("query", t))
        assert results == [
            ("filtered", "greeting"),
            ("query", "ETC怎么办理"),
        ]

    def test_duplicate_filtered(self):
        texts = ["ETC扣费有问题", "ETC扣费有问题", "蓝牙连接不上"]
        results = []
        cache = QueryCache(similarity_threshold=0.8, min_interval=5.0)
        for t in texts:
            if _is_greeting(t):
                results.append(("filtered", "greeting"))
            elif cache.should_skip(t):
                results.append(("filtered", "duplicate"))
            else:
                cache.record(t, {"q": t})
                results.append(("query", t))
        assert results == [
            ("query", "ETC扣费有问题"),
            ("filtered", "duplicate"),
            ("query", "蓝牙连接不上"),
        ]

    def test_coreference_resolution(self):
        ctx = ContextWindow(max_size=3)
        ctx.add("ETC扣费有问题")
        text = "那个怎么退款"
        assert _has_pronoun(text) is True
        resolved = ctx.resolve_pronoun(text)
        assert "ETC扣费有问题" in resolved

    def test_vad_triggers_flush(self):
        acc = QueryAccumulator(max_sentences=5, silence_timeout=10.0)
        detector = VADSilenceDetector(silence_threshold=0.05)
        acc.add("ETC扣费有问题")
        time.sleep(0.06)
        assert detector.check_silence() is True
        ready = acc.flush()
        assert ready == ["ETC扣费有问题"]

    def test_accumulate_mode(self):
        acc = QueryAccumulator(max_sentences=2, silence_timeout=2.0)
        texts = ["ETC怎么办理", "扣费有问题"]
        queries = []
        for t in texts:
            ready = acc.add(t)
            if ready is not None:
                queries.append("".join(ready))
        assert queries == ["ETC怎么办理扣费有问题"]


class TestDiarizeTriggerLogic:
    def test_customer_speaker_triggers_query(self):
        segments = [{"start": 0.0, "end": 1.0, "speaker": "SPEAKER_00"}]
        speaker_map = {"SPEAKER_00": "customer"}
        last_speaker = segments[-1]["speaker"]
        is_customer = speaker_map.get(last_speaker) == "customer"
        assert is_customer is True

    def test_agent_speaker_skips_query(self):
        segments = [{"start": 0.0, "end": 1.0, "speaker": "SPEAKER_01"}]
        speaker_map = {"SPEAKER_00": "customer", "SPEAKER_01": "agent"}
        last_speaker = segments[-1]["speaker"]
        is_customer = speaker_map.get(last_speaker) == "customer"
        assert is_customer is False

    def test_no_label_map_uses_default(self):
        segments = [{"start": 0.0, "end": 1.0, "speaker": "SPEAKER_00"}]
        speaker_map = {}
        last_speaker = segments[-1]["speaker"]
        if speaker_map:
            is_customer = speaker_map.get(last_speaker) == "customer"
        else:
            is_customer = last_speaker == "SPEAKER_00"
        assert is_customer is True

    def test_no_label_map_default_mismatch(self):
        segments = [{"start": 0.0, "end": 1.0, "speaker": "SPEAKER_01"}]
        speaker_map = {}
        last_speaker = segments[-1]["speaker"]
        if speaker_map:
            is_customer = speaker_map.get(last_speaker) == "customer"
        else:
            is_customer = last_speaker == "SPEAKER_00"
        assert is_customer is False

    def test_empty_segments_does_not_filter(self):
        segments = []
        assert not segments


class TestSendQueryResult:
    def test_cache_hit_sends_cached(self):
        import asyncio
        mock_ws = AsyncMock()
        cache = QueryCache(similarity_threshold=0.8, min_interval=5.0)
        cache.record("ETC扣费", {"confidence": "high"})
        with patch("asr.websocket._do_query", return_value=None):
            asyncio.run(_send_query_result(mock_ws, "ETC扣费", cache=cache))
        mock_ws.send_json.assert_called_once()
        sent = mock_ws.send_json.call_args[0][0]
        assert sent["from_cache"] is True

    def test_no_cache_calls_query(self):
        import asyncio
        mock_ws = AsyncMock()
        with patch("asr.websocket._do_query", return_value={"query": "ETC扣费"}):
            asyncio.run(_send_query_result(mock_ws, "ETC扣费"))
        assert mock_ws.send_json.call_count >= 1

    def test_service_none_no_send(self):
        import asyncio
        mock_ws = AsyncMock()
        with patch("asr.websocket._do_query", return_value=None):
            asyncio.run(_send_query_result(mock_ws, "ETC扣费"))
        mock_ws.send_json.assert_not_called()


class TestStateMachine:
    def test_send_query_result_invokes_on_sent_callback(self):
        mock_ws = AsyncMock()
        callback_called = []

        def on_sent():
            callback_called.append(True)

        with patch("asr.websocket._do_query", return_value={"query": "ETC扣费"}):
            _run_async(_send_query_result(mock_ws, "ETC扣费", on_sent=on_sent))
        assert callback_called == [True]

    def test_send_query_result_invokes_on_sent_on_cache_hit(self):
        mock_ws = AsyncMock()
        cache = QueryCache(similarity_threshold=0.8, min_interval=5.0)
        cache.record("ETC扣费", {"confidence": "high"})
        callback_called = []

        def on_sent():
            callback_called.append(True)

        with patch("asr.websocket._do_query", return_value=None):
            _run_async(_send_query_result(mock_ws, "ETC扣费", cache=cache, on_sent=on_sent))
        assert callback_called == [True]

    def test_send_query_result_no_on_sent_does_not_error(self):
        mock_ws = AsyncMock()
        with patch("asr.websocket._do_query", return_value={"query": "ETC扣费"}):
            _run_async(_send_query_result(mock_ws, "ETC扣费", on_sent=None))
        assert mock_ws.send_json.call_count >= 1

    def test_audio_transitions_to_listening_from_idle(self):
        session = {"state": SessionState.IDLE}
        if session["state"] in (SessionState.IDLE, SessionState.RESOLVED, SessionState.CANDIDATES_SHOWN):
            session["state"] = SessionState.LISTENING
        assert session["state"] == SessionState.LISTENING

    def test_audio_transitions_to_listening_from_resolved(self):
        session = {"state": SessionState.RESOLVED}
        if session["state"] in (SessionState.IDLE, SessionState.RESOLVED, SessionState.CANDIDATES_SHOWN):
            session["state"] = SessionState.LISTENING
        assert session["state"] == SessionState.LISTENING

    def test_audio_transitions_to_listening_from_candidates_shown(self):
        session = {"state": SessionState.CANDIDATES_SHOWN}
        if session["state"] in (SessionState.IDLE, SessionState.RESOLVED, SessionState.CANDIDATES_SHOWN):
            session["state"] = SessionState.LISTENING
        assert session["state"] == SessionState.LISTENING

    def test_audio_does_not_transition_from_listening(self):
        session = {"state": SessionState.LISTENING}
        if session["state"] in (SessionState.IDLE, SessionState.RESOLVED, SessionState.CANDIDATES_SHOWN):
            session["state"] = SessionState.LISTENING
        assert session["state"] == SessionState.LISTENING

    def test_audio_does_not_transition_from_query_ready(self):
        session = {"state": SessionState.QUERY_READY}
        if session["state"] in (SessionState.IDLE, SessionState.RESOLVED, SessionState.CANDIDATES_SHOWN):
            session["state"] = SessionState.LISTENING
        assert session["state"] == SessionState.QUERY_READY

    def test_correction_transitions_to_listening(self):
        session = {"state": SessionState.QUERY_READY}
        if _is_correction("不对"):
            session["state"] = SessionState.LISTENING
        assert session["state"] == SessionState.LISTENING

    def test_valid_query_transitions_to_query_ready(self):
        session = {"state": SessionState.LISTENING}
        text = "ETC扣费异常怎么处理"
        if not _is_greeting(text) and len(text.strip()) >= 4:
            session["state"] = SessionState.QUERY_READY
        assert session["state"] == SessionState.QUERY_READY

    def test_query_result_callback_transitions_to_candidates_shown(self):
        session = {"state": SessionState.QUERY_READY}

        def on_sent():
            session["state"] = SessionState.CANDIDATES_SHOWN

        on_sent()
        assert session["state"] == SessionState.CANDIDATES_SHOWN

    def test_select_answer_transitions_to_resolved(self):
        session = {"state": SessionState.CANDIDATES_SHOWN}
        session["state"] = SessionState.RESOLVED
        assert session["state"] == SessionState.RESOLVED

    def test_reset_transitions_to_idle(self):
        session = {"state": SessionState.RESOLVED}
        session["state"] = SessionState.IDLE
        assert session["state"] == SessionState.IDLE

    def test_set_state_only_changes_on_difference(self):
        session = {"state": SessionState.IDLE}
        changes = []

        def _set_state(new_state):
            if session["state"] != new_state:
                session["state"] = new_state
                changes.append(new_state)

        _set_state(SessionState.IDLE)
        assert changes == []
        _set_state(SessionState.LISTENING)
        assert changes == [SessionState.LISTENING]
        _set_state(SessionState.LISTENING)
        assert changes == [SessionState.LISTENING]
        _set_state(SessionState.QUERY_READY)
        assert changes == [SessionState.LISTENING, SessionState.QUERY_READY]


class TestControlMessageUpdate:
    def test_select_answer_message_parsed(self):
        ctrl = json.loads('{"type": "select_answer", "qa_id": 42}')
        assert ctrl["type"] == "select_answer"
        assert ctrl["qa_id"] == 42

    def test_select_answer_message_without_qa_id(self):
        ctrl = json.loads('{"type": "select_answer"}')
        assert ctrl["type"] == "select_answer"
        assert ctrl.get("qa_id") is None

    def test_reset_message_parsed(self):
        ctrl = json.loads('{"type": "reset"}')
        assert ctrl["type"] == "reset"

    def test_select_answer_response_shape(self):
        response = {"type": "answer_selected", "qa_id": 42}
        assert response["type"] == "answer_selected"
        assert response["qa_id"] == 42

    def test_reset_response_shape(self):
        response = {"type": "reset_done"}
        assert response["type"] == "reset_done"

    def test_ready_message_includes_state(self):
        response = {
            "type": "ready",
            "mode": "local",
            "auto_query": True,
            "state": SessionState.IDLE.value,
        }
        assert response["state"] == "idle"

    def test_state_change_message_shape(self):
        response = {"type": "state_change", "state": SessionState.LISTENING.value}
        assert response["type"] == "state_change"
        assert response["state"] == "listening"


class TestOnFinalCorrections:
    def test_corrections_applied_when_text_and_corrections_present(self):
        text = "E T C扣费异常"
        text_corrections = {"E T C": "ETC"}
        if text and text_corrections:
            text = _apply_corrections(text, text_corrections)
        assert text == "ETC扣费异常"

    def test_corrections_not_applied_when_corrections_empty(self):
        text = "E T C扣费异常"
        text_corrections = {}
        if text and text_corrections:
            text = _apply_corrections(text, text_corrections)
        assert text == "E T C扣费异常"

    def test_corrections_not_applied_when_text_empty(self):
        text = ""
        text_corrections = {"E T C": "ETC"}
        if text and text_corrections:
            text = _apply_corrections(text, text_corrections)
        assert text == ""

    def test_corrections_applied_before_greeting_filter(self):
        text = "为你好"
        text_corrections = {"为你好": "你好"}
        if text and text_corrections:
            text = _apply_corrections(text, text_corrections)
        assert _is_greeting(text) is True

    def test_corrections_applied_before_query(self):
        text = "O B U设备怎么激活"
        text_corrections = {"O B U": "OBU"}
        if text and text_corrections:
            text = _apply_corrections(text, text_corrections)
        assert text == "OBU设备怎么激活"
        assert _is_greeting(text) is False

    def test_corrections_applied_multiple_rules(self):
        text = "E T C扣费和O B U设备"
        text_corrections = {"E T C": "ETC", "O B U": "OBU"}
        if text and text_corrections:
            text = _apply_corrections(text, text_corrections)
        assert text == "ETC扣费和OBU设备"

    def test_corrections_preserve_text_when_no_match(self):
        text = "蓝牙连接不上"
        text_corrections = {"E T C": "ETC"}
        if text and text_corrections:
            text = _apply_corrections(text, text_corrections)
        assert text == "蓝牙连接不上"

    def test_corrections_applied_then_not_greeting(self):
        text = "e t c怎么办理"
        text_corrections = {"e t c": "ETC"}
        if text and text_corrections:
            text = _apply_corrections(text, text_corrections)
        assert text == "ETC怎么办理"
        assert _is_greeting(text) is False
        assert len(text.strip()) >= 4


class MockWebSocket:
    def __init__(self):
        self.sent = []
        self.receive_queue = []
        self.closed = False
        self.accepted = False

    async def accept(self):
        self.accepted = True

    async def send_json(self, data):
        self.sent.append(data)

    async def close(self):
        self.closed = True

    async def receive(self):
        await asyncio.sleep(0)
        if self.receive_queue:
            item = self.receive_queue.pop(0)
            if isinstance(item, Exception):
                raise item
            return item
        raise WebSocketDisconnect()


def _make_cfg(**overrides):
    cfg = {"asr": {"streaming": {"enabled": True, "mode": "local", "auto_query": False}}}
    cfg["asr"]["streaming"].update(overrides)
    return cfg


def _run(cfg, messages):
    ws = MockWebSocket()
    ws.receive_queue = list(messages) + [WebSocketDisconnect()]
    with patch("asr.websocket.get_config", return_value=cfg):
        with patch("asr.streaming.get_streaming_service") as mock_get:
            mock_svc = MagicMock()
            mock_svc.mode = "local"
            mock_get.return_value = mock_svc
            loop = _get_loop()
            try:
                loop.run_until_complete(asr_stream(ws))
            except Exception:
                pass
            _clean_pending(loop)
    return ws


class TestWSDisabled:
    def test_disabled_returns_error(self):
        ws = MockWebSocket()
        with patch("asr.websocket.get_config", return_value={"asr": {"streaming": {"enabled": False}}}):
            loop = _get_loop()
            try:
                loop.run_until_complete(asr_stream(ws))
            except Exception:
                pass
                _clean_pending(loop)

        assert ws.sent[0]["type"] == "error"


class TestWSConnect:
    def test_ready_message(self):
        ws = _run(_make_cfg(), [])
        assert ws.sent[0]["type"] == "ready"
        assert ws.sent[0]["mode"] == "local"


class TestWSConfig:
    def test_config_message(self):
        _run(_make_cfg(), [{"text": '{"type": "config", "category_l1": "ETC业务"}'}])


class TestWSFlush:
    def test_flush_empty(self):
        _run(_make_cfg(), [{"text": '{"type": "flush"}'}])


class TestWSLabelSpeaker:
    def test_label_speaker(self):
        ws = _run(_make_cfg(), [{"text": '{"type": "label_speaker", "speaker": "SPEAKER_00", "label": "customer"}'}])
        assert ws.sent[1]["type"] == "speaker_labeled"


class TestWSClearCache:
    def test_clear_cache(self):
        ws = _run(_make_cfg(), [{"text": '{"type": "clear_cache"}'}])
        assert ws.sent[1]["type"] == "cache_cleared"


class TestWSClearContext:
    def test_clear_context(self):
        ws = _run(_make_cfg(), [{"text": '{"type": "clear_context"}'}])
        assert ws.sent[1]["type"] == "context_cleared"


class TestWSAudio:
    def test_receive_bytes(self):
        _run(_make_cfg(), [{"bytes": b"\x00" * 3200}])


class TestWSChannelMode:
    def test_channel_extract(self):
        import numpy as np
        stereo = np.array([[100, 200], [300, 400]], dtype=np.int16)
        _run(_make_cfg(speaker_mode="channel"), [{"bytes": stereo.tobytes()}])


class TestWSInvalidJson:
    def test_invalid_json(self):
        _run(_make_cfg(), [{"text": "not valid json"}])


class TestWSVAD:
    def test_vad_enabled(self):
        ws = MockWebSocket()
        ws.receive_queue = [{"bytes": b"\x00" * 3200}, WebSocketDisconnect()]
        with patch("asr.websocket.get_config", return_value=_make_cfg(vad_trigger_enabled=True, vad_silence_threshold=0.05)):
            with patch("asr.streaming.get_streaming_service") as mock_get:
                with patch("asr.websocket.VADSilenceDetector._load_model", return_value=None):
                    with patch("asr.websocket.VADSilenceDetector.feed_audio"):
                        mock_svc = MagicMock()
                        mock_svc.mode = "local"
                        mock_get.return_value = mock_svc
                        loop = _get_loop()
                        try:
                            loop.run_until_complete(asr_stream(ws))
                        except Exception:
                            pass
                            _clean_pending(loop)


class TestWSMultiple:
    def test_multi_messages(self):
        _run(_make_cfg(), [
            {"text": '{"type": "config", "category_l1": "ETC业务"}'},
            {"bytes": b"\x00" * 3200},
            {"text": '{"type": "clear_cache"}'},
            {"text": '{"type": "clear_context"}'},
        ])


def _run_callback(cfg_overrides, final_texts=None, partial_texts=None, error_text=None,
                  drain=0.05):
    ws = MockWebSocket()
    cfg = _make_cfg(auto_query=True, **cfg_overrides)
    captured = {}

    def start_stream(cb):
        captured["cb"] = cb

    finals = list(final_texts or [])
    partials = list(partial_texts or [])

    def send_audio(data):
        cb = captured.get("cb")
        if not cb:
            return
        if partials:
            cb.on_partial(partials.pop(0))
        if finals:
            cb.on_final(finals.pop(0))
        if error_text:
            cb.on_error(error_text)

    n = max(1, len(finals), len(partials), 1 if error_text else 0)
    messages = [{"bytes": b"\x00" * 3200} for _ in range(n)]

    with patch("asr.websocket.get_config", return_value=cfg):
        with patch("asr.streaming.get_streaming_service") as mock_get:
            with patch("asr.websocket._do_query", return_value={"answer": "测试"}):
                mock_svc = MagicMock()
                mock_svc.mode = "local"
                mock_svc.start_stream = start_stream
                mock_svc.send_audio = send_audio
                mock_get.return_value = mock_svc
                ws.receive_queue = messages + [WebSocketDisconnect()]
                loop = _get_loop()
                try:
                    loop.run_until_complete(asr_stream(ws))
                    if drain:
                        loop.run_until_complete(asyncio.sleep(drain))
                except Exception:
                    pass
                _clean_pending(loop)
    return ws


class TestWSCallbackPartial:
    def test_on_partial(self):
        ws = _run_callback({}, partial_texts=["你好"])
        types = [m["type"] for m in ws.sent]
        assert "partial" in types


class TestWSCallbackError:
    def test_on_error(self):
        ws = _run_callback({}, error_text="ASR错误")
        types = [m["type"] for m in ws.sent]
        assert "error" in types


class TestWSCallbackFinalNormal:
    def test_final_with_query(self):
        ws = _run_callback({}, final_texts=["ETC扣费怎么查询"])
        types = [m["type"] for m in ws.sent]
        assert "final" in types
        assert "query_result" in types


class TestWSCallbackFinalGreeting:
    def test_final_greeting_filtered(self):
        ws = _run_callback({}, final_texts=["你好"])
        types = [m["type"] for m in ws.sent]
        assert "final" in types
        assert "filtered" in types


class TestWSCallbackFinalTooShort:
    def test_final_too_short(self):
        ws = _run_callback({}, final_texts=["ETC"])
        types = [m["type"] for m in ws.sent]
        assert "filtered" in types
        filtered_msgs = [m for m in ws.sent if m.get("type") == "filtered"]
        assert any(m.get("reason") == "too_short" for m in filtered_msgs)


class TestWSCallbackFinalCorrection:
    def test_final_correction(self):
        ws = _run_callback({}, final_texts=["ETC扣费"], )
        ws2 = _run_callback({}, final_texts=["不对"])
        types2 = [m["type"] for m in ws2.sent]
        assert "corrected" in types2


class TestWSCallbackFinalNoAutoQuery:
    def test_final_no_auto_query(self):
        ws = MockWebSocket()
        cfg = _make_cfg(auto_query=False)
        captured = {}

        def start_stream(cb):
            captured["cb"] = cb

        def send_audio(data):
            cb = captured.get("cb")
            if cb:
                cb.on_final("ETC扣费查询")

        with patch("asr.websocket.get_config", return_value=cfg):
            with patch("asr.streaming.get_streaming_service") as mock_get:
                mock_svc = MagicMock()
                mock_svc.mode = "local"
                mock_svc.start_stream = start_stream
                mock_svc.send_audio = send_audio
                mock_get.return_value = mock_svc
                ws.receive_queue = [{"bytes": b"\x00" * 3200}, WebSocketDisconnect()]
                loop = _get_loop()
                try:
                    loop.run_until_complete(asr_stream(ws))
                    loop.run_until_complete(asyncio.sleep(0.05))
                except Exception:
                    pass
                    _clean_pending(loop)
        types = [m["type"] for m in ws.sent]
        assert "final" in types
        assert "query_result" not in types


class TestWSCallbackFinalDedup:
    def test_final_dedup(self):
        ws = _run_callback({}, final_texts=["ETC扣费查询", "ETC扣费查询"])
        types = [m["type"] for m in ws.sent]
        assert types.count("final") == 2


class TestWSCallbackFinalCoreference:
    def test_final_coreference(self):
        ws = _run_callback({}, final_texts=["ETC设备", "它怎么办理"])
        types = [m["type"] for m in ws.sent]
        assert "coreference_resolved" in types


class TestWSCallbackFinalAccumulate:
    def test_final_accumulate(self):
        ws = _run_callback({"accumulate_mode": "accumulate", "accumulate_max_sentences": 2},
                           final_texts=["ETC扣费", "OBU设备"])
        types = [m["type"] for m in ws.sent]
        assert "query_result" in types


class TestWSErrorHandler:
    def test_service_start_error(self):
        ws = MockWebSocket()
        cfg = _make_cfg()
        with patch("asr.websocket.get_config", return_value=cfg):
            with patch("asr.streaming.get_streaming_service") as mock_get:
                mock_svc = MagicMock()
                mock_svc.mode = "local"
                mock_svc.start_stream = MagicMock(side_effect=RuntimeError("启动失败"))
                mock_get.return_value = mock_svc
                ws.receive_queue = [WebSocketDisconnect()]
                loop = _get_loop()
                try:
                    loop.run_until_complete(asr_stream(ws))
                except Exception:
                    pass
                    _clean_pending(loop)
        types = [m["type"] for m in ws.sent]
        assert "error" in types


class TestWSFlushWithData:
    def test_flush_after_accumulate(self):
        ws = MockWebSocket()
        cfg = _make_cfg(accumulate_mode="accumulate", auto_query=True)
        captured = {}

        def start_stream(cb):
            captured["cb"] = cb

        def send_audio(data):
            cb = captured.get("cb")
            if cb:
                cb.on_final("ETC扣费查询")

        with patch("asr.websocket.get_config", return_value=cfg):
            with patch("asr.streaming.get_streaming_service") as mock_get:
                with patch("asr.websocket._do_query", return_value={"answer": "测试"}):
                    mock_svc = MagicMock()
                    mock_svc.mode = "local"
                    mock_svc.start_stream = start_stream
                    mock_svc.send_audio = send_audio
                    mock_get.return_value = mock_svc
                    ws.receive_queue = [
                        {"bytes": b"\x00" * 3200},
                        {"text": '{"type": "flush"}'},
                        WebSocketDisconnect(),
                    ]
                    loop = _get_loop()
                    try:
                        loop.run_until_complete(asr_stream(ws))
                        loop.run_until_complete(asyncio.sleep(0.05))
                    except Exception:
                        pass
                        _clean_pending(loop)
        types = [m["type"] for m in ws.sent]
        assert "query_result" in types


class TestWSConfigSpeakerFilter:
    def test_config_with_speaker_filter(self):
        ws = _run(_make_cfg(), [{"text": '{"type": "config", "category_l1": "ETC业务", "speaker_filter": "SPEAKER_01"}'}])
        assert ws.sent[0]["type"] == "ready"


class TestWSCallbackSpeakerMismatch:
    def test_speaker_mismatch_filter(self):
        ws = MockWebSocket()
        cfg = _make_cfg(auto_query=True, speaker_filter="SPEAKER_01")
        captured = {}

        def start_stream(cb):
            captured["cb"] = cb

        def send_audio(data):
            cb = captured.get("cb")
            if cb:
                cb.on_final("ETC扣费查询")

        with patch("asr.websocket.get_config", return_value=cfg):
            with patch("asr.streaming.get_streaming_service") as mock_get:
                with patch("asr.websocket._do_query", return_value={"answer": "测试"}):
                    mock_svc = MagicMock()
                    mock_svc.mode = "local"
                    mock_svc.start_stream = start_stream
                    mock_svc.send_audio = send_audio
                    mock_get.return_value = mock_svc
                    ws.receive_queue = [
                        {"text": '{"type": "label_speaker", "speaker": "SPEAKER_00", "label": "customer"}'},
                        {"bytes": b"\x00" * 3200},
                        WebSocketDisconnect(),
                    ]
                    loop = _get_loop()
                    try:
                        loop.run_until_complete(asr_stream(ws))
                        loop.run_until_complete(asyncio.sleep(0.05))
                    except Exception:
                        pass
                        _clean_pending(loop)
        types = [m["type"] for m in ws.sent]
        assert "filtered" in types
        filtered_msgs = [m for m in ws.sent if m.get("type") == "filtered"]
        assert any(m.get("reason") == "speaker_mismatch" for m in filtered_msgs)


class TestWSCallbackDuplicateFiltered:
    def test_duplicate_filtered(self):
        ws = MockWebSocket()
        cfg = _make_cfg(auto_query=True)
        captured = {}

        def start_stream(cb):
            captured["cb"] = cb

        def send_audio(data):
            cb = captured.get("cb")
            if cb:
                cb.on_final("ETC扣费查询")

        with patch("asr.websocket.get_config", return_value=cfg):
            with patch("asr.streaming.get_streaming_service") as mock_get:
                with patch("asr.websocket._do_query", return_value={"answer": "测试"}):
                    with patch("asr.websocket.QueryCache.should_skip", side_effect=[False, True]):
                        mock_svc = MagicMock()
                        mock_svc.mode = "local"
                        mock_svc.start_stream = start_stream
                        mock_svc.send_audio = send_audio
                        mock_get.return_value = mock_svc
                        ws.receive_queue = [
                            {"bytes": b"\x00" * 3200},
                            {"bytes": b"\x00" * 3200},
                            WebSocketDisconnect(),
                        ]
                        loop = _get_loop()
                        try:
                            loop.run_until_complete(asr_stream(ws))
                            loop.run_until_complete(asyncio.sleep(0.05))
                        except Exception:
                            pass
                            _clean_pending(loop)
        filtered_msgs = [m for m in ws.sent if m.get("type") == "filtered"]
        assert any(m.get("reason") == "duplicate" for m in filtered_msgs)


class TestWSReadyHasState:
    def test_ready_message_contains_state_field(self):
        ws = _run(_make_cfg(), [])
        ready = ws.sent[0]
        assert ready["type"] == "ready"
        assert "state" in ready
        assert ready["state"] == "idle"


class TestWSSelectAnswer:
    def test_select_answer_returns_answer_selected(self):
        ws = _run(_make_cfg(), [{"text": '{"type": "select_answer", "qa_id": 42}'}])
        types = [m["type"] for m in ws.sent]
        assert "answer_selected" in types
        selected = [m for m in ws.sent if m.get("type") == "answer_selected"][0]
        assert selected["qa_id"] == 42

    def test_select_answer_without_qa_id(self):
        ws = _run(_make_cfg(), [{"text": '{"type": "select_answer"}'}])
        types = [m["type"] for m in ws.sent]
        assert "answer_selected" in types


class TestWSReset:
    def test_reset_returns_reset_done(self):
        ws = _run(_make_cfg(), [{"text": '{"type": "reset"}'}])
        types = [m["type"] for m in ws.sent]
        assert "reset_done" in types


class TestWSAudioStateTransition:
    def test_audio_sends_state_change_to_listening(self):
        ws = _run(_make_cfg(), [{"bytes": b"\x00" * 3200}])
        state_changes = [m for m in ws.sent if m.get("type") == "state_change"]
        assert any(m["state"] == "listening" for m in state_changes)


class TestWSStateMachineFullCycle:
    def test_audio_then_select_answer_then_reset(self):
        ws = _run(_make_cfg(), [
            {"bytes": b"\x00" * 3200},
            {"text": '{"type": "select_answer", "qa_id": 1}'},
            {"text": '{"type": "reset"}'},
        ])
        types = [m["type"] for m in ws.sent]
        assert "answer_selected" in types
        assert "reset_done" in types


class TestWSOnFinalCorrections:
    def test_corrections_applied_in_on_final(self):
        ws = MockWebSocket()
        cfg = _make_cfg(auto_query=False)
        captured = {}

        def start_stream(cb):
            captured["cb"] = cb

        def send_audio(data):
            cb = captured.get("cb")
            if cb:
                cb.on_final("E T C扣费异常")

        with patch("asr.websocket.get_config", return_value=cfg):
            with patch("asr.streaming.get_streaming_service") as mock_get:
                with patch("asr.websocket._load_corrections", return_value={"E T C": "ETC"}):
                    mock_svc = MagicMock()
                    mock_svc.mode = "local"
                    mock_svc.start_stream = start_stream
                    mock_svc.send_audio = send_audio
                    mock_get.return_value = mock_svc
                    ws.receive_queue = [{"bytes": b"\x00" * 3200}, WebSocketDisconnect()]
                    loop = _get_loop()
                    try:
                        loop.run_until_complete(asr_stream(ws))
                        loop.run_until_complete(asyncio.sleep(0.05))
                    except Exception:
                        pass
                        _clean_pending(loop)
        final_msgs = [m for m in ws.sent if m.get("type") == "final"]
        assert len(final_msgs) >= 1
        assert final_msgs[0]["text"] == "ETC扣费异常"

    def test_corrections_applied_then_query_uses_corrected_text(self):
        ws = MockWebSocket()
        cfg = _make_cfg(auto_query=True)
        captured = {}

        def start_stream(cb):
            captured["cb"] = cb

        def send_audio(data):
            cb = captured.get("cb")
            if cb:
                cb.on_final("O B U设备激活")

        with patch("asr.websocket.get_config", return_value=cfg):
            with patch("asr.streaming.get_streaming_service") as mock_get:
                with patch("asr.websocket._load_corrections", return_value={"O B U": "OBU"}):
                    with patch("asr.websocket._do_query", return_value={"answer": "测试"}) as mock_q:
                        mock_svc = MagicMock()
                        mock_svc.mode = "local"
                        mock_svc.start_stream = start_stream
                        mock_svc.send_audio = send_audio
                        mock_get.return_value = mock_svc
                        ws.receive_queue = [{"bytes": b"\x00" * 3200}, WebSocketDisconnect()]
                        loop = _get_loop()
                        try:
                            loop.run_until_complete(asr_stream(ws))
                            loop.run_until_complete(asyncio.sleep(0.05))
                        except Exception:
                            pass
                            _clean_pending(loop)
        query_calls = [c[0][0] for c in mock_q.call_args_list]
        assert any("OBU设备激活" in q for q in query_calls)
        assert not any("O B U" in q for q in query_calls)

    def test_no_corrections_when_table_empty(self):
        ws = MockWebSocket()
        cfg = _make_cfg(auto_query=False)
        captured = {}

        def start_stream(cb):
            captured["cb"] = cb

        def send_audio(data):
            cb = captured.get("cb")
            if cb:
                cb.on_final("E T C扣费")

        with patch("asr.websocket.get_config", return_value=cfg):
            with patch("asr.streaming.get_streaming_service") as mock_get:
                with patch("asr.websocket._load_corrections", return_value={}):
                    mock_svc = MagicMock()
                    mock_svc.mode = "local"
                    mock_svc.start_stream = start_stream
                    mock_svc.send_audio = send_audio
                    mock_get.return_value = mock_svc
                    ws.receive_queue = [{"bytes": b"\x00" * 3200}, WebSocketDisconnect()]
                    loop = _get_loop()
                    try:
                        loop.run_until_complete(asr_stream(ws))
                        loop.run_until_complete(asyncio.sleep(0.05))
                    except Exception:
                        pass
                        _clean_pending(loop)
        final_msgs = [m for m in ws.sent if m.get("type") == "final"]
        assert len(final_msgs) >= 1
        assert final_msgs[0]["text"] == "E T C扣费"
