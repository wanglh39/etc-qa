import os
import tempfile
import threading

from utils.config import get_config
from utils.logger import get_logger

logger = get_logger("asr.preprocess")


class AudioPreprocessor:
    def __init__(self):
        cfg = get_config().get("asr", {}).get("preprocess", {})
        self._vad_enabled = cfg.get("vad_enabled", False)
        self._denoise_enabled = cfg.get("denoise_enabled", False)
        self._sample_rate = cfg.get("sample_rate", 16000)
        self._min_speech_duration = cfg.get("min_speech_duration", 0.5)
        self._min_silence_duration = cfg.get("min_silence_duration", 0.3)
        self._speech_pad_ms = cfg.get("speech_pad_ms", 200)
        self._denoise_strength = cfg.get("denoise_strength", 0.03)
        self._lock = threading.Lock()

    @property
    def vad_enabled(self) -> bool:
        return self._vad_enabled

    @property
    def denoise_enabled(self) -> bool:
        return self._denoise_enabled

    def _load_audio(self, audio_path: str):
        import librosa
        import numpy as np
        audio, sr = librosa.load(audio_path, sr=self._sample_rate)
        return audio, sr

    def _save_audio(self, audio, sr: int, path: str):
        import soundfile as sf
        sf.write(path, audio, sr)

    def apply_vad(self, audio, sr: int) -> tuple:
        if not self._vad_enabled:
            return audio, sr

        try:
            import torch
            model, utils = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad",
                trust_repo=True,
            )
            get_speech_timestamps = utils[0]
        except Exception as e:
            logger.warning(f"silero-vad加载失败，跳过VAD: {e}")
            return audio, sr

        import numpy as np
        import torch

        torch.set_num_threads(1)
        audio_tensor = torch.from_numpy(audio).float()

        timestamps = get_speech_timestamps(
            audio_tensor,
            model,
            sampling_rate=sr,
            min_speech_duration_ms=int(self._min_speech_duration * 1000),
            min_silence_duration_ms=int(self._min_silence_duration * 1000),
            speech_pad_ms=self._speech_pad_ms,
        )

        if not timestamps:
            logger.warning("VAD未检测到语音段，返回原始音频")
            return audio, sr

        segments = []
        for ts in timestamps:
            segments.append(audio[ts["start"]:ts["end"]])

        trimmed = np.concatenate(segments) if segments else audio
        original_duration = len(audio) / sr
        trimmed_duration = len(trimmed) / sr
        logger.info(
            f"VAD: {original_duration:.1f}s → {trimmed_duration:.1f}s "
            f"({len(timestamps)}段语音, 去除{original_duration - trimmed_duration:.1f}s静音)"
        )
        return trimmed, sr

    def apply_denoise(self, audio, sr: int) -> tuple:
        if not self._denoise_enabled:
            return audio, sr

        try:
            import noisereduce
        except ImportError as e:
            logger.warning(f"noisereduce未安装，跳过降噪: {e}")
            return audio, sr

        import numpy as np

        if len(audio) < sr:
            logger.warning("音频太短，跳过降噪")
            return audio, sr

        noisy_part = audio[: int(sr * 0.5)]
        reduced = noisereduce.reduce_noise(
            y=audio,
            sr=sr,
            y_noise=noisy_part,
            stationary=False,
            prop_decrease=self._denoise_strength,
        )

        noise_level = np.mean(np.abs(audio - reduced))
        logger.info(f"降噪完成: 噪声水平={noise_level:.4f}")
        return reduced, sr

    def process(self, audio_path: str) -> str:
        if not self._vad_enabled and not self._denoise_enabled:
            return audio_path

        try:
            audio, sr = self._load_audio(audio_path)
        except Exception as e:
            logger.warning(f"音频加载失败，跳过预处理: {e}")
            return audio_path

        audio, sr = self.apply_denoise(audio, sr)
        audio, sr = self.apply_vad(audio, sr)

        suffix = os.path.splitext(audio_path)[1] or ".wav"
        fd, out_path = tempfile.mkstemp(suffix=suffix, prefix="asr_prep_")
        os.close(fd)

        try:
            self._save_audio(audio, sr, out_path)
            logger.info(f"预处理完成: {audio_path} → {out_path}")
            return out_path
        except Exception as e:
            logger.warning(f"预处理音频保存失败: {e}")
            return audio_path

    def cleanup(self, processed_path: str, original_path: str):
        if processed_path != original_path and os.path.exists(processed_path):
            try:
                os.unlink(processed_path)
            except Exception:
                pass

    def health(self) -> dict:
        return {
            "vad_enabled": self._vad_enabled,
            "denoise_enabled": self._denoise_enabled,
        }


_preprocessor: AudioPreprocessor | None = None


def get_preprocessor() -> AudioPreprocessor:
    global _preprocessor
    if _preprocessor is None:
        _preprocessor = AudioPreprocessor()
    return _preprocessor