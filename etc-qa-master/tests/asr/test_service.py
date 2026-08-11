import builtins
import sys
from unittest.mock import MagicMock, patch

import asr.service as svc_module
from asr.service import ASRService, _apply_corrections, _load_corrections, get_asr_service


class TestApplyCorrections:
    def test_replaces_words(self):
        result = _apply_corrections("解忧ETC扣费异常", {"解忧": "解悠"})
        assert result == "解悠ETC扣费异常"

    def test_no_corrections(self):
        result = _apply_corrections("ETC扣费异常", {})
        assert result == "ETC扣费异常"


class TestLoadCorrections:
    def test_from_business_config(self):
        with patch("asr.service.get_business_config", return_value={"解忧": "解悠"}), \
             patch("asr.service.get_config", return_value={}):
            result = _load_corrections()
            assert result == {"解忧": "解悠"}

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
            assert "ASR未启用" in str(e)

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
        mock_model.generate.return_value = [{"text": "解忧ETC扣费异常", "confidence": 0.95}]
        svc._model = mock_model

        with patch("asr.service.get_business_config", return_value={"解忧": "解悠"}):
            import os
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                tmp_path = f.name
            try:
                result = svc.transcribe(tmp_path)
                assert "解悠" in result.text
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
        mock_model.generate.return_value = [{"text": "ETC问题"}]
        svc._model = mock_model

        with patch("asr.service.get_business_config", return_value=None):
            import os
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                tmp_path = f.name
            try:
                result = svc.transcribe(tmp_path)
                assert result.text == "ETC问题"
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
                assert "vLLM模式导入失败" in str(e)

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
                assert "funasr导入失败" in str(e)


class TestGetASRService:
    def test_singleton(self):
        svc_module._asr_service = None
        with patch("asr.service.get_config", return_value={"asr": {"enabled": False}}):
            s1 = get_asr_service()
            s2 = get_asr_service()
            assert s1 is s2
