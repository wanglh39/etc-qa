import json
import os
import sys
import traceback

os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["ETC_QA_ENV"] = "test"

_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

_cov = None
if os.environ.get("COVERAGE_PROCESS_START"):
    try:
        import coverage
        cov_file = os.environ.get("COVERAGE_FILE", os.path.join(_project_root, ".coverage"))
        _cov = coverage.Coverage(data_file=cov_file, config_file=os.environ["COVERAGE_PROCESS_START"])
        _cov.start()
    except Exception:
        _cov = None

import torch

torch.set_num_threads(1)

ASR_SAMPLES_DIR = os.path.join(_project_root, "data", "asr_samples")


def _run_test(name, func):
    try:
        data = func()
        return {"test": name, "status": "passed", "data": data}
    except Exception as e:
        return {"test": name, "status": "failed", "error": str(e), "traceback": traceback.format_exc()}


def test_model_load():
    from asr.service import ASRService
    svc = ASRService()
    assert svc._enabled is True
    svc._load_model()
    assert svc._model is not None


def test_transcribe_single():
    from asr.service import ASRService
    svc = ASRService()
    metadata_path = os.path.normpath(os.path.join(ASR_SAMPLES_DIR, "metadata.json"))
    with open(metadata_path, encoding="utf-8") as f:
        metadata = json.load(f)
    sample = metadata[0]
    audio_path = os.path.normpath(os.path.join(ASR_SAMPLES_DIR, sample["filename"]))
    assert os.path.exists(audio_path), f"闊抽鏂囦欢涓嶅瓨鍦? {audio_path}"

    result = svc.transcribe(audio_path)
    assert result.text != ""
    assert result.confidence >= 0.0
    assert result.model != ""


def test_batch_accuracy():
    from asr.service import ASRService
    svc = ASRService()
    metadata_path = os.path.normpath(os.path.join(ASR_SAMPLES_DIR, "metadata.json"))
    with open(metadata_path, encoding="utf-8") as f:
        metadata = json.load(f)

    correct = 0
    total = 0
    for sample in metadata[:5]:
        audio_path = os.path.normpath(os.path.join(ASR_SAMPLES_DIR, sample["filename"]))
        if not os.path.exists(audio_path):
            continue
        total += 1
        result = svc.transcribe(audio_path)
        expected = sample["final_question"]
        if expected in result.text or result.text in expected:
            correct += 1
        else:
            for kw in sample.get("keyword", "").split(","):
                if kw and kw in result.text:
                    correct += 1
                    break

    accuracy = correct / total if total > 0 else 0
    assert accuracy >= 0.6, f"ASR鎵归噺璇嗗埆鍑嗙‘鐜噞accuracy:.0%}浣庝簬60%闃堝€?


def test_streaming_recognize():
    import soundfile as sf
    import numpy as np
    from asr.streaming import StreamingASRService, StreamingCallback

    class _Cb(StreamingCallback):
        def __init__(self):
            self.finals = []
            self.partials = []
            self.errors = []

        def on_partial(self, text):
            self.partials.append(text)

        def on_final(self, text, is_end=False):
            self.finals.append(text)

        def on_error(self, error):
            self.errors.append(error)

    svc = StreamingASRService()
    if not svc.enabled:
        raise AssertionError("娴佸紡ASR鏈惎鐢?)
    cb = _Cb()
    svc.start_stream(cb)

    audio_path = os.path.normpath(os.path.join(ASR_SAMPLES_DIR, "sample_01.wav"))
    audio_data, sr = sf.read(audio_path, dtype="int16")
    pcm_bytes = audio_data.tobytes()
    chunk_size = sr * 2 // 10
    for i in range(0, len(pcm_bytes), chunk_size):
        svc.send_audio(pcm_bytes[i:i + chunk_size])

    svc.stop_stream()
    all_text = "".join(cb.finals) + "".join(cb.partials)
    assert len(all_text) > 0, f"娴佸紡ASR鏈骇鐢熶换浣曠粨鏋? finals={cb.finals}, partials={cb.partials}"
    return {"text": all_text, "finals_count": len(cb.finals)}


def test_asr_to_query():
    from asr.service import ASRService
    svc = ASRService()
    metadata_path = os.path.normpath(os.path.join(ASR_SAMPLES_DIR, "metadata.json"))
    with open(metadata_path, encoding="utf-8") as f:
        metadata = json.load(f)

    results = []
    for sample in metadata[:5]:
        audio_path = os.path.normpath(os.path.join(ASR_SAMPLES_DIR, sample["filename"]))
        if not os.path.exists(audio_path):
            continue
        result = svc.transcribe(audio_path)
        results.append({
            "filename": sample["filename"],
            "expected": sample["final_question"],
            "recognized": result.text,
            "keyword": sample.get("keyword", ""),
            "category_l1": sample.get("category_l1", ""),
        })
    assert len(results) > 0, "娌℃湁鍙祴璇曠殑闊抽鏍锋湰"
    return results


def test_channel_asr():
    import numpy as np
    import soundfile as sf
    import tempfile
    import os
    from asr.websocket import _extract_channel
    from asr.service import ASRService

    stereo_path = os.path.normpath(os.path.join(ASR_SAMPLES_DIR, "sample_01.wav"))
    stereo_audio, sr = sf.read(stereo_path, dtype="int16")
    assert stereo_audio.ndim == 2, f"sample_01.wav搴斾负鍙屽０閬? 瀹為檯ndim={stereo_audio.ndim}"

    stereo_bytes = stereo_audio.tobytes()
    left_bytes = _extract_channel(stereo_bytes, "left")
    right_bytes = _extract_channel(stereo_bytes, "right")

    svc = ASRService()

    fd_l, tmp_l = tempfile.mkstemp(suffix=".wav")
    os.close(fd_l)
    fd_r, tmp_r = tempfile.mkstemp(suffix=".wav")
    os.close(fd_r)

    try:
        sf.write(tmp_l, np.frombuffer(left_bytes, dtype=np.int16), sr)
        sf.write(tmp_r, np.frombuffer(right_bytes, dtype=np.int16), sr)

        customer_result = svc.transcribe(tmp_l)
        agent_result = svc.transcribe(tmp_r)

        return {
            "customer_text": customer_result.text,
            "agent_text": agent_result.text,
            "customer_expected": "ETC鎵ｈ垂寮傚父鎬庝箞澶勭悊",
            "agent_expected": "鎮ㄥソ璇烽棶鏈変粈涔堝彲浠ュ府鎮?,
        }
    finally:
        for p in (tmp_l, tmp_r):
            if os.path.exists(p):
                os.unlink(p)


if __name__ == "__main__":
    test_name = sys.argv[1] if len(sys.argv) > 1 else "all"

    tests = {
        "model_load": test_model_load,
        "transcribe_single": test_transcribe_single,
        "batch_accuracy": test_batch_accuracy,
        "streaming_recognize": test_streaming_recognize,
        "asr_to_query": test_asr_to_query,
        "channel_asr": test_channel_asr,
    }

    if test_name == "all":
        results = [_run_test(name, func) for name, func in tests.items()]
    else:
        func = tests.get(test_name)
        if func is None:
            print(json.dumps({"error": f"鏈煡娴嬭瘯: {test_name}"}))
            sys.exit(1)
        results = [_run_test(test_name, func)]

    print("===ASR_TEST_RESULT===")
    print(json.dumps(results, ensure_ascii=False))

    if _cov is not None:
        try:
            _cov.stop()
            _cov.save()
        except Exception:
            pass

    failed = [r for r in results if r["status"] == "failed"]
    sys.exit(1 if failed else 0)