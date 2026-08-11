import os
import threading
import time

from asr.models import ASRHealthResponse, ASRResponse
from utils.config import get_config
from utils.config_center import get_business_config
from utils.logger import get_logger

logger = get_logger("asr.service")


def _apply_corrections(text: str, corrections: dict) -> str:
    for wrong, correct in corrections.items():
        text = text.replace(wrong, correct)
    return text


def _load_corrections() -> dict:
    corrections = get_business_config("asr_corrections", None)
    if corrections and isinstance(corrections, dict):
        return corrections
    return get_config().get("asr", {}).get("corrections", {})


class ASRService:
    def __init__(self):
        cfg = get_config().get("asr", {})
        self._enabled = cfg.get("enabled", False)
        self._model_name = cfg.get("model", "FunAudioLLM/Fun-ASR-Nano-2512")
        self._finetuned_path = cfg.get("finetuned_path", "")
        self._max_duration_ms = cfg.get("max_duration_ms", 30000)
        self._sample_rate = cfg.get("sample_rate", 16000)
        self._language = cfg.get("language", "zh")
        self._device = cfg.get("device", "cuda")
        self._use_vllm = cfg.get("use_vllm", False)
        self._tensor_parallel_size = cfg.get("tensor_parallel_size", 1)

        self._model = None
        self._lock = threading.Lock()

    def _get_corrections(self) -> dict:
        return _load_corrections()

    def _load_model(self):
        if self._model is not None:
            return

        with self._lock:
            if self._model is not None:
                return

            model_name = self._finetuned_path if self._finetuned_path else self._model_name

            if self._use_vllm:
                try:
                    from funasr.auto.auto_model_vllm import AutoModelVLLM
                except ImportError as e:
                    raise RuntimeError(f"vLLM模式导入失败: {e}，需要安装: pip install vllm>=0.12.0 funasr")
                logger.info(f"加载ASR模型(vLLM加速): {model_name}, tensor_parallel_size={self._tensor_parallel_size}")
                self._model = AutoModelVLLM(
                    model=model_name,
                    tensor_parallel_size=self._tensor_parallel_size,
                )
            else:
                try:
                    from funasr import AutoModel
                except ImportError as e:
                    raise RuntimeError(f"funasr导入失败(缺{e.name})，请运行: pip install funasr torchaudio")
                import torch
                torch.set_num_threads(1)
                logger.info(f"加载ASR模型: {model_name}, device={self._device}")
                self._model = AutoModel(
                    model=model_name,
                    device=self._device,
                )

            logger.info(f"ASR模型加载完成: {model_name} (vllm={self._use_vllm})")

    def transcribe(self, audio_path: str) -> ASRResponse:
        if not self._enabled:
            raise RuntimeError("ASR未启用，请在config/asr.yaml中配置asr.enabled=true")

        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")

        self._load_model()

        t0 = time.time()
        result = self._model.generate(input=audio_path)
        elapsed_ms = int((time.time() - t0) * 1000)

        text = ""
        confidence = 1.0
        language = None

        if result and len(result) > 0:
            text = result[0].get("text", "").strip()
            confidence = float(result[0].get("confidence", 1.0))
            language = result[0].get("language")

        corrections = self._get_corrections()
        if corrections:
            text = _apply_corrections(text, corrections)

        duration_ms = elapsed_ms
        model_used = self._finetuned_path if self._finetuned_path else self._model_name

        return ASRResponse(
            text=text,
            confidence=confidence,
            duration_ms=duration_ms,
            model=model_used,
            language=language,
        )

    def health(self) -> ASRHealthResponse:
        return ASRHealthResponse(
            loaded=self._model is not None,
            model=self._finetuned_path if self._finetuned_path else self._model_name,
            device=self._device,
            finetuned=bool(self._finetuned_path),
        )

    def reload(self):
        with self._lock:
            self._model = None
        logger.info("ASR模型已卸载，下次调用时重新加载")


_asr_service: ASRService | None = None


def get_asr_service() -> ASRService:
    global _asr_service
    if _asr_service is None:
        _asr_service = ASRService()
    return _asr_service
