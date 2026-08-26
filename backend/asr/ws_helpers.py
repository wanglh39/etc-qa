import os
import re
import tempfile
from collections import deque

from utils.logger import get_logger

logger = get_logger("asr.websocket")

_GREETING_PATTERNS = re.compile(
    r"^(你好|您好|喂|为你好|为你|嗯|哎|那个|就是|我想问一下|请问一下|不好意思|打扰了|在吗)[啊吗吧呢哇哦呀]*[，。？！、；：…]*$"
)

_CORRECTION_PATTERNS = re.compile(
    r"^(不对|不是|搞错了|说错了|不好意思|纠正一下|更正一下|我重说|重新说)"
)

_PRONOUN_PATTERNS = re.compile(
    r"(那个|这个|它|他|她|上面|刚才|前边|前面|刚刚说的|刚刚提到的)"
)


def _is_greeting(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    if len(stripped) <= 2:
        return True
    return bool(_GREETING_PATTERNS.match(stripped))


def _is_correction(text: str) -> bool:
    stripped = text.strip()
    return bool(_CORRECTION_PATTERNS.match(stripped))


def _has_pronoun(text: str) -> bool:
    stripped = text.strip()
    return bool(_PRONOUN_PATTERNS.search(stripped))


def _char_overlap_ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    set_a = set(a)
    set_b = set(b)
    intersection = set_a & set_b
    return len(intersection) / max(len(set_a), len(set_b))


def _do_query(text: str, category_l1: str | None = None) -> dict | None:
    from api.routes import service
    if service is None:
        return None
    try:
        result = service.query(text, category_l1)
        return result.model_dump()
    except Exception as e:
        logger.error(f"流式检索失败: {e}")
        return None


def _do_diarize_segment(audio_buffer: bytes, sample_rate: int) -> list[dict]:
    import numpy as np

    from asr.diarizer import get_diarizer

    diarizer = get_diarizer()
    if not diarizer.enabled:
        return []

    tmp_path = None
    try:
        audio_np = np.frombuffer(audio_buffer, dtype=np.int16).astype(np.float32) / 32768.0

        import soundfile as sf
        fd, tmp_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        sf.write(tmp_path, audio_np, sample_rate)

        return diarizer.diarize(tmp_path)
    except Exception as e:
        logger.warning(f"流式说话人分离失败: {e}")
        return []
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _get_recent_audio(chunks: deque, window_seconds: float, sample_rate: int) -> list[bytes]:
    bytes_per_second = sample_rate * 2
    target_bytes = int(window_seconds * bytes_per_second)
    result = []
    accumulated = 0
    for chunk in reversed(chunks):
        result.append(chunk)
        accumulated += len(chunk)
        if accumulated >= target_bytes:
            break
    return list(reversed(result))


def _extract_channel(audio_bytes: bytes, side: str) -> bytes:
    if len(audio_bytes) < 4:
        return audio_bytes
    import numpy as np
    audio_np = np.frombuffer(audio_bytes, dtype=np.int16)
    if len(audio_np) % 2 != 0:
        return audio_bytes
    stereo = audio_np.reshape(-1, 2)
    channel_idx = 0 if side == "left" else 1
    return stereo[:, channel_idx].tobytes()


def _identify_speaker(
    text: str, all_texts: list[str], speaker_map: dict[str, str]
) -> str | None:
    if not speaker_map:
        return None
    for speaker, label in speaker_map.items():
        if label == "customer":
            return speaker
    return None