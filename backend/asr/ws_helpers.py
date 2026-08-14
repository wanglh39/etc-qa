import os
import re
import tempfile
from collections import deque

from utils.logger import get_logger

logger = get_logger("asr.websocket")

_GREETING_PATTERNS = re.compile(
    r"^(浣犲ソ|鎮ㄥソ|鍠倈涓轰綘濂絴涓轰綘|鍡瘄鍝巪閭ｄ釜|灏辨槸|鎴戞兂闂竴涓媩璇烽棶涓€涓媩涓嶅ソ鎰忔€潀鎵撴壈浜唡鍦ㄥ悧)[鍟婂悧鍚у憿鍝囧摝鍛€]*[锛屻€傦紵锛併€侊紱锛氣€*$"
)

_CORRECTION_PATTERNS = re.compile(
    r"^(涓嶅|涓嶆槸|鎼為敊浜唡璇撮敊浜唡涓嶅ソ鎰忔€潀绾犳涓€涓媩鏇存涓€涓媩鎴戦噸璇磡閲嶆柊璇?"
)

_PRONOUN_PATTERNS = re.compile(
    r"(閭ｄ釜|杩欎釜|瀹億浠東濂箌涓婇潰|鍒氭墠|鍓嶈竟|鍓嶉潰|鍒氬垰璇寸殑|鍒氬垰鎻愬埌鐨?"
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
        logger.error(f"娴佸紡妫€绱㈠け璐? {e}")
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
        logger.warning(f"娴佸紡璇磋瘽浜哄垎绂诲け璐? {e}")
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