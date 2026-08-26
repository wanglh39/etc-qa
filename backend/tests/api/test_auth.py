from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.auth import router as auth_router
from utils import jwt_utils
from utils.jwt_utils import create_token, set_mysql_client, verify_token
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
def app():
    application = FastAPI()
    application.include_router(auth_router, prefix="/api")
    return application


@pytest.fixture
def client(app):
    return TestClient(app)


def _header(role="superadmin", dept="", impersonated_by=None):
    token = create_token(role, role, dept, impersonated_by=impersonated_by)
    return {"Authorization": f"Bearer {token}"}


class TestVerifyEndpoint:
    def test_valid_token_returns_user_info(self, client):
        token = create_token("admin", "admin", "")
        resp = client.get("/api/auth/verify", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "admin"
        assert data["role"] == "admin"

    def test_valid_token_with_dept(self, client):
        token = create_token("dept", "dept", "aftersale")
        resp = client.get("/api/auth/verify", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["dept"] == "aftersale"

    def test_no_token_returns_401(self, client):
        resp = client.get("/api/auth/verify")
        assert resp.status_code == 401

    def test_invalid_token_returns_401(self, client):
        resp = client.get("/api/auth/verify", headers={"Authorization": "Bearer invalidtoken123"})
        assert resp.status_code == 401

    def test_malformed_header_returns_401(self, client):
        resp = client.get("/api/auth/verify", headers={"Authorization": "NotBearer abc"})
        assert resp.status_code == 401


class TestImpersonateAccess:
    def test_superadmin_can_impersonate_admin(self, client):
        resp = client.post("/api/auth/impersonate", json={"target_role": "admin"}, headers=_header("superadmin"))
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "admin"
        assert data["username"] == "admin"

    def test_superadmin_can_impersonate_service(self, client):
        resp = client.post("/api/auth/impersonate", json={"target_role": "service"}, headers=_header("superadmin"))
        assert resp.status_code == 200
        assert resp.json()["role"] == "service"

    def test_superadmin_can_impersonate_dept(self, client):
        resp = client.post("/api/auth/impersonate", json={"target_role": "dept"}, headers=_header("superadmin"))
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "dept"
        assert data["dept"] == "aftersale"

    def test_superadmin_can_impersonate_ops(self, client):
        resp = client.post("/api/auth/impersonate", json={"target_role": "ops"}, headers=_header("superadmin"))
        assert resp.status_code == 200
        assert resp.json()["role"] == "ops"

    def test_admin_cannot_impersonate(self, client):
        resp = client.post("/api/auth/impersonate", json={"target_role": "service"}, headers=_header("admin"))
        assert resp.status_code == 403

    def test_service_cannot_impersonate(self, client):
        resp = client.post("/api/auth/impersonate", json={"target_role": "admin"}, headers=_header("service"))
        assert resp.status_code == 403

    def test_dept_cannot_impersonate(self, client):
        resp = client.post("/api/auth/impersonate", json={"target_role": "admin"}, headers=_header("dept", "aftersale"))
        assert resp.status_code == 403

    def test_no_token_cannot_impersonate(self, client):
        resp = client.post("/api/auth/impersonate", json={"target_role": "admin"})
        assert resp.status_code == 401


class TestImpersonateValidation:
    def test_unsupported_role_returns_400(self, client):
        resp = client.post("/api/auth/impersonate", json={"target_role": "god"}, headers=_header("superadmin"))
        assert resp.status_code == 400

    def test_empty_role_returns_400(self, client):
        resp = client.post("/api/auth/impersonate", json={"target_role": ""}, headers=_header("superadmin"))
        assert resp.status_code == 400


class TestImpersonateToken:
    def test_returned_token_contains_impersonated_by(self, client):
        resp = client.post("/api/auth/impersonate", json={"target_role": "service"}, headers=_header("superadmin"))
        assert resp.status_code == 200
        token = resp.json()["access_token"]
        payload = verify_token(token)
        assert payload["impersonated_by"] == "superadmin"

    def test_returned_token_has_target_role(self, client):
        resp = client.post("/api/auth/impersonate", json={"target_role": "dept"}, headers=_header("superadmin"))
        token = resp.json()["access_token"]
        payload = verify_token(token)
        assert payload["role"] == "dept"
        assert payload["dept"] == "aftersale"

    def test_returned_token_can_access_verify(self, client):
        resp = client.post("/api/auth/impersonate", json={"target_role": "admin"}, headers=_header("superadmin"))
        token = resp.json()["access_token"]
        resp2 = client.get("/api/auth/verify", headers={"Authorization": f"Bearer {token}"})
        assert resp2.status_code == 200
        assert resp2.json()["role"] == "admin"


class TestImpersonateAuditLog:
    @patch("utils.jwt_utils._mysql_client")
    def test_audit_log_written(self, mock_mysql, client):
        mock_mysql.insert_operation_log = MagicMock()
        client.post("/api/auth/impersonate", json={"target_role": "service"}, headers=_header("superadmin"))
        mock_mysql.insert_operation_log.assert_called_once()
        call_args = mock_mysql.insert_operation_log.call_args[0]
        assert call_args[0] == "superadmin"
        assert call_args[1] == "impersonate"
        assert "service" in call_args[4]

    @patch("utils.jwt_utils._mysql_client")
    def test_audit_log_failure_does_not_break_impersonate(self, mock_mysql, client):
        mock_mysql.insert_operation_log = MagicMock(side_effect=Exception("db down"))
        resp = client.post("/api/auth/impersonate", json={"target_role": "admin"}, headers=_header("superadmin"))
        assert resp.status_code == 200

    def test_no_mysql_client_no_audit_log(self, client):
        with patch("utils.jwt_utils._mysql_client", None):
            resp = client.post("/api/auth/impersonate", json={"target_role": "admin"}, headers=_header("superadmin"))
            assert resp.status_code == 200


class TestLoginFlow:
    def test_login_success(self, client):
        resp = client.post("/api/auth/login", json={"username": "admin", "password": "123456"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["role"] == "admin"

    def test_login_wrong_password(self, client):
        resp = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
        assert resp.status_code == 401

    def test_login_unknown_user(self, client):
        resp = client.post("/api/auth/login", json={"username": "ghost", "password": "123456"})
        assert resp.status_code == 401

    def test_login_returns_usable_token(self, client):
        resp = client.post("/api/auth/login", json={"username": "service", "password": "123456"})
        token = resp.json()["access_token"]
        resp2 = client.get("/api/auth/verify", headers={"Authorization": f"Bearer {token}"})
        assert resp2.status_code == 200
        assert resp2.json()["role"] == "service"

    def test_login_dept_returns_dept_field(self, client):
        resp = client.post("/api/auth/login", json={"username": "dept", "password": "123456"})
        assert resp.status_code == 200
        assert resp.json()["dept"] == "aftersale"