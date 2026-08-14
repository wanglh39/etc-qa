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
        capture_output=True, text=True, timeout=600, env=env,
        cwd=project_root,
    )
    if result.returncode != 0 and not result.stdout.strip():
        pytest.fail(f"瀛愯繘绋嬪紓甯搁€€鍑? {result.stderr[-500:]}")
    marker = "===ASR_TEST_RESULT==="
    if marker not in result.stdout:
        pytest.fail(f"瀛愯繘绋嬫湭杈撳嚭缁撴灉鏍囪: stdout={result.stdout[-300:]}, stderr={result.stderr[-300:]}")
    json_line = result.stdout.split(marker)[-1].strip()
    try:
        results = json.loads(json_line)
    except json.JSONDecodeError:
        pytest.fail(f"瀛愯繘绋嬭緭鍑鸿В鏋愬け璐? {json_line[:300]}")
        return
    if isinstance(results, list):
        for r in results:
            if r["status"] == "failed":
                pytest.fail(f"{r['test']} 澶辫触: {r.get('error', '')}")
    elif isinstance(results, dict) and "error" in results:
        pytest.fail(results["error"])
    return results


def _run_isolated_data(test_name):
    """杩愯闅旂娴嬭瘯骞惰繑鍥炵粨鏋滄暟鎹?""
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
        corrections = {"涓€浣撴満": "ETC", "钃濆憖": "钃濈墮"}
        text = "涓€浣撴満钃濆憖杩炴帴涓嶄笂"
        corrected = _apply_corrections(text, corrections)
        assert "ETC" in corrected
        assert "钃濈墮" in corrected
        assert "涓€浣撴満" not in corrected

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
        with pytest.raises(RuntimeError, match="ASR鏈惎鐢?):
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
        """闆嗘垚娴嬭瘯L2: 娴佸紡ASR绔埌绔?- 鐢ㄧ湡瀹為煶棰戦獙璇丼treamingASRService"""
        data = _run_isolated_data("streaming_recognize")
        assert data is not None, "娴佸紡ASR娴嬭瘯鏈繑鍥炴暟鎹?
        assert "text" in data, f"杩斿洖鏁版嵁缂哄皯text瀛楁: {data}"
        assert len(data["text"]) > 0, "娴佸紡ASR璇嗗埆缁撴灉涓虹┖"
        assert data.get("finals_count", 0) > 0, "娌℃湁浜х敓final缁撴灉"

    def test_asr_to_query_end_to_end(self, qa_service):
        """闆嗘垚娴嬭瘯L2: 璇煶鈫掓绱㈢鍒扮 - ASR璇嗗埆鈫扱AService妫€绱⑩啋楠岃瘉绛旀"""
        asr_results = _run_isolated_data("asr_to_query")
        assert asr_results is not None, "ASR璇嗗埆鏈繑鍥炴暟鎹?
        assert len(asr_results) > 0, "娌℃湁ASR璇嗗埆缁撴灉"

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
                print(f"  [鏈懡涓璢 ASR='{recognized}' expected='{expected}' -> 鏃犲€欓€夌粨鏋?)
                continue

            found = False
            for candidate in query_result.candidates:
                combined = candidate.question + candidate.answer
                if keyword and keyword in combined:
                    matched += 1
                    found = True
                    break
                if any(expected[i:i+2] in combined for i in range(len(expected) - 1)):
                    matched += 1
                    found = True
                    break

            if not found:
                top = query_result.candidates[0]
                print(f"  [鏈尮閰峕 ASR='{recognized}' keyword='{keyword}' "
                      f"-> top_question='{top.question[:30]}' answer='{top.answer[:30]}'")

        match_rate = matched / total if total > 0 else 0
        assert match_rate >= 0.4, f"璇煶鈫掓绱㈠尮閰嶇巼{match_rate:.0%}浣庝簬40%闃堝€?(matched={matched}/{total})"

    def test_speaker_channel_separation(self):
        """闆嗘垚娴嬭瘯L2: 璇磋瘽浜哄垎绂?- sample_01.wav涓哄弻澹伴亾锛岄獙璇侀€氶亾鍒嗙"""
        import numpy as np
        import soundfile as sf
        from asr.websocket import _extract_channel

        stereo_path = os.path.join(ASR_SAMPLES_DIR, "sample_01.wav")
        stereo_audio, sr = sf.read(stereo_path, dtype="int16")
        assert stereo_audio.ndim == 2, f"sample_01.wav搴斾负鍙屽０閬? 瀹為檯ndim={stereo_audio.ndim}"

        stereo_bytes = stereo_audio.tobytes()
        left_extracted = _extract_channel(stereo_bytes, "left")
        right_extracted = _extract_channel(stereo_bytes, "right")

        left_np = np.frombuffer(left_extracted, dtype=np.int16)
        right_np = np.frombuffer(right_extracted, dtype=np.int16)

        assert len(left_np) == len(stereo_audio), "宸﹀０閬撴牱鏈暟搴斾笌绔嬩綋澹板抚鏁颁竴鑷?
        assert len(right_np) == len(stereo_audio), "鍙冲０閬撴牱鏈暟搴斾笌绔嬩綋澹板抚鏁颁竴鑷?

        left_energy = np.sum(left_np.astype(np.float64) ** 2)
        right_energy = np.sum(right_np.astype(np.float64) ** 2)
        assert left_energy > 0, "宸﹀０閬撹兘閲忎负0锛岄煶棰戞暟鎹紓甯?
        assert right_energy > 0, "鍙冲０閬撹兘閲忎负0锛岄煶棰戞暟鎹紓甯?

    def test_speaker_channel_asr(self):
        """闆嗘垚娴嬭瘯L2: 鍙屽０閬撳垎绂诲悗ASR璇嗗埆 - 楠岃瘉鍒嗙鍑虹殑瀹㈡埛澹伴亾鍙纭瘑鍒?""
        data = _run_isolated_data("channel_asr")
        assert data is not None, "鍙屽０閬揂SR娴嬭瘯鏈繑鍥炴暟鎹?
        assert "customer_text" in data, f"杩斿洖鏁版嵁缂哄皯customer_text: {data}"
        assert len(data["customer_text"]) > 0, "瀹㈡埛澹伴亾璇嗗埆缁撴灉涓虹┖"
        assert "agent_text" in data, f"杩斿洖鏁版嵁缂哄皯agent_text: {data}"
        assert len(data["agent_text"]) > 0, "瀹㈡湇澹伴亾璇嗗埆缁撴灉涓虹┖"


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
            with patch.object(svc, 'transcribe', side_effect=FileNotFoundError("鏂囦欢涓嶅瓨鍦?)):
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
        with patch.object(svc, 'transcribe', side_effect=RuntimeError("妯″瀷鏈姞杞?)):
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(b"fake audio")
                tmp_path = f.name
            with open(tmp_path, "rb") as f:
                resp = real_client.post("/api/v1/asr", files={"file": ("test.wav", f, "audio/wav")})
            assert resp.status_code == 503
            os.unlink(tmp_path)