import asyncio
import sys
import time
from unittest.mock import MagicMock, patch

from asr.ws_state import (
    ContextWindow,
    QueryAccumulator,
    QueryCache,
    SessionState,
    VADSilenceDetector,
)


class TestQueryAccumulator:
    def test_no_flush_before_max(self):
        acc = QueryAccumulator(max_sentences=3, silence_timeout=2.0)
        assert acc.add("第一句") is None
        assert acc.add("第二句") is None
        assert acc.pending_count == 2

    def test_auto_flush_at_max(self):
        acc = QueryAccumulator(max_sentences=3, silence_timeout=2.0)
        acc.add("A")
        acc.add("B")
        result = acc.add("C")
        assert result == ["A", "B", "C"]
        assert acc.pending_count == 0

    def test_manual_flush(self):
        acc = QueryAccumulator(max_sentences=5, silence_timeout=2.0)
        acc.add("X")
        acc.add("Y")
        flushed = acc.flush()
        assert flushed == ["X", "Y"]
        assert acc.pending_count == 0

    def test_flush_empty(self):
        acc = QueryAccumulator(max_sentences=3, silence_timeout=2.0)
        flushed = acc.flush()
        assert flushed == []

    def test_pop_last(self):
        acc = QueryAccumulator(max_sentences=5, silence_timeout=2.0)
        acc.add("A")
        acc.add("B")
        popped = acc.pop_last()
        assert popped == "B"
        assert acc.pending_count == 1

    def test_pop_last_empty(self):
        acc = QueryAccumulator(max_sentences=3, silence_timeout=2.0)
        assert acc.pop_last() is None

    def test_correction_removes_last(self):
        acc = QueryAccumulator(max_sentences=3, silence_timeout=2.0)
        acc.add("ETC扣费有问题")
        acc.add("不对")
        popped = acc.pop_last()
        assert popped == "不对"
        assert acc.pending_count == 1


class TestQueryCache:
    def test_first_query_not_skipped(self):
        cache = QueryCache(similarity_threshold=0.8, min_interval=5.0)
        assert cache.should_skip("ETC扣费有问题") is False

    def test_duplicate_skipped(self):
        cache = QueryCache(similarity_threshold=0.8, min_interval=5.0)
        cache.record("ETC扣费有问题", {"confidence": "high"})
        assert cache.should_skip("ETC扣费有问题") is True

    def test_different_not_skipped(self):
        cache = QueryCache(similarity_threshold=0.8, min_interval=5.0)
        cache.record("ETC扣费有问题", {"confidence": "high"})
        assert cache.should_skip("蓝牙连接不上") is False

    def test_get_recent_hit(self):
        cache = QueryCache(similarity_threshold=0.8, min_interval=5.0)
        cache.record("ETC扣费有问题", {"confidence": "high"})
        cached = cache.get_recent("ETC扣费有问题")
        assert cached is not None
        assert cached["confidence"] == "high"

    def test_get_recent_miss(self):
        cache = QueryCache(similarity_threshold=0.8, min_interval=5.0)
        cache.record("ETC扣费有问题", {"confidence": "high"})
        assert cache.get_recent("蓝牙连接不上") is None

    def test_expired_entry_ignored(self):
        cache = QueryCache(similarity_threshold=0.8, min_interval=0.01)
        cache.record("test", {"data": 1})
        time.sleep(0.02)
        assert cache.should_skip("test") is False

    def test_clear(self):
        cache = QueryCache(similarity_threshold=0.8, min_interval=5.0)
        cache.record("test", {"data": 1})
        cache.clear()
        assert cache.should_skip("test") is False


class TestContextWindow:
    def test_empty_context(self):
        ctx = ContextWindow(max_size=3)
        assert ctx.get_context() == []

    def test_add_and_get(self):
        ctx = ContextWindow(max_size=3)
        ctx.add("ETC扣费有问题")
        ctx.add("退款什么时候到账")
        assert ctx.get_context() == ["ETC扣费有问题", "退款什么时候到账"]

    def test_max_size_overflow(self):
        ctx = ContextWindow(max_size=3)
        ctx.add("A")
        ctx.add("B")
        ctx.add("C")
        ctx.add("D")
        assert len(ctx.get_context()) == 3
        assert ctx.get_context() == ["B", "C", "D"]

    def test_resolve_pronoun_with_context(self):
        ctx = ContextWindow(max_size=3)
        ctx.add("ETC扣费有问题")
        ctx.add("退款什么时候到账")
        resolved = ctx.resolve_pronoun("那个怎么处理")
        assert "ETC扣费有问题" in resolved
        assert "退款什么时候到账" in resolved
        assert "那个怎么处理" in resolved

    def test_resolve_no_pronoun(self):
        ctx = ContextWindow(max_size=3)
        ctx.add("ETC扣费有问题")
        result = ctx.resolve_pronoun("蓝牙连接不上")
        assert result == "蓝牙连接不上"

    def test_resolve_empty_context(self):
        ctx = ContextWindow(max_size=3)
        result = ctx.resolve_pronoun("那个怎么处理")
        assert result == "那个怎么处理"

    def test_clear(self):
        ctx = ContextWindow(max_size=3)
        ctx.add("A")
        ctx.add("B")
        ctx.clear()
        assert ctx.get_context() == []


class TestVADSilenceDetector:
    def test_initial_not_silence(self):
        detector = VADSilenceDetector(silence_threshold=0.05)
        assert detector.check_silence() is False

    def test_silence_after_timeout(self):
        detector = VADSilenceDetector(silence_threshold=0.05)
        time.sleep(0.06)
        assert detector.check_silence() is True

    def test_reset(self):
        detector = VADSilenceDetector(silence_threshold=0.05)
        time.sleep(0.06)
        detector.reset()
        assert detector.check_silence() is False


class TestVADFeedAudio:
    def test_empty_chunk_returns(self):
        detector = VADSilenceDetector(silence_threshold=100)
        detector.feed_audio(b"")
        assert detector.check_silence() is False

    def test_no_model_updates_time(self):
        detector = VADSilenceDetector(silence_threshold=0.05)
        detector._model = None
        detector.feed_audio(b"\x00" * 100)
        assert detector.check_silence() is False

    def test_with_model_speech_detected(self):
        detector = VADSilenceDetector(silence_threshold=0.05)
        detector._model = MagicMock()
        detector._get_speech_timestamps = MagicMock(return_value=[{"start": 0}])
        with patch("torch.from_numpy") as mock_torch:
            mock_torch.return_value = MagicMock()
            detector.feed_audio(b"\x00" * 3200)
        assert detector.check_silence() is False

    def test_with_model_no_speech(self):
        detector = VADSilenceDetector(silence_threshold=0.05)
        detector._model = MagicMock()
        detector._get_speech_timestamps = MagicMock(return_value=[])
        with patch("torch.from_numpy") as mock_torch:
            mock_torch.return_value = MagicMock()
            time.sleep(0.06)
            detector.feed_audio(b"\x00" * 3200)
        assert detector.check_silence() is True

    def test_exception_fallback(self):
        detector = VADSilenceDetector(silence_threshold=0.05)
        detector._model = MagicMock()
        detector._get_speech_timestamps = MagicMock(side_effect=RuntimeError("fail"))
        with patch("torch.from_numpy", side_effect=RuntimeError("fail")):
            detector.feed_audio(b"\x00" * 3200)
        assert detector.check_silence() is False


class TestAccumulatorCheckTimeout:
    def test_timeout_triggers_flush(self):
        acc = QueryAccumulator(max_sentences=5, silence_timeout=0.05)
        acc.add("ETC扣费")
        time.sleep(0.06)
        result = acc.check_timeout()
        assert result == ["ETC扣费"]
        assert acc.pending_count == 0

    def test_no_timeout_returns_none(self):
        acc = QueryAccumulator(max_sentences=5, silence_timeout=2.0)
        acc.add("ETC扣费")
        result = acc.check_timeout()
        assert result is None

    def test_empty_buffer_returns_none(self):
        acc = QueryAccumulator(max_sentences=5, silence_timeout=0.01)
        time.sleep(0.02)
        result = acc.check_timeout()
        assert result is None


class TestSessionState:
    def test_state_values(self):
        assert SessionState.IDLE.value == "idle"
        assert SessionState.LISTENING.value == "listening"
        assert SessionState.QUERY_READY.value == "query_ready"
        assert SessionState.CANDIDATES_SHOWN.value == "candidates_shown"
        assert SessionState.RESOLVED.value == "resolved"

    def test_state_transitions(self):
        assert SessionState.IDLE != SessionState.LISTENING
        assert SessionState.LISTENING != SessionState.QUERY_READY
        assert SessionState.QUERY_READY != SessionState.CANDIDATES_SHOWN
        assert SessionState.CANDIDATES_SHOWN != SessionState.RESOLVED
        assert SessionState.RESOLVED != SessionState.IDLE

    def test_state_membership_for_audio_transition(self):
        transition_states = (SessionState.IDLE, SessionState.RESOLVED, SessionState.CANDIDATES_SHOWN)
        assert SessionState.IDLE in transition_states
        assert SessionState.RESOLVED in transition_states
        assert SessionState.CANDIDATES_SHOWN in transition_states
        assert SessionState.LISTENING not in transition_states
        assert SessionState.QUERY_READY not in transition_states

    def test_state_is_enum(self):
        from enum import Enum
        assert isinstance(SessionState.IDLE, Enum)
        assert isinstance(SessionState.LISTENING, SessionState)


class TestVADLoadModel:
    def test_load_model_success(self):
        detector = VADSilenceDetector(silence_threshold=2.0)
        mock_model = MagicMock()
        mock_get_speech_timestamps = MagicMock()
        mock_utils = [mock_get_speech_timestamps, MagicMock()]
        mock_torch = MagicMock()
        mock_torch.hub.load.return_value = (mock_model, mock_utils)
        with patch.dict(sys.modules, {"torch": mock_torch}):
            asyncio.run(detector._load_model())
        assert detector._model is mock_model
        assert detector._get_speech_timestamps is mock_get_speech_timestamps

    def test_load_model_failure(self):
        detector = VADSilenceDetector(silence_threshold=2.0)
        mock_torch = MagicMock()
        mock_torch.hub.load.side_effect = RuntimeError("load failed")
        with patch.dict(sys.modules, {"torch": mock_torch}):
            asyncio.run(detector._load_model())
        assert detector._model is None
        assert detector._get_speech_timestamps is None

    def test_load_model_import_error(self):
        detector = VADSilenceDetector(silence_threshold=2.0)
        original_import = __import__

        def blocking_import(name, *args, **kwargs):
            if name == "torch":
                raise ImportError("No module named 'torch'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=blocking_import):
            asyncio.run(detector._load_model())
        assert detector._model is None

    def test_load_model_already_loaded_skips(self):
        detector = VADSilenceDetector(silence_threshold=2.0)
        existing_model = MagicMock()
        existing_get_speech = MagicMock()
        detector._model = existing_model
        detector._get_speech_timestamps = existing_get_speech
        mock_torch = MagicMock()
        with patch.dict(sys.modules, {"torch": mock_torch}):
            asyncio.run(detector._load_model())
        mock_torch.hub.load.assert_not_called()
        assert detector._model is existing_model
        assert detector._get_speech_timestamps is existing_get_speech