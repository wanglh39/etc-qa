from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from api import routes
from api.auth import LoginRequest, login
from models.schemas import WorkOrderReplyRequest
from utils.rate_limit import limiter


def _dept_user(dept="aftersale"):
    return {"sub": "dept", "role": "dept", "dept": dept}


class TestConfigRedact:
    def test_redact_secrets_recursive(self):
        value = {"llm": {"api_key": "sk-123", "base_url": "https://x", "nested": [{"token": "t"}]}}
        out = routes._redact_secrets(value)
        assert out["llm"]["api_key"] == "***"
        assert out["llm"]["base_url"] == "https://x"
        assert out["llm"]["nested"][0]["token"] == "***"

    def test_get_config_value_redacts(self):
        with patch("api.routes.get_business_config", return_value={"api_key": "sk-123", "name": "ETC"}):
            result = routes.get_config_value("llm")
        assert result == {"key": "llm", "value": {"api_key": "***", "name": "ETC"}}


class TestWorkOrderDeptIsolation:
    def _set_order(self, dept):
        mock_mysql = MagicMock()
        mock_mysql.get_work_order_detail.return_value = {
            "id": 1,
            "external_id": "WO-1",
            "status": "submitted",
            "dept": dept,
            "raw_data": None,
        }
        routes.set_mysql_client(mock_mysql)
        return mock_mysql

    def test_list_work_orders_dept_passthrough(self):
        mock_mysql = MagicMock()
        mock_mysql.get_work_order_list.return_value = {"items": [], "total": 0, "page": 1, "page_size": 20}
        routes.set_mysql_client(mock_mysql)
        routes.list_work_orders(page=1, page_size=20, dept="finance")
        mock_mysql.get_work_order_list.assert_called_once_with(page=1, page_size=20, status=None, dept="finance")

    def test_list_work_orders_no_dept(self):
        mock_mysql = MagicMock()
        mock_mysql.get_work_order_list.return_value = {"items": [], "total": 0, "page": 1, "page_size": 20}
        routes.set_mysql_client(mock_mysql)
        routes.list_work_orders(page=1, page_size=20)
        mock_mysql.get_work_order_list.assert_called_once_with(page=1, page_size=20, status=None, dept=None)

    def test_get_work_order_ok(self):
        self._set_order("aftersale")
        result = routes.get_work_order(1)
        assert result.status == "submitted"

    def test_get_work_order_not_found(self):
        mock_mysql = MagicMock()
        mock_mysql.get_work_order_detail.return_value = None
        routes.set_mysql_client(mock_mysql)
        with pytest.raises(HTTPException) as exc:
            routes.get_work_order(999)
        assert exc.value.status_code == 404

    def test_reply_work_order_ok(self):
        self._set_order("aftersale")
        req = WorkOrderReplyRequest(handle_remark="x")
        mock_mysql = routes.mysql_client
        mock_mysql.update_work_order.return_value = True
        result = routes.reply_work_order(1, req)
        assert result is not None


class TestLoginRateLimit:
    def test_login_rate_limited_after_5_attempts(self):
        limiter.reset()
        req = LoginRequest(username="admin", password="wrong")
        request = MagicMock()
        request.client.host = "203.0.113.7"
        for _ in range(5):
            with pytest.raises(HTTPException) as exc:
                login(req, request)
            assert exc.value.status_code == 401
        with pytest.raises(HTTPException) as exc:
            login(req, request)
        assert exc.value.status_code == 429
        limiter.reset()
