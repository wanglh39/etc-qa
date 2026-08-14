import builtins
import sys
from unittest.mock import MagicMock, patch

import asr.service as svc_module
from asr.models import SpeakerSegment
from asr.service import ASRService, _apply_corrections, _load_corrections, get_asr_service


class TestApplyCorrections:
    def test_replaces_words(self):
        result = _apply_corrections("瑙ｅ咖ETC鎵ｈ垂寮傚父", {"瑙ｅ咖": "瑙ｆ偁"})
        assert result == "瑙ｆ偁ETC鎵ｈ垂寮傚父"

    def test_no_corrections(self):
        result = _apply_corrections("ETC鎵ｈ垂寮傚父", {})
        assert result == "ETC鎵ｈ垂寮傚父"

    def test_apply_corrections_etc_spaces(self):
        result = _apply_corrections("E T C鎵ｈ垂", {"E T C": "ETC"})
        assert result == "ETC鎵ｈ垂"

    def test_apply_corrections_obu_spaces(self):
        result = _apply_corrections("O B U璁惧", {"O B U": "OBU"})
        assert result == "OBU璁惧"

    def test_apply_corrections_lowercase_etc_spaces(self):
        result = _apply_corrections("e t c鎵ｈ垂", {"e t c": "ETC"})
        assert result == "ETC鎵ｈ垂"

    def test_apply_corrections_multiple_space_corrections(self):
        corrections = {"E T C": "ETC", "O B U": "OBU"}
        result = _apply_corrections("E T C鎵ｈ垂鍜孫 B U璁惧", corrections)
        assert result == "ETC鎵ｈ垂鍜孫BU璁惧"

    def test_apply_corrections_space_correction_at_end(self):
        result = _apply_corrections("鎵ｈ垂E T C", {"E T C": "ETC"})
        assert result == "鎵ｈ垂ETC"

    def test_apply_corrections_no_match_preserves_text(self):
        result = _apply_corrections("ETC鎵ｈ垂", {"E T C": "ETC"})
        assert result == "ETC鎵ｈ垂"


class TestLoadCorrections:
    def test_from_business_config(self):
        with patch("asr.service.get_business_config", return_value={"瑙ｅ咖": "瑙ｆ偁"}), \
             patch("asr.service.get_config", return_value={}):
            result = _load_corrections()
            assert result == {"瑙ｅ咖": "瑙ｆ偁"}

    def test_from_yaml_config(self):
        with patch("asr.service.get_business_config", return_value=None), \
             patch("asr.service.get_config", return_value={"asr": {"corrections": {"ETC": "etc"}}}):
            result = _load_corrections()
            assert result == {"ETC": "etc"}

    def test_business_config_not_dict(self):
        with patch("asr.service.get_business_config", return_value="not a dict"), \
             patch("asr.service.get_config", return_value={"asr": {"corrections": {"a": "b"}}}):
            result = _load_corrections()
            assert result == {"a": "b"}

    def test_no_corrections_anywhere(self):
        with patch("asr.service.get_business_config", return_value=None), \
             patch("asr.service.get_config", return_value={}):
            result = _load_corrections()
            assert result == {}


class TestASRService:
    @patch("asr.service.get_config")
    def test_disabled_raises(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"enabled": False}}
        svc = ASRService()
        try:
            svc.transcribe("fake.wav")
            assert False
        except RuntimeError as e:
            assert "ASR鏈惎鐢? in str(e)

    @patch("asr.service.get_config")
    def test_file_not_found(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"enabled": True, "model": "test", "device": "cpu"}}
        svc = ASRService()
        try:
            svc.transcribe("nonexistent_audio_file.wav")
            assert False
        except FileNotFoundError:
            pass

    @patch("asr.service.get_config")
    def test_health_not_loaded(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"enabled": True, "model": "test-model", "device": "cuda"}}
        svc = ASRService()
        h = svc.health()
        assert h.loaded is False
        assert h.model == "test-model"
        assert h.device == "cuda"
        assert h.finetuned is False

    @patch("asr.service.get_config")
    def test_health_finetuned(self, mock_cfg):
        mock_cfg.return_value = {
            "asr": {
                "enabled": True,
                "model": "base-model",
                "finetuned_path": "/path/to/finetuned",
                "device": "cuda",
            }
        }
        svc = ASRService()
        h = svc.health()
        assert h.finetuned is True
        assert h.model == "/path/to/finetuned"

    @patch("asr.service.get_config")
    def test_reload_clears_model(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"enabled": True, "model": "test", "device": "cpu"}}
        svc = ASRService()
        svc._model = MagicMock()
        svc.reload()
        assert svc._model is None

    @patch("asr.service.get_config")
    def test_transcribe_with_corrections(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"enabled": True, "model": "test", "device": "cpu"}}
        svc = ASRService()
        mock_model = MagicMock()
        mock_model.generate.return_value = [{"text": "瑙ｅ咖ETC鎵ｈ垂寮傚父", "confidence": 0.95}]
        svc._model = mock_model

        with patch("asr.service.get_business_config", return_value={"瑙ｅ咖": "瑙ｆ偁"}):
            import os
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                tmp_path = f.name
            try:
                result = svc.transcribe(tmp_path)
                assert "瑙ｆ偁" in result.text
                assert result.confidence == 0.95
            finally:
                os.unlink(tmp_path)

    @patch("asr.service.get_config")
    def test_transcribe_empty_result(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"enabled": True, "model": "test", "device": "cpu"}}
        svc = ASRService()
        mock_model = MagicMock()
        mock_model.generate.return_value = []
        svc._model = mock_model

        with patch("asr.service.get_business_config", return_value=None):
            import os
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                tmp_path = f.name
            try:
                result = svc.transcribe(tmp_path)
                assert result.text == ""
                assert result.confidence == 1.0
            finally:
                os.unlink(tmp_path)

    @patch("asr.service.get_config")
    def test_transcribe_no_confidence(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"enabled": True, "model": "test", "device": "cpu"}}
        svc = ASRService()
        mock_model = MagicMock()
        mock_model.generate.return_value = [{"text": "ETC闂"}]
        svc._model = mock_model

        with patch("asr.service.get_business_config", return_value=None):
            import os
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                tmp_path = f.name
            try:
                result = svc.transcribe(tmp_path)
                assert result.text == "ETC闂"
                assert result.confidence == 1.0
            finally:
                os.unlink(tmp_path)


class TestASRServiceVLLM:
    @patch("asr.service.get_config")
    def test_vllm_config_parsed(self, mock_cfg):
        mock_cfg.return_value = {
            "asr": {
                "enabled": True,
                "model": "FunAudioLLM/Fun-ASR-Nano-2512",
                "device": "cuda",
                "use_vllm": True,
                "tensor_parallel_size": 2,
            }
        }
        svc = ASRService()
        assert svc._use_vllm is True
        assert svc._tensor_parallel_size == 2

    @patch("asr.service.get_config")
    def test_vllm_default_config(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"enabled": True, "model": "test", "device": "cpu"}}
        svc = ASRService()
        assert svc._use_vllm is False
        assert svc._tensor_parallel_size == 1

    @patch("asr.service.get_config")
    def test_vllm_load_model_success(self, mock_cfg):
        mock_cfg.return_value = {
            "asr": {
                "enabled": True,
                "model": "test-vllm-model",
                "device": "cuda",
                "use_vllm": True,
                "tensor_parallel_size": 2,
            }
        }
        mock_vllm_cls = MagicMock()
        with patch.dict(sys.modules, {"funasr.auto.auto_model_vllm": MagicMock(AutoModelVLLM=mock_vllm_cls)}):
            svc = ASRService()
            svc._load_model()
            mock_vllm_cls.assert_called_once_with(
                model="test-vllm-model",
                tensor_parallel_size=2,
            )
            assert svc._model is not None

    @patch("asr.service.get_config")
    def test_vllm_import_error(self, mock_cfg):
        mock_cfg.return_value = {
            "asr": {
                "enabled": True,
                "model": "test-vllm-model",
                "device": "cuda",
                "use_vllm": True,
                "tensor_parallel_size": 1,
            }
        }
        original_import = builtins.__import__

        def blocking_import(name, *args, **kwargs):
            if name == "funasr.auto.auto_model_vllm":
                raise ImportError("No module named 'vllm'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=blocking_import):
            svc = ASRService()
            try:
                svc._load_model()
                assert False
            except RuntimeError as e:
                assert "vLLM妯″紡瀵煎叆澶辫触" in str(e)

    @patch("asr.service.get_config")
    def test_vllm_finetuned_path_used(self, mock_cfg):
        mock_cfg.return_value = {
            "asr": {
                "enabled": True,
                "model": "base-model",
                "finetuned_path": "/path/to/finetuned",
                "device": "cuda",
                "use_vllm": True,
                "tensor_parallel_size": 1,
            }
        }
        mock_vllm_cls = MagicMock()
        with patch.dict(sys.modules, {"funasr.auto.auto_model_vllm": MagicMock(AutoModelVLLM=mock_vllm_cls)}):
            svc = ASRService()
            svc._load_model()
            mock_vllm_cls.assert_called_once_with(
                model="/path/to/finetuned",
                tensor_parallel_size=1,
            )

    @patch("asr.service.get_config")
    def test_vllm_no_double_load(self, mock_cfg):
        mock_cfg.return_value = {
            "asr": {
                "enabled": True,
                "model": "test-model",
                "device": "cuda",
                "use_vllm": True,
                "tensor_parallel_size": 1,
            }
        }
        mock_vllm_cls = MagicMock()
        with patch.dict(sys.modules, {"funasr.auto.auto_model_vllm": MagicMock(AutoModelVLLM=mock_vllm_cls)}):
            svc = ASRService()
            svc._load_model()
            svc._load_model()
            assert mock_vllm_cls.call_count == 1

    @patch("asr.service.get_config")
    def test_normal_load_model_import_error(self, mock_cfg):
        mock_cfg.return_value = {
            "asr": {"enabled": True, "model": "test-model", "device": "cpu"}
        }
        original_import = builtins.__import__

        def blocking_import(name, *args, **kwargs):
            if name == "funasr":
                raise ImportError("No module named 'funasr'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=blocking_import):
            svc = ASRService()
            try:
                svc._load_model()
                assert False
            except RuntimeError as e:
                assert "funasr瀵煎叆澶辫触" in str(e)


class TestGetASRService:
    def test_singleton(self):
        svc_module._asr_service = None
        with patch("asr.service.get_config", return_value={"asr": {"enabled": False}}):
            s1 = get_asr_service()
            s2 = get_asr_service()
            assert s1 is s2


class TestMergeASRDiarize:
    @patch("asr.service.get_config")
    def test_empty_diarize(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"enabled": True, "model": "test", "device": "cpu"}}
        svc = ASRService()
        result = svc._merge_asr_diarize("ETC鎵ｈ垂寮傚父", [])
        assert result == []

    @patch("asr.service.get_config")
    def test_single_speaker(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"enabled": True, "model": "test", "device": "cpu"}}
        svc = ASRService()
        segments = svc._merge_asr_diarize(
            "ETC鎵ｈ垂寮傚父鎬庝箞澶勭悊",
            [{"start": 0.0, "end": 3.0, "speaker": "SPEAKER_00"}],
        )
        assert len(segments) == 1
        assert segments[0].speaker == "SPEAKER_00"
        assert segments[0].text == "ETC鎵ｈ垂寮傚父鎬庝箞澶勭悊"

    @patch("asr.service.get_config")
    def test_two_speakers(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"enabled": True, "model": "test", "device": "cpu"}}
        svc = ASRService()
        text = "ETC鎵ｈ垂寮傚父鎬庝箞澶勭悊閲嶅鎵ｈ垂鍙互鐢宠閫€娆?
        segments = svc._merge_asr_diarize(
            text,
            [
                {"start": 0.0, "end": 3.0, "speaker": "SPEAKER_00"},
                {"start": 3.5, "end": 6.0, "speaker": "SPEAKER_01"},
            ],
        )
        assert len(segments) == 2
        assert segments[0].speaker == "SPEAKER_00"
        assert segments[1].speaker == "SPEAKER_01"
        assert len(segments[0].text) > 0
        assert len(segments[1].text) > 0

    @patch("asr.service.get_config")
    def test_empty_text(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"enabled": True, "model": "test", "device": "cpu"}}
        svc = ASRService()
        segments = svc._merge_asr_diarize(
            "",
            [{"start": 0.0, "end": 3.0, "speaker": "SPEAKER_00"}],
        )
        assert len(segments) == 1
        assert segments[0].text == ""


class TestASRServiceDiarize:
    @patch("asr.service.get_config")
    def test_transcribe_with_diarize_enabled(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"enabled": True, "model": "test", "device": "cpu"}}
        svc = ASRService()
        mock_model = MagicMock()
        mock_model.generate.return_value = [{"text": "ETC鎵ｈ垂寮傚父", "confidence": 0.95}]
        svc._model = mock_model

        mock_diarizer = MagicMock()
        mock_diarizer.enabled = True
        mock_diarizer.diarize.return_value = [
            {"start": 0.0, "end": 2.0, "speaker": "SPEAKER_00"},
        ]
        svc._diarizer = mock_diarizer

        import os
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name
        try:
            with patch("asr.service.get_business_config", return_value=None):
                result = svc.transcribe(tmp_path, enable_diarize=True)
            assert len(result.segments) == 1
            assert result.segments[0].speaker == "SPEAKER_00"
        finally:
            os.unlink(tmp_path)

    @patch("asr.service.get_config")
    def test_transcribe_diarize_disabled(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"enabled": True, "model": "test", "device": "cpu"}}
        svc = ASRService()
        mock_model = MagicMock()
        mock_model.generate.return_value = [{"text": "ETC鎵ｈ垂寮傚父", "confidence": 0.95}]
        svc._model = mock_model

        mock_diarizer = MagicMock()
        mock_diarizer.enabled = False
        svc._diarizer = mock_diarizer

        import os
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name
        try:
            with patch("asr.service.get_business_config", return_value=None):
                result = svc.transcribe(tmp_path)
            assert result.segments == []
        finally:
            os.unlink(tmp_path)

    @patch("asr.service.get_config")
    def test_transcribe_diarize_failure_graceful(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"enabled": True, "model": "test", "device": "cpu"}}
        svc = ASRService()
        mock_model = MagicMock()
        mock_model.generate.return_value = [{"text": "ETC鎵ｈ垂寮傚父", "confidence": 0.95}]
        svc._model = mock_model

        mock_diarizer = MagicMock()
        mock_diarizer.enabled = True
        mock_diarizer.diarize.side_effect = RuntimeError("pipeline error")
        svc._diarizer = mock_diarizer

        import os
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name
        try:
            with patch("asr.service.get_business_config", return_value=None):
                result = svc.transcribe(tmp_path)
            assert result.text == "ETC鎵ｈ垂寮傚父"
            assert result.segments == []
        finally:
            os.unlink(tmp_path)

    @patch("asr.service.get_config")
    def test_health_includes_diarize(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"enabled": True, "model": "test", "device": "cpu"}}
        svc = ASRService()
        mock_diarizer = MagicMock()
        mock_diarizer.enabled = True
        svc._diarizer = mock_diarizer

        h = svc.health()
        assert h.diarize_enabled is True