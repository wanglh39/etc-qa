import asyncio
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from utils.auth_middleware import get_current_user, require_role


class _FakeCredentials:
    def __init__(self, token):
        self.credentials = token


class TestGetCurrentUser:
    def test_credentials_none_raises_401(self):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(get_current_user(None))
        assert exc.value.status_code == 401
        assert exc.value.detail == "未提供认证令牌"

    def test_verify_token_exception_raises_401(self):
        credentials = _FakeCredentials("bad-token")
        with patch("utils.auth_middleware.verify_token", side_effect=Exception("decode failed")):
            with pytest.raises(HTTPException) as exc:
                asyncio.run(get_current_user(credentials))
        assert exc.value.status_code == 401
        assert exc.value.detail == "令牌无效或已过期"

    def test_valid_credentials_returns_payload(self):
        credentials = _FakeCredentials("good-token")
        payload = {"sub": "admin", "role": "admin", "dept": ""}
        with patch("utils.auth_middleware.verify_token", return_value=payload):
            result = asyncio.run(get_current_user(credentials))
        assert result == payload


class TestRequireRole:
    def test_role_not_allowed_raises_403(self):
        checker = require_role("admin")
        with pytest.raises(HTTPException) as exc:
            asyncio.run(checker({"role": "service", "dept": ""}))
        assert exc.value.status_code == 403
        assert exc.value.detail == "权限不足"

    def test_role_allowed_returns_user(self):
        checker = require_role("admin")
        user = {"role": "admin", "dept": ""}
        result = asyncio.run(checker(user))
        assert result == user

    def test_multiple_roles_any_match_returns_user(self):
        checker = require_role("admin", "service")
        user = {"role": "service", "dept": ""}
        result = asyncio.run(checker(user))
        assert result == user

    def test_multiple_roles_none_match_raises_403(self):
        checker = require_role("admin", "service")
        with pytest.raises(HTTPException) as exc:
            asyncio.run(checker({"role": "dept", "dept": "aftersale"}))
        assert exc.value.status_code == 403

    def test_user_missing_role_raises_403(self):
        checker = require_role("admin")
        with pytest.raises(HTTPException) as exc:
            asyncio.run(checker({"dept": "aftersale"}))
        assert exc.value.status_code == 403