import asyncio
import time
from collections import deque
from enum import Enum

from asr.ws_helpers import _char_overlap_ratio, _has_pronoun
from utils.logger import get_logger

logger = get_logger("asr.websocket")


class SessionState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    QUERY_READY = "query_ready"
    CANDIDATES_SHOWN = "candidates_shown"
    RESOLVED = "resolved"


class QueryAccumulator:
    def __init__(self, max_sentences: int = 3, silence_timeout: float = 2.0):
        self._max_sentences = max_sentences
        self._silence_timeout = silence_timeout
        self._buffer: list[str] = []
        self._last_final_time = 0.0

    def add(self, text: str) -> list[str] | None:
        self._last_final_time = time.time()
        self._buffer.append(text)

        if len(self._buffer) >= self._max_sentences:
            return self.flush()

        return None

    def check_timeout(self) -> list[str] | None:
        if self._buffer and (time.time() - self._last_final_time) >= self._silence_timeout:
            return self.flush()
        return None

    def flush(self) -> list[str]:
        result = self._buffer[:]
        self._buffer.clear()
        return result

    def pop_last(self) -> str | None:
        if self._buffer:
            return self._buffer.pop()
        return None

    @property
    def pending_count(self) -> int:
        return len(self._buffer)


class QueryCache:
    def __init__(self, similarity_threshold: float = 0.8, min_interval: float = 5.0, max_size: int = 20):
        self._similarity_threshold = similarity_threshold
        self._min_interval = min_interval
        self._max_size = max_size
        self._entries: deque[dict] = deque(maxlen=max_size)

    def should_skip(self, text: str) -> bool:
        now = time.time()
        for entry in self._entries:
            if now - entry["time"] < self._min_interval:
                ratio = _char_overlap_ratio(text, entry["text"])
                if ratio >= self._similarity_threshold:
                    return True
        return False

    def record(self, text: str, result: dict | None):
        self._entries.append({"text": text, "time": time.time(), "result": result})

    def get_recent(self, text: str) -> dict | None:
        now = time.time()
        for entry in reversed(self._entries):
            if now - entry["time"] < self._min_interval:
                ratio = _char_overlap_ratio(text, entry["text"])
                if ratio >= self._similarity_threshold and entry["result"] is not None:
                    return entry["result"]
        return None

    def clear(self):
        self._entries.clear()


class ContextWindow:
    def __init__(self, max_size: int = 3):
        self._max_size = max_size
        self._items: deque[str] = deque(maxlen=max_size)

    def add(self, text: str):
        if text and text.strip():
            self._items.append(text.strip())

    def get_context(self) -> list[str]:
        return list(self._items)

    def resolve_pronoun(self, text: str) -> str:
        if not _has_pronoun(text):
            return text
        if not self._items:
            return text
        context = list(self._items)
        combined = "".join(context) + text
        return combined

    def clear(self):
        self._items.clear()


class VADSilenceDetector:
    def __init__(self, silence_threshold: float = 2.0, chunk_duration_ms: float = 60.0):
        self._silence_threshold = silence_threshold
        self._chunk_duration_ms = chunk_duration_ms
        self._last_speech_time = time.time()
        self._model = None
        self._get_speech_timestamps = None
        self._lock = asyncio.Lock()

    async def _load_model(self):
        if self._model is not None:
            return
        try:
            import torch

            model, utils = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad",
                trust_repo=True,
            )
            self._model = model
            self._get_speech_timestamps = utils[0]
            logger.info("VAD静音检测模型加载完成")
        except Exception as e:
            logger.warning(f"VAD模型加载失败: {e}")

    def feed_audio(self, audio_chunk: bytes):
        try:
            import numpy as np
            import torch

            audio_data = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32) / 32768.0
            if len(audio_data) == 0:
                return
            if self._model is None:
                self._last_speech_time = time.time()
                return
            audio_tensor = torch.from_numpy(audio_data).float()
            timestamps = self._get_speech_timestamps(
                audio_tensor,
                self._model,
                sampling_rate=16000,
                min_speech_duration_ms=100,
                min_silence_duration_ms=int(self._silence_threshold * 1000),
                speech_pad_ms=200,
            )
            if timestamps:
                self._last_speech_time = time.time()
        except Exception:
            self._last_speech_time = time.time()

    def check_silence(self) -> bool:
        return (time.time() - self._last_speech_time) >= self._silence_threshold

    def reset(self):
        self._last_speech_time = time.time()
