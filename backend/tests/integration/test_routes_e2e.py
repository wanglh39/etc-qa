from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import router, set_mysql_client, set_service, set_work_order_client
from models.schemas import CandidateResult, QueryResponse
from utils.auth_middleware import get_current_user

_MOCK_USER = {"sub": "test_user", "role": "admin"}


@pytest.fixture
def app():
    application = FastAPI()
    application.dependency_overrides[get_current_user] = lambda: _MOCK_USER
    application.include_router(router, prefix="/api/v1")
    return application


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def mock_service():
    svc = MagicMock()
    set_service(svc)
    yield svc
    set_service(None)


@pytest.fixture
def mock_mysql():
    mysql = MagicMock()
    set_mysql_client(mysql)
    yield mysql
    set_mysql_client(None)


@pytest.fixture
def mock_wo():
    wo = MagicMock()
    set_work_order_client(wo)
    yield wo
    set_work_order_client(None)


class TestQueryE2E:
    def test_query_success(self, client, mock_service):
        mock_service.query.return_value = QueryResponse(
            query="ETC扣费异常",
            standardized_query="ETC扣费异常",
            confidence="high",
            candidates=[CandidateResult(qa_id=1, question="ETC扣费异常", answer="核实退款",
                                        category_l1="售后", category_l2="扣费",
                                        internal_process="", feedback_dept="", score=0.95)],
            total_candidates=1,
        )
        resp = client.post("/api/v1/query", json={"question": "ETC扣费异常"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["confidence"] == "high"
        assert len(data["candidates"]) == 1
        assert data["candidates"][0]["qa_id"] == 1

    def test_query_no_service(self, client):
        set_service(None)
        resp = client.post("/api/v1/query", json={"question": "test"})
        assert resp.status_code == 500

    def test_query_with_category(self, client, mock_service):
        mock_service.query.return_value = QueryResponse(
            query="test", standardized_query="test", confidence="none",
            candidates=[], total_candidates=0,
        )
        resp = client.post("/api/v1/query", json={"question": "test", "category_l1": "售后业务"})
        assert resp.status_code == 200
        mock_service.query.assert_called_with("test", "售后业务")


class TestAddQAE2E:
    def test_add_qa_success(self, client, mock_service):
        mock_service.add_knowledge.return_value = 42
        resp = client.post("/api/v1/add", json={
            "question": "新问题", "answer": "新答案",
            "category_l1": "售后", "category_l2": "扣费",
        })
        assert resp.status_code == 200
        assert resp.json()["qa_id"] == 42



class TestQAListE2E:
    def test_list_qa(self, client, mock_mysql):
        mock_mysql.get_qa_list.return_value = {
            "items": [{"id": 1, "question": "q1", "answer": "a1",
                       "category_l1": "售后", "category_l2": "扣费",
                       "status": "active", "created_at": "2024-01-01"}],
            "total": 1, "page": 1, "page_size": 20,
        }
        resp = client.get("/api/v1/qa/list")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_list_qa_no_mysql(self, client):
        set_mysql_client(None)
        resp = client.get("/api/v1/qa/list")
        assert resp.status_code == 500


class TestQADetailE2E:
    def test_get_qa_detail(self, client, mock_mysql):
        mock_mysql.get_qa_detail.return_value = {
            "id": 1, "question": "q1", "answer": "a1",
            "category_l1": "售后", "category_l2": "扣费",
            "internal_process": "", "feedback_dept": "",
            "status": "active", "created_at": "2024-01-01",
        }
        resp = client.get("/api/v1/qa/1")
        assert resp.status_code == 200
        assert resp.json()["id"] == 1

    def test_get_qa_detail_not_found(self, client, mock_mysql):
        mock_mysql.get_qa_detail.return_value = None
        resp = client.get("/api/v1/qa/999")
        assert resp.status_code == 404


class TestDeleteQAE2E:
    def test_delete_qa(self, client, mock_mysql, mock_service):
        mock_mysql.delete_qa.return_value = True
        resp = client.delete("/api/v1/qa/1")
        assert resp.status_code == 200
        mock_service.invalidate_active_ids_cache.assert_called_once()

    def test_delete_qa_not_found(self, client, mock_mysql):
        mock_mysql.delete_qa.return_value = False
        resp = client.delete("/api/v1/qa/999")
        assert resp.status_code == 404


class TestUpdateStatusE2E:
    def test_update_status(self, client, mock_mysql, mock_service):
        mock_mysql.update_qa_status.return_value = None
        resp = client.put("/api/v1/qa/status", json={"qa_id": 1, "status": "deprecated"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "deprecated"

    def test_update_status_invalid(self, client, mock_mysql):
        resp = client.put("/api/v1/qa/status", json={"qa_id": 1, "status": "invalid"})
        assert resp.status_code == 400


class TestSearchQAE2E:
    def test_search_qa(self, client, mock_mysql):
        mock_mysql.search_qa.return_value = {
            "items": [{"id": 1, "question": "ETC扣费", "answer": "核实",
                       "category_l1": "售后", "category_l2": "扣费",
                       "status": "active", "created_at": "2024-01-01"}],
            "total": 1, "page": 1, "page_size": 20,
        }
        resp = client.post("/api/v1/qa/search", json={"keyword": "ETC"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 1


class TestStatsE2E:
    def test_get_stats(self, client, mock_mysql):
        mock_mysql.count_qa.return_value = {"total": 100, "active": 80, "deprecated": 15, "archived": 5}
        mock_mysql.count_work_orders.return_value = {"total": 50, "submitted": 10, "processed": 40}
        mock_mysql.get_category_stats.return_value = {}
        resp = client.get("/api/v1/stats")
        assert resp.status_code == 200
        assert resp.json()["qa_total"] == 100


class TestCategoriesE2E:
    def test_get_categories(self, client, mock_mysql):
        mock_mysql.get_category_tree.return_value = {"售后业务": ["扣费", "退款"]}
        resp = client.get("/api/v1/categories")
        assert resp.status_code == 200


class TestConfigE2E:
    def test_get_config(self, client):
        with patch("api.routes.get_business_config", return_value=["ETC"]):
            resp = client.get("/api/v1/config/must_preserve_kws")
            assert resp.status_code == 200

    def test_update_config(self, client, mock_mysql):
        resp = client.put("/api/v1/config/test_key", json={"value": "new_val"})
        assert resp.status_code == 200

    def test_reload_config(self, client):
        resp = client.post("/api/v1/config/reload")
        assert resp.status_code == 200


class TestWorkOrdersE2E:
    def test_list_work_orders(self, client, mock_mysql):
        mock_mysql.get_work_order_list.return_value = {
            "items": [], "total": 0, "page": 1, "page_size": 20,
        }
        resp = client.get("/api/v1/work_orders")
        assert resp.status_code == 200



class TestAddQANoService:
    def test_add_qa_no_service(self, client):
        set_service(None)
        resp = client.post("/api/v1/add", json={"question": "q", "answer": "a"})
        assert resp.status_code == 500


class TestUpdateStatusNoMySQL:
    def test_update_status_no_mysql(self, client):
        set_mysql_client(None)
        resp = client.put("/api/v1/qa/status", json={"qa_id": 1, "status": "active"})
        assert resp.status_code == 500


class TestConfigNoMySQL:
    def test_update_config_no_mysql(self, client):
        set_mysql_client(None)
        resp = client.put("/api/v1/config/test_key", json={"value": "val"})
        assert resp.status_code == 500


class TestQADetailNoMySQL:
    def test_qa_detail_no_mysql(self, client):
        set_mysql_client(None)
        resp = client.get("/api/v1/qa/1")
        assert resp.status_code == 500


class TestDeleteQANoMySQL:
    def test_delete_qa_no_mysql(self, client):
        set_mysql_client(None)
        resp = client.delete("/api/v1/qa/1")
        assert resp.status_code == 500


class TestSearchQANoMySQL:
    def test_search_qa_no_mysql(self, client):
        set_mysql_client(None)
        resp = client.post("/api/v1/qa/search", json={"keyword": "test"})
        assert resp.status_code == 500


class TestStatsNoMySQL:
    def test_stats_no_mysql(self, client):
        set_mysql_client(None)
        resp = client.get("/api/v1/stats")
        assert resp.status_code == 500


class TestCategoriesNoMySQL:
    def test_categories_no_mysql(self, client):
        set_mysql_client(None)
        resp = client.get("/api/v1/categories")
        assert resp.status_code == 500


class TestWorkOrdersNoMySQL:
    def test_work_orders_no_mysql(self, client):
        set_mysql_client(None)
        resp = client.get("/api/v1/work_orders")
        assert resp.status_code == 500


class TestASRHealthE2E:
    def test_asr_health(self, client):
        from asr.models import ASRHealthResponse
        with patch("api.routes.get_asr_service") as mock_get:
            mock_asr = MagicMock()
            mock_asr.health.return_value = ASRHealthResponse(loaded=True, model="paraformer", device="cpu")
            mock_get.return_value = mock_asr
            resp = client.get("/api/v1/asr/health")
            assert resp.status_code == 200
            assert resp.json()["loaded"] is True


class TestASRDisabledE2E:
    def test_asr_disabled(self, client):
        with patch("api.routes.get_asr_service") as mock_get:
            mock_asr = MagicMock()
            mock_asr._enabled = False
            mock_get.return_value = mock_asr
            resp = client.post("/api/v1/asr", files={"file": ("test.wav", b"fake audio", "audio/wav")})
            assert resp.status_code == 503


class TestASRSuccessE2E:
    def test_asr_transcribe_success(self, client):
        from asr.models import ASRResponse
        with patch("api.routes.get_asr_service") as mock_get:
            mock_asr = MagicMock()
            mock_asr._enabled = True
            mock_asr.transcribe.return_value = ASRResponse(text="ETC扣费异常", confidence=0.95)
            mock_get.return_value = mock_asr
            resp = client.post("/api/v1/asr", files={"file": ("test.wav", b"fake audio", "audio/wav")})
            assert resp.status_code == 200
            assert resp.json()["text"] == "ETC扣费异常"


class TestASRErrorE2E:
    def test_asr_file_not_found(self, client):
        with patch("api.routes.get_asr_service") as mock_get:
            mock_asr = MagicMock()
            mock_asr._enabled = True
            mock_asr.transcribe.side_effect = FileNotFoundError("file not found")
            mock_get.return_value = mock_asr
            resp = client.post("/api/v1/asr", files={"file": ("test.wav", b"fake audio", "audio/wav")})
            assert resp.status_code == 404

    def test_asr_runtime_error(self, client):
        with patch("api.routes.get_asr_service") as mock_get:
            mock_asr = MagicMock()
            mock_asr._enabled = True
            mock_asr.transcribe.side_effect = RuntimeError("model error")
            mock_get.return_value = mock_asr
            resp = client.post("/api/v1/asr", files={"file": ("test.wav", b"fake audio", "audio/wav")})
            assert resp.status_code == 503

    def test_asr_generic_error(self, client):
        with patch("api.routes.get_asr_service") as mock_get:
            mock_asr = MagicMock()
            mock_asr._enabled = True
            mock_asr.transcribe.side_effect = Exception("unknown error")
            mock_get.return_value = mock_asr
            resp = client.post("/api/v1/asr", files={"file": ("test.wav", b"fake audio", "audio/wav")})
            assert resp.status_code == 500

