import asyncio
import json
import threading
import time
from abc import ABC, abstractmethod
from collections import deque

from asr.models import ASRResponse, SpeakerSegment
from utils.config import get_config
from utils.config_center import get_business_config
from utils.logger import get_logger

logger = get_logger("asr.streaming")


class StreamingCallback:
    def on_partial(self, text: str):
        pass

    def on_final(self, text: str, is_end: bool = False):
        pass

    def on_error(self, error: str):
        pass


class StreamingBackend(ABC):
    @abstractmethod
    def start(self, callback: StreamingCallback):
        pass

    @abstractmethod
    def send_audio(self, chunk: bytes):
        pass

    @abstractmethod
    def stop(self):
        pass

    def warmup(self):
        pass


class LocalStreamingBackend(StreamingBackend):
    def __init__(self, model_name: str = "paraformer-zh-streaming", device: str = "cpu", hotwords: list | None = None):
        self._model_name = model_name
        self._device = device
        self._hotwords = hotwords or []
        self._model = None
        self._callback = None
        self._chunk_size = 960
        self._encoder_lookback = 640
        self._decoder_lookback = 880
        self._cache = {}
        self._running = False
        self._audio_buffer = deque()
        self._lock = threading.Lock()

    def _load_model(self):
        if self._model is not None:
            return
        try:
            from funasr import AutoModel
        except ImportError as e:
            raise RuntimeError(f"funasr导入失败: {e}")
        logger.info(f"加载流式ASR模型: {self._model_name}, device={self._device}")
        self._model = AutoModel(model=self._model_name, device=self._device)
        self._cache = {}
        logger.info("流式ASR模型加载完成")

    def warmup(self):
        self._load_model()

    def start(self, callback: StreamingCallback):
        self._load_model()
        self._callback = callback
        self._running = True
        self._cache = {}
        self._audio_buffer.clear()

    def send_audio(self, chunk: bytes):
        if not self._running or self._model is None:
            return

        import numpy as np

        audio_data = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0

        is_final = False
        generate_kwargs = {
            "input": audio_data,
            "cache": self._cache,
            "is_final": is_final,
            "chunk_size": [5, 10, 5],
            "encoder_chunk_lookback": self._encoder_lookback,
            "decoder_chunk_lookback": self._decoder_lookback,
        }
        if self._hotwords:
            generate_kwargs["hotword"] = " ".join(self._hotwords)
        result = self._model.generate(**generate_kwargs)

        if result and len(result) > 0:
            text = result[0].get("text", "").strip()
            if text and self._callback:
                if is_final:
                    self._callback.on_final(text, is_end=False)
                else:
                    self._callback.on_partial(text)

    def stop(self):
        self._running = False
        if self._model and self._cache is not None:
            import numpy as np

            audio_data = np.zeros(1, dtype=np.float32)
            result = self._model.generate(
                input=audio_data,
                cache=self._cache,
                is_final=True,
                chunk_size=[5, 10, 5],
                encoder_chunk_lookback=self._encoder_lookback,
                decoder_chunk_lookback=self._decoder_lookback,
            )
            if result and len(result) > 0:
                text = result[0].get("text", "").strip()
                if text and self._callback:
                    self._callback.on_final(text, is_end=True)
        self._cache = {}


class PseudoStreamingBackend(StreamingBackend):
    def __init__(
        self,
        model_name: str = "FunAudioLLM/Fun-ASR-Nano-2512",
        device: str = "cuda",
        hotwords: list | None = None,
        sample_rate: int = 16000,
        silence_threshold: float = 0.01,
        silence_duration_ms: int = 500,
        min_utterance_ms: int = 300,
    ):
        self._model_name = model_name
        self._device = device
        self._hotwords = hotwords or []
        self._sample_rate = sample_rate
        self._silence_threshold = silence_threshold
        self._silence_duration_ms = silence_duration_ms
        self._min_utterance_ms = min_utterance_ms
        self._model = None
        self._callback = None
        self._running = False
        self._audio_buffer = bytearray()
        self._silence_samples = 0
        self._lock = threading.Lock()

    def _load_model(self):
        if self._model is not None:
            return
        try:
            from funasr import AutoModel
        except ImportError as e:
            raise RuntimeError(f"funasr导入失败: {e}")
        logger.info(f"加载伪流式ASR模型: {self._model_name}, device={self._device}")
        self._model = AutoModel(model=self._model_name, device=self._device)
        logger.info("伪流式ASR模型加载完成")

    def warmup(self):
        self._load_model()

    def start(self, callback: StreamingCallback):
        self._load_model()
        self._callback = callback
        self._running = True
        self._audio_buffer = bytearray()
        self._silence_samples = 0

    def _process_utterance(self):
        if not self._audio_buffer:
            return
        min_bytes = self._min_utterance_ms * self._sample_rate * 2 // 1000
        if len(self._audio_buffer) < min_bytes:
            self._audio_buffer = bytearray()
            self._silence_samples = 0
            return

        import os
        import tempfile

        import numpy as np
        import soundfile as sf

        audio_np = np.frombuffer(bytes(self._audio_buffer), dtype=np.int16).astype(np.float32) / 32768.0
        tmp_path = os.path.join(tempfile.gettempdir(), f"pseudo_asr_{threading.get_ident()}.wav")
        sf.write(tmp_path, audio_np, self._sample_rate, subtype="PCM_16")

        try:
            kwargs = {"input": tmp_path}
            if self._hotwords:
                kwargs["hotword"] = " ".join(self._hotwords)
            result = self._model.generate(**kwargs)
            if result and len(result) > 0:
                text = result[0].get("text", "").strip()
                if text and self._callback:
                    self._callback.on_final(text, is_end=False)
        except Exception as e:
            logger.error(f"伪流式识别失败: {e}")
            if self._callback:
                self._callback.on_error(str(e))
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

        self._audio_buffer = bytearray()
        self._silence_samples = 0

    def send_audio(self, chunk: bytes):
        if not self._running or self._model is None:
            return

        import numpy as np

        with self._lock:
            self._audio_buffer.extend(chunk)
            audio_np = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
            rms = np.sqrt(np.mean(audio_np**2)) if len(audio_np) > 0 else 0.0

            if rms < self._silence_threshold:
                self._silence_samples += len(audio_np)
            else:
                self._silence_samples = 0

            silence_threshold_samples = self._silence_duration_ms * self._sample_rate // 1000
            if self._silence_samples >= silence_threshold_samples:
                self._process_utterance()

    def stop(self):
        self._running = False
        with self._lock:
            if self._audio_buffer:
                self._process_utterance()
        if self._callback:
            self._callback.on_final("", is_end=True)


class AliCloudStreamingBackend(StreamingBackend):
    def __init__(
        self,
        app_key: str,
        access_key_id: str,
        access_key_secret: str,
        sample_rate: int = 16000,
        format: str = "pcm",
        hotwords_id: str = "",
    ):
        self._app_key = app_key
        self._access_key_id = access_key_id
        self._access_key_secret = access_key_secret
        self._sample_rate = sample_rate
        self._format = format
        self._hotwords_id = hotwords_id
        self._callback = None
        self._running = False
        self._ws = None
        self._ws_thread = None
        self._task_id = ""
        self._token = None
        self._token_expire = 0
        self._connected = threading.Event()


    def _get_token(self) -> str:
        import json as _json

        from aliyunsdkcore.client import AcsClient
        from aliyunsdkcore.profile import region_provider
        from aliyunsdkcore.request import RpcRequest

        if self._token and time.time() < self._token_expire - 60:
            return self._token

        region_provider.modify_point("nls-meta", "cn-shanghai", "nls-meta.cn-shanghai.aliyuncs.com")
        client = AcsClient(self._access_key_id, self._access_key_secret, "cn-shanghai")
        req = RpcRequest("nls-meta", "2019-02-28", "CreateToken")
        resp = client.do_action_with_exception(req)
        result = _json.loads(resp)
        self._token = result.get("Token", {}).get("Id", "")
        self._token_expire = result.get("Token", {}).get("ExpireTime", 0)
        logger.info(
            f"阿里云NLS Token获取成功, 有效期至 {time.strftime('%H:%M:%S', time.localtime(self._token_expire))}"
        )
        return self._token

    def start(self, callback: StreamingCallback):
        self._callback = callback
        self._running = True
        self._task_id = __import__("uuid").uuid4().hex
        self._connected.clear()

        token = self._get_token()
        url = f"wss://nls-gateway.cn-shanghai.aliyuncs.com/ws/v1?token={token}"

        import websocket

        self._ws = websocket.WebSocketApp(
            url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )
        self._ws_thread = threading.Thread(target=self._ws.run_forever, daemon=True)
        self._ws_thread.start()

        if not self._connected.wait(timeout=5):
            logger.warning("阿里云ASR连接超时, 继续等待")

    def _on_open(self, ws):
        logger.info(f"阿里云流式ASR连接成功: app_key={self._app_key[:8]}...")
        msg = {
            "header": {
                "message_id": __import__("uuid").uuid4().hex,
                "task_id": self._task_id,
                "namespace": "SpeechTranscriber",
                "name": "StartTranscription",
                "appkey": self._app_key,
            },
            "payload": {
                "sample_rate": self._sample_rate,
                "format": self._format,
                "enable_intermediate_result": True,
                "enable_punctuation_prediction": True,
                "enable_inverse_text_normalization": True,
            },
        }
        if self._hotwords_id:
            msg["payload"]["hotwords_id"] = self._hotwords_id
            logger.info(f"使用热词表: {self._hotwords_id}")
        ws.send(json.dumps(msg))
        self._connected.set()


    def send_audio(self, chunk: bytes):
        if not self._running and self._callback:
            logger.info("阿里云ASR连接断开，自动重连")
            self._reconnect()
            return
        if not self._ws:
            return
        try:
            import websocket

            self._ws.send(chunk, opcode=websocket.ABNF.OPCODE_BINARY)

        except Exception as e:
            logger.error(f"阿里云ASR发送音频失败: {e}")

    def _reconnect(self):
        self._running = True
        self._task_id = __import__("uuid").uuid4().hex
        self._connected.clear()
        token = self._get_token()
        url = f"wss://nls-gateway.cn-shanghai.aliyuncs.com/ws/v1?token={token}"
        import websocket

        self._ws = websocket.WebSocketApp(
            url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )
        self._ws_thread = threading.Thread(target=self._ws.run_forever, daemon=True)
        self._ws_thread.start()

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            header = data.get("header", {})
            name = header.get("name", "")
            status = header.get("status", 0)

            if status != 20000000:
                err = header.get("status_text", "未知错误")
                if status == 40000004:
                    logger.warning(f"阿里云ASR空闲超时(正常): {err}")
                else:
                    logger.error(f"阿里云ASR错误: status={status}, msg={err}")
                    if self._callback:
                        self._callback.on_error(err)
                return

            payload = data.get("payload", {})
            result = payload.get("result", "")

            if name == "TranscriptionResultChanged" or name == "TranscriptionResult":
                is_end = payload.get("isSentenceEnd", False)
                if is_end:
                    if self._callback:
                        self._callback.on_final(result)
                else:
                    if self._callback:
                        self._callback.on_partial(result)
            elif name == "SentenceEnd":
                if self._callback:
                    self._callback.on_final(result)
            elif name == "SentenceBegin":
                pass
            elif name == "TranscriptionCompleted":
                if self._callback:
                    self._callback.on_final("", is_end=True)
        except Exception as e:
            logger.error(f"阿里云ASR解析消息失败: {e}")

    def _on_error(self, ws, error):
        logger.error(f"阿里云ASR WebSocket错误: {error}")
        if self._callback:
            self._callback.on_error(str(error))

    def _on_close(self, ws, close_status, close_msg):
        logger.info(f"阿里云ASR连接关闭: status={close_status}")
        self._running = False

    def stop(self):
        self._running = False
        if self._ws:
            msg = {
                "header": {
                    "message_id": __import__("uuid").uuid4().hex,
                    "task_id": self._task_id,
                    "namespace": "SpeechTranscriber",
                    "name": "StopTranscription",
                    "appkey": self._app_key,
                },
            }
            try:
                self._ws.send(json.dumps(msg))
            except Exception:
                pass
            self._ws.close()
        if self._callback:
            self._callback.on_final("", is_end=True)
        logger.info("阿里云流式ASR连接关闭")


class StreamingASRService:
    def __init__(self):
        cfg = get_config().get("asr", {}).get("streaming", {})
        self._enabled = cfg.get("enabled", False)
        self._mode = cfg.get("mode", "local")
        self._device = cfg.get("device", "cpu")
        self._local_model = cfg.get("local_model", "paraformer-zh-streaming")
        self._hotwords = cfg.get("hotwords", [])
        self._alicloud = cfg.get("alicloud", {})
        self._backend: StreamingBackend | None = None
        self._lock = threading.Lock()
        asr_cfg = get_config().get("asr", {})
        self._offline_model = asr_cfg.get("model", "FunAudioLLM/Fun-ASR-Nano-2512")
        self._offline_device = asr_cfg.get("device", "cuda")
        self._sample_rate = asr_cfg.get("sample_rate", 16000)
        self._silence_threshold = cfg.get("silence_threshold", 0.01)
        self._silence_duration_ms = cfg.get("silence_duration_ms", 500)
        self._min_utterance_ms = cfg.get("min_utterance_ms", 300)

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def mode(self) -> str:
        return self._mode

    def _create_backend(self) -> StreamingBackend:
        if self._mode == "pseudo":
            return PseudoStreamingBackend(
                model_name=self._offline_model,
                device=self._offline_device,
                hotwords=self._hotwords,
                sample_rate=self._sample_rate,
                silence_threshold=self._silence_threshold,
                silence_duration_ms=self._silence_duration_ms,
                min_utterance_ms=self._min_utterance_ms,
            )
        if self._mode == "alicloud":
            return AliCloudStreamingBackend(
                app_key=self._alicloud.get("app_key", ""),
                access_key_id=self._alicloud.get("access_key_id", ""),
                access_key_secret=self._alicloud.get("access_key_secret", ""),
                sample_rate=self._alicloud.get("sample_rate", 16000),
                format=self._alicloud.get("format", "pcm"),
                hotwords_id=self._alicloud.get("hotwords_id", ""),
            )
        return LocalStreamingBackend(
            model_name=self._local_model,
            device=self._device,
            hotwords=self._hotwords,
        )

    def warmup(self):
        if not self._enabled:
            logger.info("流式ASR未启用，跳过预热")
            return
        try:
            with self._lock:
                if self._backend is None:
                    self._backend = self._create_backend()
                    logger.info(f"预热流式ASR backend: mode={self._mode}")
                else:
                    logger.info(f"流式ASR backend已存在，跳过创建: mode={self._mode}")
                t0 = time.time()
                self._backend.warmup()
                elapsed_ms = int((time.time() - t0) * 1000)
                logger.info(f"流式ASR模型预热完成: mode={self._mode}, 耗时={elapsed_ms}ms")
        except Exception as e:
            logger.warning(f"流式ASR模型预热失败，退化为懒加载: {e}")

    def start_stream(self, callback: StreamingCallback):
        if not self._enabled:
            raise RuntimeError("流式ASR未启用")

        with self._lock:
            if self._backend is None:
                self._backend = self._create_backend()
                logger.info("创建新backend实例")
            else:
                logger.info("复用已有backend实例")
            self._backend.start(callback)
        logger.info(f"流式ASR启动: mode={self._mode}")

    def send_audio(self, chunk: bytes):
        if self._backend:
            self._backend.send_audio(chunk)

    def stop_stream(self):
        if self._backend:
            self._backend.stop()
        logger.info("流式ASR停止")

    def health(self) -> dict:
        return {
            "enabled": self._enabled,
            "mode": self._mode,
            "backend": type(self._backend).__name__ if self._backend else None,
        }


_streaming_service: StreamingASRService | None = None
_streaming_config_sig: dict | None = None


def get_streaming_service() -> StreamingASRService:
    global _streaming_service, _streaming_config_sig
    current_cfg = get_config().get("asr", {}).get("streaming", {})
    if _streaming_service is None or _streaming_config_sig != current_cfg:
        _streaming_service = StreamingASRService()
        _streaming_config_sig = current_cfg
    return _streaming_service
