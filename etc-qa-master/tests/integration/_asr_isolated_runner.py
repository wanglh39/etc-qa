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
        func()
        return {"test": name, "status": "passed"}
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
    assert os.path.exists(audio_path), f"音频文件不存在: {audio_path}"

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
        expected = sample["text"]
        if expected in result.text or result.text in expected:
            correct += 1
        else:
            for kw in sample.get("keyword", "").split(","):
                if kw and kw in result.text:
                    correct += 1
                    break

    accuracy = correct / total if total > 0 else 0
    assert accuracy >= 0.6, f"ASR批量识别准确率{accuracy:.0%}低于60%阈值"


if __name__ == "__main__":
    test_name = sys.argv[1] if len(sys.argv) > 1 else "all"

    tests = {
        "model_load": test_model_load,
        "transcribe_single": test_transcribe_single,
        "batch_accuracy": test_batch_accuracy,
    }

    if test_name == "all":
        results = [_run_test(name, func) for name, func in tests.items()]
    else:
        func = tests.get(test_name)
        if func is None:
            print(json.dumps({"error": f"未知测试: {test_name}"}))
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
