import glob as glob_mod
import json
import os
import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

ASR_SAMPLES_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "asr_samples"))
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
        capture_output=True,
        text=True,
        timeout=600,
        env=env,
        cwd=project_root,
    )
    if result.returncode != 0 and not result.stdout.strip():
        stderr_tail = result.stderr[-500:]
        if "ModuleNotFoundError" in stderr_tail:
            pytest.skip(f"依赖缺失，跳过ASR测试: {stderr_tail}")
        pytest.fail(f"子进程异常退出: {stderr_tail}")
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
    return results


def _run_isolated_data(test_name):
    """运行隔离测试并返回结果数据"""
    results = _run_isolated(test_name)
    if not results or not isinstance(results, list):
        return None
    return results[0].get("data") if results else None


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

    def test_streaming_asr_recognize(self):
        """集成测试L2: 流式ASR端到端 - 用真实音频验证StreamingASRService"""
        data = _run_isolated_data("streaming_recognize")
        assert data is not None, "流式ASR测试未返回数据"
        assert "text" in data, f"返回数据缺少text字段: {data}"
        assert len(data["text"]) > 0, "流式ASR识别结果为空"
        assert data.get("finals_count", 0) > 0, "没有产生final结果"

    def test_asr_to_query_end_to_end(self, qa_service):
        """集成测试L2: 语音→检索端到端 - ASR识别→QAService检索→验证答案"""
        asr_results = _run_isolated_data("asr_to_query")
        assert asr_results is not None, "ASR识别未返回数据"
        assert len(asr_results) > 0, "没有ASR识别结果"

        matched = 0
        total = 0
        for item in asr_results:
            recognized = item["recognized"]
            keyword = item.get("keyword", "")
            category_l1 = item.get("category_l1")
            expected = item.get("expected", "")

            if not recognized.strip():
                continue
            total += 1

            query_result = qa_service.query(recognized, category_l1)
            if query_result is None or not query_result.candidates:
                print(f"  [未命中] ASR='{recognized}' expected='{expected}' -> 无候选结果")
                continue

            found = False
            for candidate in query_result.candidates:
                combined = candidate.question + candidate.answer
                if keyword and keyword in combined:
                    matched += 1
                    found = True
                    break
                if any(expected[i : i + 2] in combined for i in range(len(expected) - 1)):
                    matched += 1
                    found = True
                    break

            if not found:
                top = query_result.candidates[0]
                print(
                    f"  [未匹配] ASR='{recognized}' keyword='{keyword}' "
                    f"-> top_question='{top.question[:30]}' answer='{top.answer[:30]}'"
                )

        match_rate = matched / total if total > 0 else 0
        assert match_rate >= 0.4, f"语音→检索匹配率{match_rate:.0%}低于40%阈值 (matched={matched}/{total})"

    def test_speaker_channel_separation(self):
        """集成测试L2: 说话人分离 - sample_01.wav为双声道，验证通道分离"""
        import numpy as np
        import soundfile as sf

        from asr.websocket import _extract_channel

        stereo_path = os.path.join(ASR_SAMPLES_DIR, "sample_01.wav")
        stereo_audio, sr = sf.read(stereo_path, dtype="int16")
        assert stereo_audio.ndim == 2, f"sample_01.wav应为双声道, 实际ndim={stereo_audio.ndim}"

        stereo_bytes = stereo_audio.tobytes()
        left_extracted = _extract_channel(stereo_bytes, "left")
        right_extracted = _extract_channel(stereo_bytes, "right")

        left_np = np.frombuffer(left_extracted, dtype=np.int16)
        right_np = np.frombuffer(right_extracted, dtype=np.int16)

        assert len(left_np) == len(stereo_audio), "左声道样本数应与立体声帧数一致"
        assert len(right_np) == len(stereo_audio), "右声道样本数应与立体声帧数一致"

        left_energy = np.sum(left_np.astype(np.float64) ** 2)
        right_energy = np.sum(right_np.astype(np.float64) ** 2)
        assert left_energy > 0, "左声道能量为0，音频数据异常"
        assert right_energy > 0, "右声道能量为0，音频数据异常"

    def test_speaker_channel_asr(self):
        """集成测试L2: 双声道分离后ASR识别 - 验证分离出的客户声道可正确识别"""
        data = _run_isolated_data("channel_asr")
        assert data is not None, "双声道ASR测试未返回数据"
        assert "customer_text" in data, f"返回数据缺少customer_text: {data}"
        assert len(data["customer_text"]) > 0, "客户声道识别结果为空"
        assert "agent_text" in data, f"返回数据缺少agent_text: {data}"
        assert len(data["agent_text"]) > 0, "客服声道识别结果为空"


@pytest.mark.integration
class TestL2APIRoutesASRError:
    def test_asr_disabled_returns_503(self, real_client):
        from asr.service import get_asr_service

        svc = get_asr_service()
        original_enabled = svc._enabled
        svc._enabled = False
        try:
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(b"fake audio")
                tmp_path = f.name
            with open(tmp_path, "rb") as f:
                resp = real_client.post("/api/v1/asr", files={"file": ("test.wav", f, "audio/wav")})
            assert resp.status_code == 503
            os.unlink(tmp_path)
        finally:
            svc._enabled = original_enabled

    def test_asr_file_not_found_returns_404(self, real_client):
        from asr.service import get_asr_service

        svc = get_asr_service()
        original_enabled = svc._enabled
        svc._enabled = True
        try:
            with patch.object(svc, "transcribe", side_effect=FileNotFoundError("文件不存在")):
                import tempfile

                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    f.write(b"fake audio")
                    tmp_path = f.name
                with open(tmp_path, "rb") as f:
                    resp = real_client.post("/api/v1/asr", files={"file": ("test.wav", f, "audio/wav")})
                assert resp.status_code == 404
                os.unlink(tmp_path)
        finally:
            svc._enabled = original_enabled

    def test_asr_runtime_error_returns_503(self, real_client):
        from asr.service import get_asr_service

        svc = get_asr_service()
        with patch.object(svc, "transcribe", side_effect=RuntimeError("模型未加载")):
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(b"fake audio")
                tmp_path = f.name
            with open(tmp_path, "rb") as f:
                resp = real_client.post("/api/v1/asr", files={"file": ("test.wav", f, "audio/wav")})
            assert resp.status_code == 503
            os.unlink(tmp_path)
