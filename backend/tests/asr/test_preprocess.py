from unittest.mock import MagicMock, patch

import numpy as np

import asr.preprocess as preprocess_module
from asr.preprocess import AudioPreprocessor, get_preprocessor


class TestAudioPreprocessor:
    @patch("asr.preprocess.get_config")
    def test_default_config(self, mock_cfg):
        mock_cfg.return_value = {"asr": {}}
        p = AudioPreprocessor()
        assert p.vad_enabled is False
        assert p.denoise_enabled is False

    @patch("asr.preprocess.get_config")
    def test_vad_enabled(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"preprocess": {"vad_enabled": True}}}
        p = AudioPreprocessor()
        assert p.vad_enabled is True

    @patch("asr.preprocess.get_config")
    def test_denoise_enabled(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"preprocess": {"denoise_enabled": True}}}
        p = AudioPreprocessor()
        assert p.denoise_enabled is True

    @patch("asr.preprocess.get_config")
    def test_process_noop_when_disabled(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"preprocess": {}}}
        p = AudioPreprocessor()
        result = p.process("test.wav")
        assert result == "test.wav"

    @patch("asr.preprocess.get_config")
    def test_apply_vad_disabled(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"preprocess": {"vad_enabled": False}}}
        p = AudioPreprocessor()
        import numpy as np

        audio = np.zeros(16000)
        result, sr = p.apply_vad(audio, 16000)
        assert (result == audio).all()

    @patch("asr.preprocess.get_config")
    def test_apply_denoise_disabled(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"preprocess": {"denoise_enabled": False}}}
        p = AudioPreprocessor()
        import numpy as np

        audio = np.zeros(16000)
        result, sr = p.apply_denoise(audio, 16000)
        assert (result == audio).all()

    @patch("asr.preprocess.get_config")
    def test_health(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"preprocess": {"vad_enabled": True, "denoise_enabled": True}}}
        p = AudioPreprocessor()
        h = p.health()
        assert h["vad_enabled"] is True
        assert h["denoise_enabled"] is True

    @patch("asr.preprocess.get_config")
    def test_cleanup_removes_temp(self, mock_cfg):
        mock_cfg.return_value = {"asr": {}}
        p = AudioPreprocessor()
        import os
        import tempfile

        fd, tmp = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        assert os.path.exists(tmp)
        p.cleanup(tmp, "original.wav")
        assert not os.path.exists(tmp)

    @patch("asr.preprocess.get_config")
    def test_cleanup_keeps_original(self, mock_cfg):
        mock_cfg.return_value = {"asr": {}}
        p = AudioPreprocessor()
        p.cleanup("same.wav", "same.wav")


class TestGetPreprocessor:
    def test_singleton(self):
        preprocess_module._preprocessor = None
        with patch("asr.preprocess.get_config", return_value={"asr": {}}):
            p1 = get_preprocessor()
            p2 = get_preprocessor()
            assert p1 is p2


class TestLoadAudio:
    @patch("asr.preprocess.get_config")
    def test_load_audio_success(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"preprocess": {}}}
        p = AudioPreprocessor()
        with patch("librosa.load", return_value=(np.zeros(16000), 16000)):
            audio, sr = p._load_audio("test.wav")
        assert sr == 16000
        assert len(audio) == 16000


class TestSaveAudio:
    @patch("asr.preprocess.get_config")
    def test_save_audio_success(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"preprocess": {}}}
        p = AudioPreprocessor()
        with patch("soundfile.write") as mock_write:
            p._save_audio(np.zeros(100), 16000, "out.wav")
        mock_write.assert_called_once()


class TestApplyVadEnabled:
    @patch("asr.preprocess.get_config")
    def test_vad_detects_speech(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"preprocess": {"vad_enabled": True}}}
        p = AudioPreprocessor()
        audio = np.zeros(16000)

        mock_model = MagicMock()
        mock_utils = [MagicMock(return_value=[{"start": 0, "end": 100}])]
        with patch("torch.hub.load", return_value=(mock_model, mock_utils)):
            with patch("torch.set_num_threads"):
                with patch("torch.from_numpy", return_value=MagicMock()):
                    result, sr = p.apply_vad(audio, 16000)
        assert sr == 16000

    @patch("asr.preprocess.get_config")
    def test_vad_no_speech_returns_original(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"preprocess": {"vad_enabled": True}}}
        p = AudioPreprocessor()
        audio = np.zeros(16000)

        mock_model = MagicMock()
        mock_utils = [MagicMock(return_value=[])]
        with patch("torch.hub.load", return_value=(mock_model, mock_utils)):
            with patch("torch.set_num_threads"):
                with patch("torch.from_numpy", return_value=MagicMock()):
                    result, sr = p.apply_vad(audio, 16000)
        assert len(result) == len(audio)

    @patch("asr.preprocess.get_config")
    def test_vad_load_failure_returns_original(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"preprocess": {"vad_enabled": True}}}
        p = AudioPreprocessor()
        audio = np.zeros(16000)

        with patch("torch.hub.load", side_effect=RuntimeError("fail")):
            result, sr = p.apply_vad(audio, 16000)
        assert len(result) == len(audio)


class TestApplyDenoiseEnabled:
    @patch("asr.preprocess.get_config")
    def test_denoise_success(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"preprocess": {"denoise_enabled": True}}}
        p = AudioPreprocessor()
        audio = np.random.randn(32000).astype(np.float32)

        import sys

        mock_nr = MagicMock()
        mock_nr.reduce_noise.return_value = audio * 0.5
        with patch.dict(sys.modules, {"noisereduce": mock_nr}):
            result, sr = p.apply_denoise(audio, 16000)
        assert sr == 16000

    @patch("asr.preprocess.get_config")
    def test_denoise_too_short(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"preprocess": {"denoise_enabled": True}}}
        p = AudioPreprocessor()
        audio = np.zeros(100)

        result, sr = p.apply_denoise(audio, 16000)
        assert len(result) == 100

    @patch("asr.preprocess.get_config")
    def test_denoise_import_error(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"preprocess": {"denoise_enabled": True}}}
        p = AudioPreprocessor()
        audio = np.zeros(32000)

        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "noisereduce":
                raise ImportError("not installed")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            result, sr = p.apply_denoise(audio, 16000)
        assert len(result) == 32000


class TestProcessFlow:
    @patch("asr.preprocess.get_config")
    def test_process_both_enabled(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"preprocess": {"vad_enabled": True, "denoise_enabled": True}}}
        p = AudioPreprocessor()

        with patch.object(p, "_load_audio", return_value=(np.zeros(16000), 16000)):
            with patch.object(p, "apply_denoise", return_value=(np.zeros(16000), 16000)):
                with patch.object(p, "apply_vad", return_value=(np.zeros(8000), 16000)):
                    with patch.object(p, "_save_audio"):
                        with patch("tempfile.mkstemp", return_value=(0, "out.wav")):
                            with patch("os.close"):
                                result = p.process("input.wav")
        assert result == "out.wav"

    @patch("asr.preprocess.get_config")
    def test_process_load_failure(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"preprocess": {"vad_enabled": True}}}
        p = AudioPreprocessor()

        with patch.object(p, "_load_audio", side_effect=RuntimeError("fail")):
            result = p.process("input.wav")
        assert result == "input.wav"

    @patch("asr.preprocess.get_config")
    def test_process_save_failure(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"preprocess": {"vad_enabled": True}}}
        p = AudioPreprocessor()

        with patch.object(p, "_load_audio", return_value=(np.zeros(16000), 16000)):
            with patch.object(p, "apply_vad", return_value=(np.zeros(16000), 16000)):
                with patch.object(p, "_save_audio", side_effect=RuntimeError("fail")):
                    with patch("tempfile.mkstemp", return_value=(0, "out.wav")):
                        with patch("os.close"):
                            result = p.process("input.wav")
        assert result == "input.wav"


class TestCleanupEdge:
    @patch("asr.preprocess.get_config")
    def test_cleanup_unlink_exception(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"preprocess": {}}}
        p = AudioPreprocessor()
        with patch("os.path.exists", return_value=True):
            with patch("os.unlink", side_effect=OSError("fail")):
                p.cleanup("processed.wav", "original.wav")
