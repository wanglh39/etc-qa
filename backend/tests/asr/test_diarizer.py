import sys
from unittest.mock import MagicMock, patch

import torch

import asr.diarizer as diarizer_module
from asr.diarizer import SpeakerDiarizer, get_diarizer


class TestSpeakerDiarizer:
    @patch("asr.diarizer.get_config")
    def test_disabled_returns_empty(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"diarize": {"enabled": False}}}
        d = SpeakerDiarizer()
        assert d.enabled is False
        assert d.diarize("fake.wav") == []

    @patch("asr.diarizer.get_config")
    def test_enabled_property(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"diarize": {"enabled": True}}}
        d = SpeakerDiarizer()
        assert d.enabled is True

    @patch("asr.diarizer.get_config")
    def test_default_config(self, mock_cfg):
        mock_cfg.return_value = {"asr": {}}
        d = SpeakerDiarizer()
        assert d._enabled is False
        assert d._model_name == "pyannote/speaker-diarization-community-1"
        assert d._device == "cuda"

    @patch("asr.diarizer.get_config")
    def test_custom_config(self, mock_cfg):
        mock_cfg.return_value = {
            "asr": {
                "diarize": {
                    "enabled": True,
                    "model": "custom-model",
                    "hf_token": "hf_test_token",
                    "device": "cpu",
                    "num_speakers": 2,
                    "min_speakers": 1,
                    "max_speakers": 3,
                }
            }
        }
        d = SpeakerDiarizer()
        assert d._model_name == "custom-model"
        assert d._hf_token == "hf_test_token"
        assert d._device == "cpu"
        assert d._num_speakers == 2
        assert d._min_speakers == 1
        assert d._max_speakers == 3

    @patch("asr.diarizer.get_config")
    def test_health_disabled(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"diarize": {"enabled": False}}}
        d = SpeakerDiarizer()
        h = d.health()
        assert h["enabled"] is False
        assert h["loaded"] is False

    @patch("asr.diarizer.get_config")
    def test_reload_clears_pipeline(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"diarize": {"enabled": True}}}
        d = SpeakerDiarizer()
        d._pipeline = MagicMock()
        d.reload()
        assert d._pipeline is None

    @patch("asr.diarizer.get_config")
    def test_diarize_with_mock_pipeline(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"diarize": {"enabled": True, "device": "cpu"}}}
        d = SpeakerDiarizer()

        mock_pipeline = MagicMock()
        mock_turn1 = MagicMock()
        mock_turn1.start = 0.0
        mock_turn1.end = 2.5
        mock_turn2 = MagicMock()
        mock_turn2.start = 2.8
        mock_turn2.end = 5.0

        mock_pipeline.return_value.itertracks.return_value = [
            (mock_turn1, "SPEAKER_00"),
            (mock_turn2, "SPEAKER_01"),
        ]
        d._pipeline = mock_pipeline

        result = d.diarize("test.wav")
        assert len(result) == 2
        assert result[0]["start"] == 0.0
        assert result[0]["end"] == 2.5
        assert result[0]["speaker"] == "SPEAKER_00"
        assert result[1]["speaker"] == "SPEAKER_01"

    @patch("asr.diarizer.get_config")
    def test_diarize_passes_num_speakers(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"diarize": {"enabled": True, "device": "cpu", "num_speakers": 2}}}
        d = SpeakerDiarizer()
        mock_pipeline = MagicMock()
        mock_pipeline.return_value.itertracks.return_value = []
        d._pipeline = mock_pipeline

        d.diarize("test.wav")
        mock_pipeline.assert_called_once_with("test.wav", num_speakers=2)

    @patch("asr.diarizer.get_config")
    def test_diarize_failure_returns_empty(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"diarize": {"enabled": True, "device": "cpu"}}}
        d = SpeakerDiarizer()
        d._pipeline = MagicMock()
        d._pipeline.side_effect = RuntimeError("pipeline error")

        try:
            result = d.diarize("test.wav")
            assert False
        except RuntimeError:
            pass


class TestGetDiarizer:
    def test_singleton(self):
        diarizer_module._diarizer = None
        with patch("asr.diarizer.get_config", return_value={"asr": {}}):
            d1 = get_diarizer()
            d2 = get_diarizer()
            assert d1 is d2


class TestLoadPipeline:
    @patch("asr.diarizer.get_config")
    def test_load_pipeline_success(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"diarize": {"enabled": True, "device": "cpu", "hf_token": "token"}}}
        d = SpeakerDiarizer()
        mock_pipeline = MagicMock()
        mock_pa = MagicMock()
        mock_pa.Pipeline.from_pretrained.return_value = mock_pipeline
        with patch.dict(sys.modules, {"pyannote.audio": mock_pa}):
            with patch("torch.cuda.is_available", return_value=False):
                d._load_pipeline()
        assert d._pipeline is mock_pipeline

    @patch("asr.diarizer.get_config")
    def test_load_pipeline_already_loaded(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"diarize": {"enabled": True}}}
        d = SpeakerDiarizer()
        d._pipeline = MagicMock()
        d._load_pipeline()
        assert d._pipeline is not None

    @patch("asr.diarizer.get_config")
    def test_load_pipeline_gpu(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"diarize": {"enabled": True, "device": "cuda", "hf_token": "t"}}}
        d = SpeakerDiarizer()
        mock_pipeline = MagicMock()
        mock_pa = MagicMock()
        mock_pa.Pipeline.from_pretrained.return_value = mock_pipeline
        with patch.dict(sys.modules, {"pyannote.audio": mock_pa}):
            with patch("torch.cuda.is_available", return_value=True):
                with patch("torch.device"):
                    d._load_pipeline()
        assert d._pipeline is not None

    @patch("asr.diarizer.get_config")
    def test_load_pipeline_import_error(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"diarize": {"enabled": True}}}
        d = SpeakerDiarizer()
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "pyannote.audio":
                raise ImportError("not installed")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            try:
                d._load_pipeline()
                assert False
            except RuntimeError as e:
                assert "pyannote" in str(e)


class TestDiarizeWithModel:
    @patch("asr.diarizer.get_config")
    def test_diarize_with_num_speakers(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"diarize": {"enabled": True, "num_speakers": 2, "device": "cpu"}}}
        d = SpeakerDiarizer()
        mock_pipeline = MagicMock()
        mock_diarization = MagicMock()
        mock_diarization.itertracks.return_value = [
            (MagicMock(start=0.0, end=1.0), "SPEAKER_00"),
            (MagicMock(start=1.0, end=2.0), "SPEAKER_01"),
        ]
        mock_pipeline.return_value = mock_diarization
        d._pipeline = mock_pipeline
        result = d.diarize("test.wav")
        assert len(result) == 2
        assert result[0]["speaker"] == "SPEAKER_00"

    @patch("asr.diarizer.get_config")
    def test_diarize_with_min_max_speakers(self, mock_cfg):
        mock_cfg.return_value = {
            "asr": {"diarize": {"enabled": True, "min_speakers": 1, "max_speakers": 3, "device": "cpu"}}
        }
        d = SpeakerDiarizer()
        mock_pipeline = MagicMock()
        mock_diarization = MagicMock()
        mock_diarization.itertracks.return_value = []
        mock_pipeline.return_value = mock_diarization
        d._pipeline = mock_pipeline
        result = d.diarize("test.wav")
        assert result == []
