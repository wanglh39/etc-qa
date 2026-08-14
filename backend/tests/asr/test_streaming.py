from unittest.mock import MagicMock, patch

import asr.streaming as streaming_module
from asr.streaming import (
    AliCloudStreamingBackend,
    LocalStreamingBackend,
    PseudoStreamingBackend,
    StreamingASRService,
    StreamingCallback,
    get_streaming_service,
)


class MockCallback(StreamingCallback):
    def __init__(self):
        self.partials = []
        self.finals = []
        self.errors = []

    def on_partial(self, text: str):
        self.partials.append(text)

    def on_final(self, text: str, is_end: bool = False):
        self.finals.append({"text": text, "is_end": is_end})

    def on_error(self, error: str):
        self.errors.append(error)


class TestStreamingCallback:
    def test_on_partial(self):
        cb = MockCallback()
        cb.on_partial("浣犲ソ")
        assert cb.partials == ["浣犲ソ"]

    def test_on_final(self):
        cb = MockCallback()
        cb.on_final("ETC鎵ｈ垂", is_end=True)
        assert cb.finals == [{"text": "ETC鎵ｈ垂", "is_end": True}]


class TestLocalStreamingBackend:
    @patch("asr.streaming.get_config")
    def test_start_stop(self, mock_cfg):
        mock_cfg.return_value = {"asr": {}}
        backend = LocalStreamingBackend()
        cb = MockCallback()

        mock_model = MagicMock()
        mock_model.generate.return_value = []
        with patch.object(backend, "_load_model"):
            backend._model = mock_model
            backend.start(cb)
            backend.stop()

    @patch("asr.streaming.get_config")
    def test_send_audio_not_running(self, mock_cfg):
        mock_cfg.return_value = {"asr": {}}
        backend = LocalStreamingBackend()
        backend.send_audio(b"\x00" * 100)


class TestAliCloudStreamingBackend:
    def test_start_stop(self):
        backend = AliCloudStreamingBackend(
            app_key="test_key",
            access_key_id="test_id",
            access_key_secret="test_secret",
        )
        cb = MockCallback()
        backend.start(cb)
        backend.stop()
        assert cb.finals[-1]["is_end"] is True

    def test_send_audio_not_running(self):
        backend = AliCloudStreamingBackend(
            app_key="test", access_key_id="test", access_key_secret="test"
        )
        backend.send_audio(b"\x00" * 100)


class TestStreamingASRService:
    @patch("asr.streaming.get_config")
    def test_disabled(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"streaming": {"enabled": False}}}
        svc = StreamingASRService()
        assert svc.enabled is False

    @patch("asr.streaming.get_config")
    def test_enabled_local(self, mock_cfg):
        mock_cfg.return_value = {
            "asr": {"streaming": {"enabled": True, "mode": "local", "device": "cpu"}}
        }
        svc = StreamingASRService()
        assert svc.enabled is True
        assert svc.mode == "local"

    @patch("asr.streaming.get_config")
    def test_enabled_alicloud(self, mock_cfg):
        mock_cfg.return_value = {
            "asr": {
                "streaming": {
                    "enabled": True,
                    "mode": "alicloud",
                    "alicloud": {
                        "app_key": "test",
                        "access_key_id": "test",
                        "access_key_secret": "test",
                    },
                }
            }
        }
        svc = StreamingASRService()
        assert svc.mode == "alicloud"

    @patch("asr.streaming.get_config")
    def test_start_stream_disabled_raises(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"streaming": {"enabled": False}}}
        svc = StreamingASRService()
        try:
            svc.start_stream(MockCallback())
            assert False
        except RuntimeError as e:
            assert "鏈惎鐢? in str(e)

    @patch("asr.streaming.get_config")
    def test_health(self, mock_cfg):
        mock_cfg.return_value = {
            "asr": {"streaming": {"enabled": True, "mode": "local"}}
        }
        svc = StreamingASRService()
        h = svc.health()
        assert h["enabled"] is True
        assert h["mode"] == "local"

    @patch("asr.streaming.get_config")
    def test_start_stream_reuses_backend(self, mock_cfg):
        mock_cfg.return_value = {
            "asr": {"streaming": {"enabled": True, "mode": "local"}}
        }
        svc = StreamingASRService()
        mock_backend = MagicMock()
        svc._create_backend = MagicMock(return_value=mock_backend)
        cb1 = MockCallback()
        cb2 = MockCallback()
        svc.start_stream(cb1)
        first_backend = svc._backend
        svc.start_stream(cb2)
        second_backend = svc._backend
        assert first_backend is second_backend
        assert svc._create_backend.call_count == 1

    @patch("asr.streaming.get_config")
    def test_stop_stream_preserves_backend(self, mock_cfg):
        mock_cfg.return_value = {
            "asr": {"streaming": {"enabled": True, "mode": "local"}}
        }
        svc = StreamingASRService()
        mock_backend = MagicMock()
        svc._create_backend = MagicMock(return_value=mock_backend)
        svc.start_stream(MockCallback())
        assert svc._backend is not None
        svc.stop_stream()
        assert svc._backend is not None
        assert svc._backend is mock_backend
        mock_backend.stop.assert_called_once()

    @patch("asr.streaming.get_config")
    def test_start_stream_creates_backend_only_once_across_stop(self, mock_cfg):
        mock_cfg.return_value = {
            "asr": {"streaming": {"enabled": True, "mode": "local"}}
        }
        svc = StreamingASRService()
        mock_backend = MagicMock()
        svc._create_backend = MagicMock(return_value=mock_backend)
        svc.start_stream(MockCallback())
        svc.stop_stream()
        svc.start_stream(MockCallback())
        assert svc._create_backend.call_count == 1
        assert svc._backend is mock_backend


class TestGetStreamingService:
    def test_singleton(self):
        streaming_module._streaming_service = None
        streaming_module._streaming_config_sig = None
        with patch("asr.streaming.get_config", return_value={"asr": {}}):
            s1 = get_streaming_service()
            s2 = get_streaming_service()
            assert s1 is s2

    def test_recreates_on_config_change(self):
        streaming_module._streaming_service = None
        streaming_module._streaming_config_sig = None
        with patch("asr.streaming.get_config", return_value={"asr": {"streaming": {"enabled": False}}}):
            s1 = get_streaming_service()
            assert s1.enabled is False
        with patch("asr.streaming.get_config", return_value={"asr": {"streaming": {"enabled": True}}}):
            s2 = get_streaming_service()
            assert s2.enabled is True
            assert s1 is not s2


class TestLocalStreamingLoadModel:
    @patch("asr.streaming.get_config")
    def test_load_model_success(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"streaming": {"local_model": "fake", "device": "cpu"}}}
        backend = LocalStreamingBackend()
        with patch("funasr.AutoModel") as mock_auto:
            mock_auto.return_value = MagicMock()
            backend._load_model()
        assert backend._model is not None

    @patch("asr.streaming.get_config")
    def test_load_model_already_loaded(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"streaming": {}}}
        backend = LocalStreamingBackend()
        backend._model = MagicMock()
        backend._load_model()
        assert backend._model is not None

    @patch("asr.streaming.get_config")
    def test_load_model_import_error(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"streaming": {}}}
        backend = LocalStreamingBackend()
        import builtins
        real_import = builtins.__import__
        def mock_import(name, *args, **kwargs):
            if name == "funasr":
                raise ImportError("not installed")
            return real_import(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=mock_import):
            try:
                backend._load_model()
                assert False
            except RuntimeError as e:
                assert "funasr" in str(e)


class TestLocalStreamingSendAudio:
    @patch("asr.streaming.get_config")
    def test_send_audio_with_result(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"streaming": {"local_model": "fake", "device": "cpu"}}}
        backend = LocalStreamingBackend()
        backend._model = MagicMock()
        backend._model.generate.return_value = [{"text": "ETC鎵ｈ垂"}]
        backend._running = True
        cb = MockCallback()
        backend._callback = cb

        with patch("numpy.frombuffer") as mock_np:
            mock_np.return_value = MagicMock()
            mock_np.return_value.astype.return_value = MagicMock()
            backend.send_audio(b"\x00" * 3200)
        assert len(cb.partials) >= 1

    @patch("asr.streaming.get_config")
    def test_send_audio_empty_result(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"streaming": {}}}
        backend = LocalStreamingBackend()
        backend._model = MagicMock()
        backend._model.generate.return_value = []
        backend._running = True
        cb = MockCallback()
        backend._callback = cb

        with patch("numpy.frombuffer") as mock_np:
            mock_np.return_value = MagicMock()
            mock_np.return_value.astype.return_value = MagicMock()
            backend.send_audio(b"\x00" * 3200)
        assert len(cb.partials) == 0

    @patch("asr.streaming.get_config")
    def test_send_audio_with_hotwords(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"streaming": {}}}
        backend = LocalStreamingBackend(hotwords=["ETC", "OBU"])
        backend._model = MagicMock()
        backend._model.generate.return_value = []
        backend._running = True

        with patch("numpy.frombuffer") as mock_np:
            mock_np.return_value = MagicMock()
            mock_np.return_value.astype.return_value = MagicMock()
            backend.send_audio(b"\x00" * 3200)
        kwargs = backend._model.generate.call_args[1]
        assert "hotword" in kwargs


class TestLocalStreamingStop:
    @patch("asr.streaming.get_config")
    def test_stop_with_model_and_cache(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"streaming": {}}}
        backend = LocalStreamingBackend()
        backend._model = MagicMock()
        backend._model.generate.return_value = [{"text": "final"}]
        backend._running = True
        backend._cache = {}
        cb = MockCallback()
        backend._callback = cb

        with patch("numpy.zeros", return_value=MagicMock()):
            backend.stop()
        assert backend._running is False
        assert len(cb.finals) >= 1

    @patch("asr.streaming.get_config")
    def test_stop_no_model(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"streaming": {}}}
        backend = LocalStreamingBackend()
        backend._running = True
        backend.stop()
        assert backend._running is False


class TestStreamingBackendWarmup:
    @patch("asr.streaming.get_config")
    def test_local_backend_warmup_calls_load_model(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"streaming": {}}}
        backend = LocalStreamingBackend()
        with patch.object(backend, "_load_model") as mock_load:
            backend.warmup()
            mock_load.assert_called_once()

    @patch("asr.streaming.get_config")
    def test_pseudo_backend_warmup_calls_load_model(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"streaming": {}}}
        backend = PseudoStreamingBackend()
        with patch.object(backend, "_load_model") as mock_load:
            backend.warmup()
            mock_load.assert_called_once()

    def test_alicloud_backend_warmup_noop(self):
        backend = AliCloudStreamingBackend(
            app_key="test", access_key_id="test", access_key_secret="test"
        )
        backend.warmup()


class TestStreamingASRServiceWarmup:
    @patch("asr.streaming.get_config")
    def test_warmup_disabled_skips(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"streaming": {"enabled": False}}}
        svc = StreamingASRService()
        svc.warmup()
        assert svc._backend is None

    @patch("asr.streaming.get_config")
    def test_warmup_creates_backend_and_loads_model(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"streaming": {"enabled": True, "mode": "local"}}}
        svc = StreamingASRService()
        mock_backend = MagicMock()
        svc._create_backend = MagicMock(return_value=mock_backend)
        svc.warmup()
        assert svc._backend is mock_backend
        mock_backend.warmup.assert_called_once()

    @patch("asr.streaming.get_config")
    def test_warmup_skips_if_backend_exists(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"streaming": {"enabled": True, "mode": "local"}}}
        svc = StreamingASRService()
        existing = MagicMock()
        svc._backend = existing
        svc._create_backend = MagicMock()
        svc.warmup()
        assert svc._create_backend.call_count == 0
        existing.warmup.assert_called_once()

    @patch("asr.streaming.get_config")
    def test_warmup_failure_does_not_raise(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"streaming": {"enabled": True, "mode": "local"}}}
        svc = StreamingASRService()
        mock_backend = MagicMock()
        mock_backend.warmup.side_effect = RuntimeError("funasr鏈畨瑁?)
        svc._create_backend = MagicMock(return_value=mock_backend)
        svc.warmup()
        assert svc._backend is mock_backend