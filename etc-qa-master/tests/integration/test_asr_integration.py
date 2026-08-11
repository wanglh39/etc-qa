import glob as glob_mod
import json
import os
import subprocess
import sys

import pytest

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

ASR_SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "asr_samples")
_RUNNER = os.path.join(os.path.dirname(__file__), "_asr_isolated_runner.py")
_PYTHON = sys.executable


def _run_isolated(test_name):
    env = os.environ.copy()
    env["ETC_QA_ENV"] = "test"
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    coveragerc = os.path.join(project_root, ".coveragerc")
    cov_data_dir = os.path.join(project_root, ".coverage_asr")
    os.makedirs(cov_data_dir, exist_ok=True)
    env["COVERAGE_PROCESS_START"] = coveragerc
    env["COVERAGE_FILE"] = os.path.join(cov_data_dir, ".coverage")

    result = subprocess.run(
        [_PYTHON, _RUNNER, test_name],
        capture_output=True, text=True, timeout=180, env=env,
        cwd=project_root,
    )
    if result.returncode != 0 and not result.stdout.strip():
        pytest.fail(f"子进程异常退出: {result.stderr[-500:]}")
    marker = "===ASR_TEST_RESULT==="
    if marker not in result.stdout:
        pytest.fail(f"子进程未输出结果标记: stdout={result.stdout[-300:]}, stderr={result.stderr[-300:]}")
    json_line = result.stdout.split(marker)[-1].strip()
    try:
        results = json.loads(json_line)
    except json.JSONDecodeError:
        pytest.fail(f"子进程输出解析失败: {json_line[:300]}")
        return
    if isinstance(results, list):
        for r in results:
            if r["status"] == "failed":
                pytest.fail(f"{r['test']} 失败: {r.get('error', '')}")
    elif isinstance(results, dict) and "error" in results:
        pytest.fail(results["error"])


@pytest.fixture(scope="session", autouse=True)
def _merge_asr_coverage():
    yield
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    cov_data_dir = os.path.join(project_root, ".coverage_asr")
    if not os.path.isdir(cov_data_dir):
        return
    cov_files = glob_mod.glob(os.path.join(cov_data_dir, ".coverage*"))
    if not cov_files:
        return
    try:
        import coverage
        main_data = os.path.join(project_root, ".coverage")
        main_cov = coverage.Coverage(data_file=main_data)
        main_cov.load()
        for cf in cov_files:
            sub_cov = coverage.Coverage(data_file=cf)
            sub_cov.load()
            main_cov.get_data().update(sub_cov.get_data())
        main_cov.save()
    except Exception as e:
        import warnings
        warnings.warn(f"ASR subprocess coverage merge failed: {e}")


@pytest.mark.integration
class TestL2ASRRecognition:
    def test_asr_service_enabled(self):
        from utils.config import get_config
        cfg = get_config()
        assert cfg.get("asr", {}).get("enabled") is True

    def test_asr_model_load(self):
        _run_isolated("model_load")

    def test_asr_transcribe_single(self):
        _run_isolated("transcribe_single")

    def test_asr_corrections_applied(self):
        from asr.service import _apply_corrections
        corrections = {"一体机": "ETC", "蓝呀": "蓝牙"}
        text = "一体机蓝呀连接不上"
        corrected = _apply_corrections(text, corrections)
        assert "ETC" in corrected
        assert "蓝牙" in corrected
        assert "一体机" not in corrected

    def test_asr_batch_accuracy(self):
        _run_isolated("batch_accuracy")

    def test_asr_health(self):
        from asr.service import ASRService
        svc = ASRService()
        health = svc.health()
        assert isinstance(health.loaded, bool)
        assert health.model != ""

    def test_asr_file_not_found(self):
        from asr.service import ASRService
        svc = ASRService()
        with pytest.raises(FileNotFoundError):
            svc.transcribe("/nonexistent/path.wav")

    def test_asr_health_api(self, real_client):
        resp = real_client.get("/api/v1/asr/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "loaded" in data

    def test_asr_load_corrections_from_config(self):
        from asr.service import _load_corrections
        corrections = _load_corrections()
        assert isinstance(corrections, dict)
        if corrections:
            assert all(isinstance(k, str) for k in corrections.keys())

    def test_asr_transcribe_disabled(self):
        from asr.service import ASRService
        svc = ASRService()
        svc._enabled = False
        with pytest.raises(RuntimeError, match="ASR未启用"):
            svc.transcribe("/dummy.wav")

    def test_asr_reload(self):
        from asr.service import ASRService
        svc = ASRService()
        svc._model = object()
        svc.reload()
        assert svc._model is None

    def test_asr_get_corrections(self):
        from asr.service import ASRService
        svc = ASRService()
        corrections = svc._get_corrections()
        assert isinstance(corrections, dict)

    def test_asr_service_singleton(self):
        from asr.service import get_asr_service
        svc1 = get_asr_service()
        svc2 = get_asr_service()
        assert svc1 is svc2

    def test_asr_health_details(self):
        from asr.service import ASRService
        svc = ASRService()
        health = svc.health()
        assert hasattr(health, "device")
        assert hasattr(health, "finetuned")
        assert health.finetuned is False
