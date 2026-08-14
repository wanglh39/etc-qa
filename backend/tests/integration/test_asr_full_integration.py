import os

import pytest

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "1")

ASR_SAMPLES_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "asr_samples"))


@pytest.mark.integration
class TestASRQueryAPIIntegration:
    def test_asr_query_success_with_real_audio(self, real_client):
        from asr.service import get_asr_service
        svc = get_asr_service()
        original_enabled = svc._enabled
        svc._enabled = True
        try:
            sample_path = os.path.join(ASR_SAMPLES_DIR, "sample_01.wav")
            assert os.path.exists(sample_path), f"音频样本不存在: {sample_path}"
            with open(sample_path, "rb") as f:
                resp = real_client.post(
                    "/api/v1/asr/query",
                    files={"file": ("sample_01.wav", f, "audio/wav")},
                )
            assert resp.status_code == 200
            data = resp.json()
            assert "asr_text" in data
            assert "asr_model" in data
            assert "asr_confidence" in data
            assert "asr_duration_ms" in data
            assert "query" in data
            assert "candidates" in data
            assert "total_candidates" in data
            if data["asr_text"].strip():
                assert data["total_candidates"] >= 0
        finally:
            svc._enabled = original_enabled

    def test_asr_query_with_category_filter(self, real_client):
        from asr.service import get_asr_service
        svc = get_asr_service()
        original_enabled = svc._enabled
        svc._enabled = True
        try:
            sample_path = os.path.join(ASR_SAMPLES_DIR, "sample_01.wav")
            with open(sample_path, "rb") as f:
                resp = real_client.post(
                    "/api/v1/asr/query",
                    files={"file": ("sample_01.wav", f, "audio/wav")},
                    params={"category_l1": "ETC"},
                )
            assert resp.status_code == 200
            data = resp.json()
            assert "asr_text" in data
        finally:
            svc._enabled = original_enabled

    def test_asr_query_second_sample(self, real_client):
        from asr.service import get_asr_service
        svc = get_asr_service()
        original_enabled = svc._enabled
        svc._enabled = True
        try:
            sample_path = os.path.join(ASR_SAMPLES_DIR, "sample_02.wav")
            assert os.path.exists(sample_path), f"音频样本不存在: {sample_path}"
            with open(sample_path, "rb") as f:
                resp = real_client.post(
                    "/api/v1/asr/query",
                    files={"file": ("sample_02.wav", f, "audio/wav")},
                )
            assert resp.status_code == 200
            data = resp.json()
            assert "asr_text" in data
            assert "asr_model" in data
        finally:
            svc._enabled = original_enabled


@pytest.mark.integration
class TestAudioPreprocessorIntegration:
    def test_process_real_audio_no_preprocess(self):
        from asr.preprocess import AudioPreprocessor
        sample_path = os.path.join(ASR_SAMPLES_DIR, "sample_01.wav")
        if not os.path.exists(sample_path):
            pytest.skip("音频样本不存在")
        pp = AudioPreprocessor()
        result = pp.process(sample_path)
        if pp.vad_enabled or pp.denoise_enabled:
            assert os.path.exists(result)
            pp.cleanup(result, sample_path)
        else:
            assert result == sample_path

    def test_health_reflects_real_config(self):
        from asr.preprocess import AudioPreprocessor
        pp = AudioPreprocessor()
        h = pp.health()
        from utils.config import get_config
        cfg = get_config().get("asr", {}).get("preprocess", {})
        assert h["vad_enabled"] == cfg.get("vad_enabled", False)
        assert h["denoise_enabled"] == cfg.get("denoise_enabled", False)

    def test_get_preprocessor_singleton(self):
        from asr.preprocess import get_preprocessor
        pp1 = get_preprocessor()
        pp2 = get_preprocessor()
        assert pp1 is pp2


@pytest.mark.integration
class TestWebSocketASRStreamIntegration:
    def test_ws_streaming_connection(self):
        from utils.config import get_config
        cfg = get_config()
        streaming_enabled = cfg.get("asr", {}).get("streaming", {}).get("enabled", False)
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from asr.websocket import router as ws_router
        app = FastAPI()
        app.include_router(ws_router, prefix="/api/v1")
        client = TestClient(app)
        try:
            with client.websocket_connect("/api/v1/ws/asr/stream") as ws:
                data = ws.receive_json()
                if not streaming_enabled:
                    assert data["type"] == "error"
                    assert "未启用" in data["message"]
                else:
                    assert data["type"] == "ready"
        except Exception as e:
            if "disconnect" in str(e).lower() or "close" in str(e).lower():
                pass
            else:
                raise
