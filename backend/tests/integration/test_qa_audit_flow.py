import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import routes
from api.auth import router as auth_router
from utils import jwt_utils
from utils.jwt_utils import create_token
from utils.rate_limit import limiter


@pytest.fixture(autouse=True)
def _reset_state():
    limiter.reset()
    old = jwt_utils._mysql_client
    jwt_utils._mysql_client = None
    yield
    jwt_utils._mysql_client = old
    limiter.reset()


@pytest.fixture
def mock_mysql():
    mysql = MagicMock()
    routes.set_mysql_client(mysql)
    yield mysql
    routes.set_mysql_client(None)


@pytest.fixture
def app():
    application = FastAPI()
    application.include_router(auth_router, prefix="/api")
    application.include_router(routes.router, prefix="/api")
    return application


@pytest.fixture
def client(app):
    return TestClient(app)


def _login(client, username="admin"):
    resp = client.post("/api/auth/login", json={"username": username, "password": "123456"})
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


class TestQAAuditFullFlow:
    def test_deprecated_to_active_flow(self, client, mock_mysql):
        mock_mysql.get_qa_list.return_value = {
            "items": [
                {
                    "id": 1,
                    "question": "ETC怎么退款",
                    "answer": "3个工作日退款",
                    "category_l1": "售后",
                    "category_l2": "退款",
                    "status": "deprecated",
                }
            ],
            "total": 1,
            "page": 1,
            "page_size": 20,
        }
        mock_mysql.update_qa_status.return_value = {"qa_id": 1, "status": "active"}
        mock_mysql.insert_audit_log.return_value = 1

        h_admin = _login(client, "admin")
        resp = client.get("/api/qa/list", params={"status": "deprecated"}, headers=h_admin)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["status"] == "deprecated"
        qa_id = items[0]["id"]

        resp = client.put("/api/qa/status", json={"qa_id": qa_id, "status": "active"}, headers=h_admin)
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

    def test_deprecated_to_archived_flow(self, client, mock_mysql):
        mock_mysql.update_qa_status.return_value = {"qa_id": 2, "status": "archived"}
        mock_mysql.insert_audit_log.return_value = 1

        h_admin = _login(client, "admin")
        resp = client.put("/api/qa/status", json={"qa_id": 2, "status": "archived"}, headers=h_admin)
        assert resp.status_code == 200
        assert resp.json()["status"] == "archived"


class TestQAAuditAccess:
    def test_service_cannot_update_status(self, client, mock_mysql):
        h_service = _login(client, "service")
        resp = client.put("/api/qa/status", json={"qa_id": 1, "status": "active"}, headers=h_service)
        assert resp.status_code == 403

    def test_dept_cannot_update_status(self, client, mock_mysql):
        h_dept = _login(client, "dept")
        resp = client.put("/api/qa/status", json={"qa_id": 1, "status": "active"}, headers=h_dept)
        assert resp.status_code == 403

    def test_admin_can_update_status(self, client, mock_mysql):
        mock_mysql.update_qa_status.return_value = {"qa_id": 1, "status": "active"}
        mock_mysql.insert_audit_log.return_value = 1
        h_admin = _login(client, "admin")
        resp = client.put("/api/qa/status", json={"qa_id": 1, "status": "active"}, headers=h_admin)
        assert resp.status_code == 200

    def test_superadmin_can_update_status(self, client, mock_mysql):
        mock_mysql.update_qa_status.return_value = {"qa_id": 1, "status": "active"}
        mock_mysql.insert_audit_log.return_value = 1
        h_super = _login(client, "superadmin")
        resp = client.put("/api/qa/status", json={"qa_id": 1, "status": "active"}, headers=h_super)
        assert resp.status_code == 200

    def test_no_token_cannot_update_status(self, client, mock_mysql):
        resp = client.put("/api/qa/status", json={"qa_id": 1, "status": "active"})
        assert resp.status_code == 401


class TestQAAuditList:
    def test_admin_can_list_deprecated(self, client, mock_mysql):
        mock_mysql.get_qa_list.return_value = {"items": [], "total": 0, "page": 1, "page_size": 20}
        h = _login(client, "admin")
        resp = client.get("/api/qa/list", params={"status": "deprecated"}, headers=h)
        assert resp.status_code == 200

    def test_service_can_list_qa(self, client, mock_mysql):
        mock_mysql.get_qa_list.return_value = {"items": [], "total": 0, "page": 1, "page_size": 20}
        h = _login(client, "service")
        resp = client.get("/api/qa/list", headers=h)
        assert resp.status_code == 200

    def test_list_filters_by_status(self, client, mock_mysql):
        mock_mysql.get_qa_list.return_value = {"items": [], "total": 0, "page": 1, "page_size": 20}
        h = _login(client, "admin")
        client.get("/api/qa/list", params={"status": "deprecated"}, headers=h)
        call_kwargs = mock_mysql.get_qa_list.call_args[1]
        assert call_kwargs["status"] == "deprecated"
