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
        assert _is_greeting("浣犲ソ") is True
        assert _is_greeting("鎮ㄥソ") is True
        assert _is_greeting("鍠?) is True
        assert _is_greeting("鍡?) is True

    def test_greetings_with_particles(self):
        assert _is_greeting("浣犲ソ鍟?) is True
        assert _is_greeting("鎮ㄥソ锛?) is True
        assert _is_greeting("鍠傦紵") is True

    def test_polite_openings(self):
        assert _is_greeting("閭ｄ釜") is True
        assert _is_greeting("灏辨槸") is True
        assert _is_greeting("鎴戞兂闂竴涓?) is True
        assert _is_greeting("璇烽棶涓€涓?) is True
        assert _is_greeting("涓嶅ソ鎰忔€?) is True

    def test_empty_and_short(self):
        assert _is_greeting("") is True
        assert _is_greeting("  ") is True
        assert _is_greeting("OK") is True

    def test_real_questions_not_greeting(self):
        assert _is_greeting("ETC鎬庝箞鍔炵悊") is False
        assert _is_greeting("ETC鎵ｈ垂寮傚父鎬庝箞澶勭悊") is False
        assert _is_greeting("鎴戠殑OBU璁惧婵€娲讳笉浜?) is False
        assert _is_greeting("钃濈墮杩炴帴涓嶄笂") is False
        assert _is_greeting("閫€娆句粈涔堟椂鍊欏埌璐?) is False

    def test_mixed_not_greeting(self):
        assert _is_greeting("浣犲ソ锛屾垜鎯抽棶涓€涓婨TC鎬庝箞鍔炵悊") is False

    def test_涓轰綘濂絖is_greeting(self):
        assert _is_greeting("涓轰綘濂?) is True

    def test_涓轰綘_is_greeting(self):
        assert _is_greeting("涓轰綘") is True


class TestIsCorrection:
    def test_correction_phrases(self):
        assert _is_correction("涓嶅") is True
        assert _is_correction("涓嶆槸") is True
        assert _is_correction("鎼為敊浜?) is True
        assert _is_correction("璇撮敊浜?) is True
        assert _is_correction("绾犳涓€涓?) is True
        assert _is_correction("鎴戦噸璇?) is True
        assert _is_correction("閲嶆柊璇?) is True

    def test_correction_with_context(self):
        assert _is_correction("涓嶅锛孍TC鎵ｈ垂") is True
        assert _is_correction("涓嶆槸閭ｄ釜鎰忔€?) is True

    def test_not_correction(self):
        assert _is_correction("ETC鎵ｈ垂鏈夐棶棰?) is False
        assert _is_correction("浣犲ソ") is False
        assert _is_correction("閫€娆句粈涔堟椂鍊欏埌璐?) is False


class TestHasPronoun:
    def test_pronouns_detected(self):
        assert _has_pronoun("閭ｄ釜鎬庝箞閫€娆?) is True
        assert _has_pronoun("杩欎釜鏈夐棶棰?) is True
        assert _has_pronoun("瀹冩€庝箞杩炴帴") is True
        assert _has_pronoun("鍒氭墠璇寸殑閭ｄ釜") is True
        assert _has_pronoun("鍓嶉潰鎻愬埌鐨?) is True
        assert _has_pronoun("鍒氬垰璇寸殑") is True

    def test_no_pronoun(self):
        assert _has_pronoun("ETC鎵ｈ垂鏈夐棶棰?) is False
        assert _has_pronoun("钃濈墮杩炴帴涓嶄笂") is False
        assert _has_pronoun("閫€娆句粈涔堟椂鍊欏埌璐?) is False


class TestCharOverlapRatio:
    def test_identical(self):
        assert _char_overlap_ratio("ETC鎵ｈ垂鏈夐棶棰?, "ETC鎵ｈ垂鏈夐棶棰?) == 1.0

    def test_similar(self):
        r = _char_overlap_ratio("ETC鎵ｈ垂鏈夐棶棰?, "ETC鎵ｈ垂寮傚父")
        assert r > 0.5

    def test_different(self):
        r = _char_overlap_ratio("ETC鎵ｈ垂鏈夐棶棰?, "钃濈墮杩炴帴涓嶄笂")
        assert r < 0.3

    def test_empty(self):
        assert _char_overlap_ratio("", "test") == 0.0
        assert _char_overlap_ratio("test", "") == 0.0

    def test_partial_overlap(self):
        r = _char_overlap_ratio("瀵瑰氨鏄墸璐规湁闂", "ETC鎵ｈ垂鏈夐棶棰?)
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
            result = _do_query("ETC鎵ｈ垂")
        assert result is None

    def test_returns_dict_on_success(self):
        import sys
        from models.schemas import QueryResponse
        mock_mod = MagicMock()
        mock_mod.service.query.return_value = QueryResponse(
            query="ETC鎵ｈ垂", confidence="high", candidates=[], total_candidates=0
        )
        with patch.dict(sys.modules, {"api.routes": mock_mod}):
            result = _do_query("ETC鎵ｈ垂")
        assert result is not None
        assert result["query"] == "ETC鎵ｈ垂"

    def test_returns_none_on_exception(self):
        import sys
        mock_mod = MagicMock()
        mock_mod.service.query.side_effect = RuntimeError("fail")
        with patch.dict(sys.modules, {"api.routes": mock_mod}):
            result = _do_query("ETC鎵ｈ垂")
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