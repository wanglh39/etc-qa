import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import routes
from api.auth import router as auth_router
from utils import jwt_utils
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
    mysql.get_qa_list.return_value = {"items": [], "total": 0, "page": 1, "page_size": 20}
    mysql.count_qa.return_value = {"total": 0, "active": 0, "deprecated": 0, "archived": 0}
    mysql.count_work_orders.return_value = {"total": 0, "submitted": 0, "processed": 0}
    mysql.get_category_stats.return_value = []
    mysql.get_audit_logs.return_value = {"items": [], "total": 0, "page": 1, "page_size": 20}
    mysql.get_user_list.return_value = {"items": [], "total": 0}
    mysql.get_role_list.return_value = []
    mysql.get_operation_logs.return_value = {"items": [], "total": 0, "page": 1, "page_size": 20}
    mysql.get_work_order_list.return_value = {"items": [], "total": 0, "page": 1, "page_size": 20}
    mysql.get_alerts.return_value = {"items": [], "total": 0}
    mysql.get_scheduler_status.return_value = {"jobs": []}
    mysql.get_scheduler_logs.return_value = {"items": [], "total": 0, "page": 1, "page_size": 20}
    mysql.get_system_status.return_value = {}
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


def _login(client, username):
    resp = client.post("/api/auth/login", json={"username": username, "password": "123456"})
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


ROLES = ["superadmin", "admin", "ops", "service", "dept"]

PROTECTED_ENDPOINTS = [
    {"method": "GET", "path": "/api/users", "allowed": ["superadmin"]},
    {"method": "GET", "path": "/api/roles", "allowed": ["superadmin"]},
    {"method": "GET", "path": "/api/operations", "allowed": ["superadmin"]},
    {
        "method": "POST",
        "path": "/api/add",
        "body": {"question": "q", "answer": "a", "category_l1": "c", "category_l2": "d"},
        "allowed": ["admin", "superadmin"],
    },
    {
        "method": "PUT",
        "path": "/api/qa/status",
        "body": {"qa_id": 1, "status": "active"},
        "allowed": ["admin", "superadmin"],
    },
    {"method": "GET", "path": "/api/config/enterprise_name", "allowed": ["admin", "superadmin"]},
    {"method": "POST", "path": "/api/config/reload", "allowed": ["admin", "superadmin"]},
    {"method": "DELETE", "path": "/api/qa/1", "allowed": ["admin", "superadmin"]},
    {"method": "GET", "path": "/api/audit/history", "allowed": ["admin", "superadmin"]},
    {"method": "GET", "path": "/api/stats", "allowed": ["admin", "superadmin", "ops"]},
    {"method": "GET", "path": "/api/stats/trend", "allowed": ["admin", "superadmin", "ops"]},
    {"method": "GET", "path": "/api/scheduler/status", "allowed": ["admin", "superadmin", "ops"]},
    {"method": "GET", "path": "/api/scheduler/logs", "allowed": ["admin", "superadmin", "ops"]},
    {"method": "GET", "path": "/api/alerts", "allowed": ["admin", "superadmin", "ops"]},
    {"method": "GET", "path": "/api/alerts/metrics", "allowed": ["admin", "superadmin", "ops"]},
    {"method": "GET", "path": "/api/system/status", "allowed": ["superadmin", "ops"]},
]


@pytest.fixture
def logged_in_clients(client):
    return {role: _login(client, role) for role in ROLES}


def _make_request(client, method, path, headers, body=None):
    if method == "GET":
        return client.get(path, headers=headers)
    elif method == "POST":
        return client.post(path, json=body or {}, headers=headers)
    elif method == "PUT":
        return client.put(path, json=body or {}, headers=headers)
    elif method == "DELETE":
        return client.delete(path, headers=headers)


class TestPermissionMatrix:
    @pytest.mark.parametrize("endpoint", PROTECTED_ENDPOINTS)
    @pytest.mark.parametrize("role", ROLES)
    def test_role_access(self, client, mock_mysql, logged_in_clients, endpoint, role):
        resp = _make_request(
            client, endpoint["method"], endpoint["path"], logged_in_clients[role], endpoint.get("body")
        )
        if role in endpoint["allowed"]:
            assert resp.status_code != 403, f"{role} 应能访问 {endpoint['method']} {endpoint['path']}，但收到 403"
        else:
            assert resp.status_code == 403, (
                f"{role} 不应访问 {endpoint['method']} {endpoint['path']}，但收到 {resp.status_code}"
            )


class TestPublicEndpoints:
    @pytest.mark.parametrize("role", ROLES)
    def test_qa_list_accessible_by_all(self, client, mock_mysql, role):
        h = _login(client, role)
        resp = client.get("/api/qa/list", headers=h)
        assert resp.status_code == 200

    @pytest.mark.parametrize("role", ROLES)
    def test_work_orders_list_accessible_by_all(self, client, mock_mysql, role):
        h = _login(client, role)
        resp = client.get("/api/work_orders", headers=h)
        assert resp.status_code == 200

    @pytest.mark.parametrize("role", ROLES)
    def test_categories_accessible_by_all(self, client, mock_mysql, role):
        h = _login(client, role)
        resp = client.get("/api/categories", headers=h)
        assert resp.status_code == 200

    @pytest.mark.parametrize("role", ROLES)
    def test_work_orders_create_accessible_by_all(self, client, mock_mysql, role):
        mock_mysql.insert_work_order_full.return_value = 1
        h = _login(client, role)
        resp = client.post("/api/work_orders", json={"next_dept": "aftersale"}, headers=h)
        assert resp.status_code == 200


class TestNoTokenAccess:
    @pytest.mark.parametrize("endpoint", PROTECTED_ENDPOINTS)
    def test_no_token_returns_401(self, client, mock_mysql, endpoint):
        resp = _make_request(client, endpoint["method"], endpoint["path"], None, endpoint.get("body"))
        assert resp.status_code == 401
