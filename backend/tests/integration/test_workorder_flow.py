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


def _login(client, username="service"):
    resp = client.post("/api/auth/login", json={"username": username, "password": "123456"})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestWorkOrderFullFlow:
    def test_service_create_dept_view_dept_reply_admin_stats(self, client, mock_mysql):
        mock_mysql.insert_work_order_full.return_value = 42
        mock_mysql.get_work_order_detail.side_effect = [
            {"id": 42, "external_id": "WO-20260824-1234", "raw_data": json.dumps({"customer_name": "test"}), "status": "submitted", "dept": "aftersale"},
            {"id": 42, "external_id": "WO-20260824-1234", "raw_data": json.dumps({"customer_name": "test", "handle_remark": "已处理"}), "status": "processed", "dept": "aftersale"},
        ]
        mock_mysql.get_work_order_list.return_value = {
            "items": [{"id": 42, "external_id": "WO-20260824-1234", "raw_data": "{}", "status": "submitted", "dept": "aftersale"}],
            "total": 1,
            "page": 1,
            "page_size": 20,
        }
        mock_mysql.update_work_order_reply.return_value = None
        mock_mysql.count_work_orders.return_value = {"total": 1, "submitted": 0, "processed": 1}
        mock_mysql.count_qa.return_value = {"total": 10, "active": 8, "deprecated": 1, "archived": 1}
        mock_mysql.get_category_stats.return_value = []

        h_service = _login(client, "service")
        resp = client.post("/api/work_orders", json={
            "service_id": "S001",
            "customer_name": "test_customer",
            "phone": "13800001111",
            "problem_type": "ETC重复扣费",
            "next_dept": "aftersale",
            "priority": "high",
            "detail_desc": "测试工单",
        }, headers=h_service)
        assert resp.status_code == 200
        wo_data = resp.json()
        assert wo_data["status"] == "submitted"
        assert wo_data["dept"] == "aftersale"
        wo_id = wo_data["id"]

        h_dept = _login(client, "dept")
        resp = client.get("/api/work_orders", params={"status": "submitted"}, headers=h_dept)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) > 0

        resp = client.put(f"/api/work_orders/{wo_id}/reply", json={"handle_remark": "已处理"}, headers=h_dept)
        assert resp.status_code == 200
        assert resp.json()["status"] == "processed"

        h_admin = _login(client, "admin")
        resp = client.get("/api/stats", headers=h_admin)
        assert resp.status_code == 200
        stats = resp.json()
        assert "work_order_total" in stats
        assert "work_order_submitted" in stats
        assert "work_order_processed" in stats


class TestWorkOrderDeptIsolation:
    def test_dept_cannot_view_other_dept_workorder(self, client, mock_mysql):
        mock_mysql.get_work_order_detail.return_value = {
            "id": 99,
            "external_id": "WO-X",
            "raw_data": "{}",
            "status": "submitted",
            "dept": "finance",
        }
        h_dept = _login(client, "dept")
        resp = client.get("/api/work_orders/99", headers=h_dept)
        assert resp.status_code == 403

    def test_dept_can_view_own_dept_workorder(self, client, mock_mysql):
        mock_mysql.get_work_order_detail.return_value = {
            "id": 99,
            "external_id": "WO-X",
            "raw_data": "{}",
            "status": "submitted",
            "dept": "aftersale",
        }
        h_dept = _login(client, "dept")
        resp = client.get("/api/work_orders/99", headers=h_dept)
        assert resp.status_code == 200

    def test_dept_list_forced_to_own_dept(self, client, mock_mysql):
        mock_mysql.get_work_order_list.return_value = {"items": [], "total": 0, "page": 1, "page_size": 20}
        h_dept = _login(client, "dept")
        client.get("/api/work_orders", params={"dept": "finance"}, headers=h_dept)
        call_kwargs = mock_mysql.get_work_order_list.call_args[1]
        assert call_kwargs["dept"] == "aftersale"

    def test_dept_cannot_reply_other_dept(self, client, mock_mysql):
        mock_mysql.get_work_order_detail.return_value = {
            "id": 99,
            "external_id": "WO-X",
            "raw_data": "{}",
            "status": "submitted",
            "dept": "finance",
        }
        h_dept = _login(client, "dept")
        resp = client.put("/api/work_orders/99/reply", json={"handle_remark": "x"}, headers=h_dept)
        assert resp.status_code == 403


class TestWorkOrderStatusFlow:
    def test_create_returns_submitted(self, client, mock_mysql):
        mock_mysql.insert_work_order_full.return_value = 1
        h = _login(client, "service")
        resp = client.post("/api/work_orders", json={"next_dept": "aftersale"}, headers=h)
        assert resp.status_code == 200
        assert resp.json()["status"] == "submitted"

    def test_reply_changes_to_processed(self, client, mock_mysql):
        mock_mysql.get_work_order_detail.side_effect = [
            {"id": 1, "external_id": "WO-1", "raw_data": "{}", "status": "submitted", "dept": "aftersale"},
            {"id": 1, "external_id": "WO-1", "raw_data": '{"handle_remark": "ok"}', "status": "processed", "dept": "aftersale"},
        ]
        mock_mysql.update_work_order_reply.return_value = None
        h = _login(client, "admin")
        resp = client.put("/api/work_orders/1/reply", json={"handle_remark": "ok"}, headers=h)
        assert resp.status_code == 200
        assert resp.json()["status"] == "processed"

    def test_get_nonexistent_returns_404(self, client, mock_mysql):
        mock_mysql.get_work_order_detail.return_value = None
        h = _login(client, "admin")
        resp = client.get("/api/work_orders/999", headers=h)
        assert resp.status_code == 404

    def test_reply_nonexistent_returns_404(self, client, mock_mysql):
        mock_mysql.get_work_order_detail.return_value = None
        h = _login(client, "admin")
        resp = client.put("/api/work_orders/999/reply", json={"handle_remark": "x"}, headers=h)
        assert resp.status_code == 404

    def test_create_no_mysql_returns_500(self, client):
        routes.set_mysql_client(None)
        h = _login(client, "service")
        resp = client.post("/api/work_orders", json={"next_dept": "aftersale"}, headers=h)
        assert resp.status_code == 500


class TestWorkOrderAccess:
    def test_no_token_create_returns_401(self, client, mock_mysql):
        resp = client.post("/api/work_orders", json={"next_dept": "aftersale"})
        assert resp.status_code == 401

    def test_service_can_create(self, client, mock_mysql):
        mock_mysql.insert_work_order_full.return_value = 1
        h = _login(client, "service")
        resp = client.post("/api/work_orders", json={"next_dept": "aftersale"}, headers=h)
        assert resp.status_code == 200

    def test_admin_can_create(self, client, mock_mysql):
        mock_mysql.insert_work_order_full.return_value = 1
        h = _login(client, "admin")
        resp = client.post("/api/work_orders", json={"next_dept": "aftersale"}, headers=h)
        assert resp.status_code == 200

    def test_stats_requires_admin_or_above(self, client, mock_mysql):
        mock_mysql.count_work_orders.return_value = {"total": 0, "submitted": 0, "processed": 0}
        mock_mysql.count_qa.return_value = {"total": 0, "active": 0, "deprecated": 0, "archived": 0}
        mock_mysql.get_category_stats.return_value = []
        h_service = _login(client, "service")
        resp = client.get("/api/stats", headers=h_service)
        assert resp.status_code == 403
        h_admin = _login(client, "admin")
        resp = client.get("/api/stats", headers=h_admin)
        assert resp.status_code == 200