from unittest.mock import MagicMock, patch

from asr.ws_helpers import (
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


class TestIsGreeting:
    def test_simple_greetings(self):
        assert _is_greeting("你好") is True
        assert _is_greeting("您好") is True
        assert _is_greeting("喂") is True
        assert _is_greeting("嗯") is True

    def test_greetings_with_particles(self):
        assert _is_greeting("你好啊") is True
        assert _is_greeting("您好，") is True
        assert _is_greeting("喂？") is True

    def test_polite_openings(self):
        assert _is_greeting("那个") is True
        assert _is_greeting("就是") is True
        assert _is_greeting("我想问一下") is True
        assert _is_greeting("请问一下") is True
        assert _is_greeting("不好意思") is True

    def test_empty_and_short(self):
        assert _is_greeting("") is True
        assert _is_greeting("  ") is True
        assert _is_greeting("OK") is True

    def test_real_questions_not_greeting(self):
        assert _is_greeting("ETC怎么办理") is False
        assert _is_greeting("ETC扣费异常怎么处理") is False
        assert _is_greeting("我的OBU设备激活不了") is False
        assert _is_greeting("蓝牙连接不上") is False
        assert _is_greeting("退款什么时候到账") is False

    def test_mixed_not_greeting(self):
        assert _is_greeting("你好，我想问一下ETC怎么办理") is False

    def test_为你好_is_greeting(self):
        assert _is_greeting("为你好") is True

    def test_为你_is_greeting(self):
        assert _is_greeting("为你") is True


class TestIsCorrection:
    def test_correction_phrases(self):
        assert _is_correction("不对") is True
        assert _is_correction("不是") is True
        assert _is_correction("搞错了") is True
        assert _is_correction("说错了") is True
        assert _is_correction("纠正一下") is True
        assert _is_correction("我重说") is True
        assert _is_correction("重新说") is True

    def test_correction_with_context(self):
        assert _is_correction("不对，ETC扣费") is True
        assert _is_correction("不是那个意思") is True

    def test_not_correction(self):
        assert _is_correction("ETC扣费有问题") is False
        assert _is_correction("你好") is False
        assert _is_correction("退款什么时候到账") is False


class TestHasPronoun:
    def test_pronouns_detected(self):
        assert _has_pronoun("那个怎么退款") is True
        assert _has_pronoun("这个有问题") is True
        assert _has_pronoun("它怎么连接") is True
        assert _has_pronoun("刚才说的那个") is True
        assert _has_pronoun("前面提到的") is True
        assert _has_pronoun("刚刚说的") is True

    def test_no_pronoun(self):
        assert _has_pronoun("ETC扣费有问题") is False
        assert _has_pronoun("蓝牙连接不上") is False
        assert _has_pronoun("退款什么时候到账") is False


class TestCharOverlapRatio:
    def test_identical(self):
        assert _char_overlap_ratio("ETC扣费有问题", "ETC扣费有问题") == 1.0

    def test_similar(self):
        r = _char_overlap_ratio("ETC扣费有问题", "ETC扣费异常")
        assert r > 0.5

    def test_different(self):
        r = _char_overlap_ratio("ETC扣费有问题", "蓝牙连接不上")
        assert r < 0.3

    def test_empty(self):
        assert _char_overlap_ratio("", "test") == 0.0
        assert _char_overlap_ratio("test", "") == 0.0

    def test_partial_overlap(self):
        r = _char_overlap_ratio("对就是扣费有问题", "ETC扣费有问题")
        assert 0.3 < r < 0.8


class TestGetRecentAudio:
    def test_returns_all_when_under_window(self):
        from collections import deque
        chunks = deque([b"\x00" * 1600, b"\x00" * 1600], maxlen=500)
        result = _get_recent_audio(chunks, window_seconds=1.0, sample_rate=16000)
        assert len(result) == 2

    def test_truncates_to_window(self):
        from collections import deque
        chunks = deque([b"\x00" * 32000] * 10, maxlen=500)
        result = _get_recent_audio(chunks, window_seconds=0.5, sample_rate=16000)
        total = sum(len(c) for c in result)
        assert total <= 32000 * 10
        assert total >= 16000

    def test_empty_chunks(self):
        from collections import deque
        chunks = deque(maxlen=500)
        result = _get_recent_audio(chunks, window_seconds=1.0, sample_rate=16000)
        assert result == []

    def test_preserves_order(self):
        from collections import deque
        chunks = deque([b"AAA", b"BBB", b"CCC"], maxlen=500)
        result = _get_recent_audio(chunks, window_seconds=1.0, sample_rate=16000)
        assert b"".join(result) == b"AAABBBCCC"


class TestExtractChannel:
    def test_extract_left_channel(self):
        import numpy as np
        stereo = np.array([[100, 200], [300, 400], [500, 600]], dtype=np.int16)
        audio_bytes = stereo.tobytes()
        result = _extract_channel(audio_bytes, "left")
        result_np = np.frombuffer(result, dtype=np.int16)
        assert list(result_np) == [100, 300, 500]

    def test_extract_right_channel(self):
        import numpy as np
        stereo = np.array([[100, 200], [300, 400], [500, 600]], dtype=np.int16)
        audio_bytes = stereo.tobytes()
        result = _extract_channel(audio_bytes, "right")
        result_np = np.frombuffer(result, dtype=np.int16)
        assert list(result_np) == [200, 400, 600]

    def test_too_short_returns_original(self):
        short = b"\x00\x01"
        assert _extract_channel(short, "left") == short

    def test_odd_samples_returns_original(self):
        import numpy as np
        mono = np.array([100, 200, 300], dtype=np.int16)
        audio_bytes = mono.tobytes()
        assert _extract_channel(audio_bytes, "left") == audio_bytes

    def test_silence_channel(self):
        import numpy as np
        stereo = np.array([[0, 500], [0, 600]], dtype=np.int16)
        result = _extract_channel(stereo.tobytes(), "left")
        result_np = np.frombuffer(result, dtype=np.int16)
        assert list(result_np) == [0, 0]


class TestDoQuery:
    def test_returns_none_when_service_none(self):
        import sys
        mock_mod = MagicMock()
        mock_mod.service = None
        with patch.dict(sys.modules, {"api.routes": mock_mod}):
            result = _do_query("ETC扣费")
        assert result is None

    def test_returns_dict_on_success(self):
        import sys

        from models.schemas import QueryResponse
        mock_mod = MagicMock()
        mock_mod.service.query.return_value = QueryResponse(
            query="ETC扣费", confidence="high", candidates=[], total_candidates=0
        )
        with patch.dict(sys.modules, {"api.routes": mock_mod}):
            result = _do_query("ETC扣费")
        assert result is not None
        assert result["query"] == "ETC扣费"

    def test_returns_none_on_exception(self):
        import sys
        mock_mod = MagicMock()
        mock_mod.service.query.side_effect = RuntimeError("fail")
        with patch.dict(sys.modules, {"api.routes": mock_mod}):
            result = _do_query("ETC扣费")
        assert result is None


class TestIdentifySpeaker:
    def test_empty_map_returns_none(self):
        assert _identify_speaker("text", [], {}) is None

    def test_finds_customer_speaker(self):
        speaker_map = {"SPEAKER_00": "customer", "SPEAKER_01": "agent"}
        assert _identify_speaker("text", [], speaker_map) == "SPEAKER_00"

    def test_no_customer_label(self):
        speaker_map = {"SPEAKER_00": "agent", "SPEAKER_01": "agent"}
        assert _identify_speaker("text", [], speaker_map) is None


class TestDoDiarizeSegment:
    @patch("asr.diarizer.get_diarizer")
    def test_disabled_returns_empty(self, mock_get):
        mock_diarizer = MagicMock()
        mock_diarizer.enabled = False
        mock_get.return_value = mock_diarizer
        result = _do_diarize_segment(b"\x00" * 100, 16000)
        assert result == []

    @patch("asr.diarizer.get_diarizer")
    def test_enabled_returns_segments(self, mock_get):
        mock_diarizer = MagicMock()
        mock_diarizer.enabled = True
        mock_diarizer.diarize.return_value = [{"start": 0.0, "end": 1.0, "speaker": "SPEAKER_00"}]
        mock_get.return_value = mock_diarizer
        with patch("soundfile.write"):
            with patch("tempfile.mkstemp", return_value=(0, "fake.wav")):
                with patch("os.close"):
                    with patch("os.path.exists", return_value=False):
                        result = _do_diarize_segment(b"\x00" * 3200, 16000)
        assert len(result) == 1

    @patch("asr.diarizer.get_diarizer")
    def test_exception_returns_empty(self, mock_get):
        mock_diarizer = MagicMock()
        mock_diarizer.enabled = True
        mock_diarizer.diarize.side_effect = RuntimeError("fail")
        mock_get.return_value = mock_diarizer
        with patch("soundfile.write"):
            with patch("tempfile.mkstemp", return_value=(0, "fake.wav")):
                with patch("os.close"):
                    with patch("os.path.exists", return_value=False):
                        result = _do_diarize_segment(b"\x00" * 3200, 16000)
        assert result == []