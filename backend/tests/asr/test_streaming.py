import sys
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

if "funasr" not in sys.modules:
    sys.modules["funasr"] = MagicMock()


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
        cb.on_partial("你好")
        assert cb.partials == ["你好"]

    def test_on_final(self):
        cb = MockCallback()
        cb.on_final("ETC扣费", is_end=True)
        assert cb.finals == [{"text": "ETC扣费", "is_end": True}]


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
        with (
            patch.object(backend, "_get_token", return_value="fake_token"),
            patch("websocket.WebSocketApp"),
        ):
            backend.start(cb)
            backend.stop()
            assert cb.finals[-1]["is_end"] is True

    def test_send_audio_not_running(self):
        backend = AliCloudStreamingBackend(app_key="test", access_key_id="test", access_key_secret="test")
        backend.send_audio(b"\x00" * 100)


class TestStreamingASRService:
    @patch("asr.streaming.get_config")
    def test_disabled(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"streaming": {"enabled": False}}}
        svc = StreamingASRService()
        assert svc.enabled is False

    @patch("asr.streaming.get_config")
    def test_enabled_local(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"streaming": {"enabled": True, "mode": "local", "device": "cpu"}}}
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
            assert "未启用" in str(e)

    @patch("asr.streaming.get_config")
    def test_health(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"streaming": {"enabled": True, "mode": "local"}}}
        svc = StreamingASRService()
        h = svc.health()
        assert h["enabled"] is True
        assert h["mode"] == "local"

    @patch("asr.streaming.get_config")
    def test_start_stream_reuses_backend(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"streaming": {"enabled": True, "mode": "local"}}}
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
        mock_cfg.return_value = {"asr": {"streaming": {"enabled": True, "mode": "local"}}}
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
        mock_cfg.return_value = {"asr": {"streaming": {"enabled": True, "mode": "local"}}}
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
        backend._model.generate.return_value = [{"text": "ETC扣费"}]
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
        backend = AliCloudStreamingBackend(app_key="test", access_key_id="test", access_key_secret="test")
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
        mock_backend.warmup.side_effect = RuntimeError("funasr未安装")
        svc._create_backend = MagicMock(return_value=mock_backend)
        svc.warmup()
        assert svc._backend is mock_backend


class TestPseudoStreamingBackend:
    @patch("asr.streaming.get_config")
    def test_start(self, mock_cfg):
        mock_cfg.return_value = {"asr": {}}
        backend = PseudoStreamingBackend()
        cb = MockCallback()
        with patch.object(backend, "_load_model"):
            backend._model = MagicMock()
            backend.start(cb)
        assert backend._callback is cb
        assert backend._running is True
        assert backend._audio_buffer == bytearray()
        assert backend._silence_samples == 0

    @patch("asr.streaming.get_config")
    def test_send_audio_not_running(self, mock_cfg):
        mock_cfg.return_value = {"asr": {}}
        backend = PseudoStreamingBackend()
        backend._running = False
        backend.send_audio(b"\x00" * 100)

    @patch("asr.streaming.get_config")
    def test_send_audio_no_model(self, mock_cfg):
        mock_cfg.return_value = {"asr": {}}
        backend = PseudoStreamingBackend()
        backend._running = True
        backend._model = None
        backend.send_audio(b"\x00" * 100)


class TestPseudoStreamingLoadModel:
    @patch("asr.streaming.get_config")
    def test_load_model_success(self, mock_cfg):
        mock_cfg.return_value = {"asr": {}}
        backend = PseudoStreamingBackend()
        with patch("funasr.AutoModel") as mock_auto:
            mock_auto.return_value = MagicMock()
            backend._load_model()
        assert backend._model is not None

    @patch("asr.streaming.get_config")
    def test_load_model_already_loaded(self, mock_cfg):
        mock_cfg.return_value = {"asr": {}}
        backend = PseudoStreamingBackend()
        existing = MagicMock()
        backend._model = existing
        backend._load_model()
        assert backend._model is existing

    @patch("asr.streaming.get_config")
    def test_load_model_import_error(self, mock_cfg):
        mock_cfg.return_value = {"asr": {}}
        backend = PseudoStreamingBackend()
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


class TestPseudoStreamingProcessUtterance:
    @patch("asr.streaming.get_config")
    def test_empty_buffer_returns(self, mock_cfg):
        mock_cfg.return_value = {"asr": {}}
        backend = PseudoStreamingBackend()
        backend._audio_buffer = bytearray()
        backend._process_utterance()
        assert backend._audio_buffer == bytearray()

    @patch("asr.streaming.get_config")
    def test_buffer_too_short_clears(self, mock_cfg):
        mock_cfg.return_value = {"asr": {}}
        backend = PseudoStreamingBackend(min_utterance_ms=300, sample_rate=16000)
        backend._audio_buffer = bytearray(b"\x00" * 100)
        backend._silence_samples = 500
        backend._process_utterance()
        assert backend._audio_buffer == bytearray()
        assert backend._silence_samples == 0

    @patch("asr.streaming.get_config")
    def test_with_result_calls_on_final(self, mock_cfg):
        mock_cfg.return_value = {"asr": {}}
        backend = PseudoStreamingBackend(min_utterance_ms=300, sample_rate=16000)
        backend._audio_buffer = bytearray(b"\x00" * 9600)
        backend._model = MagicMock()
        backend._model.generate.return_value = [{"text": "ETC扣费"}]
        cb = MockCallback()
        backend._callback = cb
        with patch("soundfile.write"):
            backend._process_utterance()
        assert len(cb.finals) == 1
        assert cb.finals[0]["text"] == "ETC扣费"
        assert cb.finals[0]["is_end"] is False
        assert backend._audio_buffer == bytearray()
        assert backend._silence_samples == 0

    @patch("asr.streaming.get_config")
    def test_with_hotwords(self, mock_cfg):
        mock_cfg.return_value = {"asr": {}}
        backend = PseudoStreamingBackend(min_utterance_ms=300, sample_rate=16000, hotwords=["ETC", "OBU"])
        backend._audio_buffer = bytearray(b"\x00" * 9600)
        backend._model = MagicMock()
        backend._model.generate.return_value = []
        with patch("soundfile.write"):
            backend._process_utterance()
        kwargs = backend._model.generate.call_args[1]
        assert "hotword" in kwargs
        assert kwargs["hotword"] == "ETC OBU"

    @patch("asr.streaming.get_config")
    def test_exception_calls_on_error(self, mock_cfg):
        mock_cfg.return_value = {"asr": {}}
        backend = PseudoStreamingBackend(min_utterance_ms=300, sample_rate=16000)
        backend._audio_buffer = bytearray(b"\x00" * 9600)
        backend._model = MagicMock()
        backend._model.generate.side_effect = RuntimeError("model error")
        cb = MockCallback()
        backend._callback = cb
        with patch("soundfile.write"):
            backend._process_utterance()
        assert len(cb.errors) == 1
        assert "model error" in cb.errors[0]
        assert backend._audio_buffer == bytearray()

    @patch("asr.streaming.get_config")
    def test_empty_result_text_no_callback(self, mock_cfg):
        mock_cfg.return_value = {"asr": {}}
        backend = PseudoStreamingBackend(min_utterance_ms=300, sample_rate=16000)
        backend._audio_buffer = bytearray(b"\x00" * 9600)
        backend._model = MagicMock()
        backend._model.generate.return_value = [{"text": ""}]
        cb = MockCallback()
        backend._callback = cb
        with patch("soundfile.write"):
            backend._process_utterance()
        assert len(cb.finals) == 0

    @patch("asr.streaming.get_config")
    def test_no_callback_no_error(self, mock_cfg):
        mock_cfg.return_value = {"asr": {}}
        backend = PseudoStreamingBackend(min_utterance_ms=300, sample_rate=16000)
        backend._audio_buffer = bytearray(b"\x00" * 9600)
        backend._model = MagicMock()
        backend._model.generate.return_value = [{"text": "ETC扣费"}]
        backend._callback = None
        with patch("soundfile.write"):
            backend._process_utterance()
        assert backend._audio_buffer == bytearray()


class TestPseudoStreamingSendAudio:
    @patch("asr.streaming.get_config")
    def test_silence_triggers_process_utterance(self, mock_cfg):
        mock_cfg.return_value = {"asr": {}}
        backend = PseudoStreamingBackend(
            sample_rate=16000,
            silence_threshold=0.01,
            silence_duration_ms=100,
            min_utterance_ms=300,
        )
        backend._model = MagicMock()
        backend._running = True
        with patch.object(backend, "_process_utterance") as mock_proc:
            backend.send_audio(b"\x00" * 3200)
            assert mock_proc.call_count == 1

    @patch("asr.streaming.get_config")
    def test_no_silence_does_not_trigger(self, mock_cfg):
        mock_cfg.return_value = {"asr": {}}
        backend = PseudoStreamingBackend(
            sample_rate=16000,
            silence_threshold=0.01,
            silence_duration_ms=500,
        )
        backend._model = MagicMock()
        backend._running = True
        chunk = b"\x00\x40" * 1600
        with patch.object(backend, "_process_utterance") as mock_proc:
            backend.send_audio(chunk)
            assert mock_proc.call_count == 0
        assert backend._silence_samples == 0

    @patch("asr.streaming.get_config")
    def test_partial_silence_accumulates(self, mock_cfg):
        mock_cfg.return_value = {"asr": {}}
        backend = PseudoStreamingBackend(
            sample_rate=16000,
            silence_threshold=0.01,
            silence_duration_ms=100,
        )
        backend._model = MagicMock()
        backend._running = True
        with patch.object(backend, "_process_utterance") as mock_proc:
            backend.send_audio(b"\x00" * 1600)
            assert mock_proc.call_count == 0
            assert backend._silence_samples == 800
            backend.send_audio(b"\x00" * 1600)
            assert mock_proc.call_count == 1

    @patch("asr.streaming.get_config")
    def test_not_running_returns(self, mock_cfg):
        mock_cfg.return_value = {"asr": {}}
        backend = PseudoStreamingBackend()
        backend._running = False
        backend._model = MagicMock()
        backend.send_audio(b"\x00" * 100)

    @patch("asr.streaming.get_config")
    def test_no_model_returns(self, mock_cfg):
        mock_cfg.return_value = {"asr": {}}
        backend = PseudoStreamingBackend()
        backend._running = True
        backend._model = None
        backend.send_audio(b"\x00" * 100)


class TestPseudoStreamingStop:
    @patch("asr.streaming.get_config")
    def test_stop_with_buffer_processes(self, mock_cfg):
        mock_cfg.return_value = {"asr": {}}
        backend = PseudoStreamingBackend()
        backend._running = True
        backend._audio_buffer = bytearray(b"\x00" * 100)
        cb = MockCallback()
        backend._callback = cb
        with patch.object(backend, "_process_utterance") as mock_proc:
            backend.stop()
        assert backend._running is False
        assert mock_proc.call_count == 1
        assert len(cb.finals) == 1
        assert cb.finals[-1]["is_end"] is True

    @patch("asr.streaming.get_config")
    def test_stop_empty_buffer_skips_process(self, mock_cfg):
        mock_cfg.return_value = {"asr": {}}
        backend = PseudoStreamingBackend()
        backend._running = True
        backend._audio_buffer = bytearray()
        cb = MockCallback()
        backend._callback = cb
        with patch.object(backend, "_process_utterance") as mock_proc:
            backend.stop()
        assert backend._running is False
        assert mock_proc.call_count == 0
        assert len(cb.finals) == 1
        assert cb.finals[-1]["is_end"] is True

    @patch("asr.streaming.get_config")
    def test_stop_no_callback(self, mock_cfg):
        mock_cfg.return_value = {"asr": {}}
        backend = PseudoStreamingBackend()
        backend._running = True
        backend._audio_buffer = bytearray()
        backend._callback = None
        backend.stop()
        assert backend._running is False


class TestStreamingASRServiceCreateBackend:
    @patch("asr.streaming.get_config")
    def test_create_backend_alicloud(self, mock_cfg):
        mock_cfg.return_value = {
            "asr": {
                "streaming": {
                    "enabled": True,
                    "mode": "alicloud",
                    "alicloud": {
                        "app_key": "test_key",
                        "access_key_id": "test_id",
                        "access_key_secret": "test_secret",
                        "sample_rate": 8000,
                        "format": "opu",
                    },
                }
            }
        }
        svc = StreamingASRService()
        backend = svc._create_backend()
        assert isinstance(backend, AliCloudStreamingBackend)
        assert backend._app_key == "test_key"
        assert backend._access_key_id == "test_id"
        assert backend._access_key_secret == "test_secret"
        assert backend._sample_rate == 8000
        assert backend._format == "opu"

    @patch("asr.streaming.get_config")
    def test_create_backend_pseudo(self, mock_cfg):
        mock_cfg.return_value = {
            "asr": {
                "streaming": {
                    "enabled": True,
                    "mode": "pseudo",
                    "silence_threshold": 0.02,
                    "silence_duration_ms": 600,
                    "min_utterance_ms": 400,
                },
                "model": "FunAudioLLM/Fun-ASR-Nano-2512",
                "device": "cuda",
                "sample_rate": 16000,
            }
        }
        svc = StreamingASRService()
        backend = svc._create_backend()
        assert isinstance(backend, PseudoStreamingBackend)
        assert backend._model_name == "FunAudioLLM/Fun-ASR-Nano-2512"
        assert backend._device == "cuda"
        assert backend._sample_rate == 16000
        assert backend._silence_threshold == 0.02
        assert backend._silence_duration_ms == 600
        assert backend._min_utterance_ms == 400

    @patch("asr.streaming.get_config")
    def test_create_backend_local(self, mock_cfg):
        mock_cfg.return_value = {
            "asr": {
                "streaming": {
                    "enabled": True,
                    "mode": "local",
                    "local_model": "paraformer-zh-streaming",
                    "device": "cpu",
                    "hotwords": ["ETC"],
                }
            }
        }
        svc = StreamingASRService()
        backend = svc._create_backend()
        assert isinstance(backend, LocalStreamingBackend)
        assert backend._model_name == "paraformer-zh-streaming"
        assert backend._device == "cpu"
        assert backend._hotwords == ["ETC"]


class TestStreamingASRServiceSendAudio:
    @patch("asr.streaming.get_config")
    def test_send_audio_with_backend(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"streaming": {"enabled": True, "mode": "local"}}}
        svc = StreamingASRService()
        mock_backend = MagicMock()
        svc._backend = mock_backend
        chunk = b"\x00" * 100
        svc.send_audio(chunk)
        mock_backend.send_audio.assert_called_once_with(chunk)

    @patch("asr.streaming.get_config")
    def test_send_audio_no_backend(self, mock_cfg):
        mock_cfg.return_value = {"asr": {"streaming": {"enabled": True, "mode": "local"}}}
        svc = StreamingASRService()
        svc._backend = None
        svc.send_audio(b"\x00" * 100)
