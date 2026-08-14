import threading

from utils.config import get_config
from utils.logger import get_logger

logger = get_logger("asr.diarizer")


class SpeakerDiarizer:
    def __init__(self):
        cfg = get_config().get("asr", {}).get("diarize", {})
        self._enabled = cfg.get("enabled", False)
        self._model_name = cfg.get("model", "pyannote/speaker-diarization-community-1")
        self._hf_token = cfg.get("hf_token", "")
        self._device = cfg.get("device", "cuda")
        self._num_speakers = cfg.get("num_speakers", None)
        self._min_speakers = cfg.get("min_speakers", None)
        self._max_speakers = cfg.get("max_speakers", None)
        self._pipeline = None
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _load_pipeline(self):
        if self._pipeline is not None:
            return

        with self._lock:
            if self._pipeline is not None:
                return

            try:
                from pyannote.audio import Pipeline
            except ImportError as e:
                raise RuntimeError(
                    f"pyannote.audio瀵煎叆澶辫触: {e}锛岃杩愯: pip install pyannote.audio"
                )

            import torch

            logger.info(f"鍔犺浇璇磋瘽浜哄垎绂绘ā鍨? {self._model_name}, device={self._device}")

            if not self._hf_token:
                self._hf_token = get_config().get("asr", {}).get("diarize", {}).get(
                    "hf_token", ""
                )

            self._pipeline = Pipeline.from_pretrained(
                self._model_name,
                use_auth_token=self._hf_token if self._hf_token else None,
            )

            if torch.cuda.is_available() and self._device == "cuda":
                self._pipeline.to(torch.device("cuda"))
                logger.info("璇磋瘽浜哄垎绂绘ā鍨嬪凡鍔犺浇鍒癎PU")
            else:
                logger.info("璇磋瘽浜哄垎绂绘ā鍨嬪凡鍔犺浇鍒癈PU")

    def diarize(self, audio_path: str) -> list[dict]:
        if not self._enabled:
            return []

        self._load_pipeline()

        kwargs = {}
        if self._num_speakers:
            kwargs["num_speakers"] = self._num_speakers
        if self._min_speakers:
            kwargs["min_speakers"] = self._min_speakers
        if self._max_speakers:
            kwargs["max_speakers"] = self._max_speakers

        diarization = self._pipeline(audio_path, **kwargs)

        segments = []
        for turn, speaker in diarization.itertracks():
            segments.append({
                "start": round(turn.start, 2),
                "end": round(turn.end, 2),
                "speaker": speaker,
            })

        logger.info(f"璇磋瘽浜哄垎绂诲畬鎴? {len(segments)}娈? {len(set(s['speaker'] for s in segments))}浣嶈璇濅汉")
        return segments

    def health(self) -> dict:
        return {
            "enabled": self._enabled,
            "model": self._model_name,
            "loaded": self._pipeline is not None,
            "device": self._device,
        }

    def reload(self):
        with self._lock:
            self._pipeline = None
        logger.info("璇磋瘽浜哄垎绂绘ā鍨嬪凡鍗歌浇锛屼笅娆¤皟鐢ㄦ椂閲嶆柊鍔犺浇")


_diarizer: SpeakerDiarizer | None = None


def get_diarizer() -> SpeakerDiarizer:
    global _diarizer
    if _diarizer is None:
        _diarizer = SpeakerDiarizer()
    return _diarizer