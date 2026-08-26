import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import jwt
import pytest

from utils.jwt_utils import ALGORITHM, SECRET_KEY, authenticate, create_token, set_mysql_client, verify_token


class TestCreateToken:
    def test_returns_str_token(self):
        token = create_token("admin", "admin", "")
        assert isinstance(token, str)

    def test_token_contains_correct_payload(self):
        token = create_token("admin", "admin", "aftersale")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "admin"
        assert payload["role"] == "admin"
        assert payload["dept"] == "aftersale"
        assert "exp" in payload
        assert "iat" in payload

    def test_token_exp_iat_diff_is_24_hours(self):
        token = create_token("u", "service", "")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert abs((payload["exp"] - payload["iat"]) - 24 * 3600) <= 2

    def test_token_iat_close_to_now(self):
        now = time.time()
        token = create_token("u", "service", "")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert abs(payload["iat"] - now) <= 5

    def test_token_exp_close_to_24h_from_now(self):
        now = time.time()
        token = create_token("u", "service", "")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert abs(payload["exp"] - (now + 24 * 3600)) <= 5


class TestVerifyToken:
    def test_valid_token_returns_payload(self):
        token = create_token("admin", "admin", "")
        payload = verify_token(token)
        assert payload["sub"] == "admin"
        assert payload["role"] == "admin"

    def test_expired_token_raises(self):
        expired_payload = {
            "sub": "admin",
            "role": "admin",
            "dept": "",
            "exp": datetime.utcnow() - timedelta(hours=1),
            "iat": datetime.utcnow() - timedelta(hours=2),
        }
        token = jwt.encode(expired_payload, SECRET_KEY, algorithm=ALGORITHM)
        with pytest.raises(jwt.ExpiredSignatureError):
            verify_token(token)

    def test_invalid_token_raises(self):
        with pytest.raises(jwt.DecodeError):
            verify_token("not.a.valid.token")

    def test_wrong_secret_raises(self):
        token = jwt.encode({"sub": "x"}, "wrong-secret", algorithm=ALGORITHM)
        with pytest.raises(jwt.InvalidSignatureError):
            verify_token(token)


class TestAuthenticate:
    def test_superadmin_default_password_success(self):
        result = authenticate("superadmin", "123456")
        assert result == {"username": "superadmin", "role": "superadmin", "dept": ""}

    def test_admin_default_password_success(self):
        result = authenticate("admin", "123456")
        assert result == {"username": "admin", "role": "admin", "dept": ""}

    def test_wrong_password_returns_none(self):
        result = authenticate("admin", "wrong-pw-xyz")
        assert result is None

    def test_unknown_user_returns_none(self):
        result = authenticate("nobody", "123456")
        assert result is None

    def test_dept_user_success(self):
        result = authenticate("dept", "123456")
        assert result == {"username": "dept", "role": "dept", "dept": "aftersale"}


class TestAuthenticateDB:
    def setup_method(self):
        set_mysql_client(None)

    def teardown_method(self):
        set_mysql_client(None)

    def test_db_active_user_returns_from_db(self):
        mock_db = MagicMock()
        mock_db.get_user_by_username.return_value = {
            "username": "admin",
            "password_hash": "123456",
            "role": "admin",
            "dept": "ops",
            "status": "active",
        }
        set_mysql_client(mock_db)
        with patch("utils.jwt_utils.verify_password", return_value=True):
            result = authenticate("admin", "123456")
        assert result == {"username": "admin", "role": "admin", "dept": "ops"}

    def test_db_disabled_user_falls_back_to_hardcoded(self):
        mock_db = MagicMock()
        mock_db.get_user_by_username.return_value = {
            "username": "admin",
            "password_hash": "xxx",
            "role": "admin",
            "dept": "",
            "status": "disabled",
        }
        set_mysql_client(mock_db)
        result = authenticate("admin", "123456")
        assert result == {"username": "admin", "role": "admin", "dept": ""}

    def test_db_user_not_found_falls_back_to_hardcoded(self):
        mock_db = MagicMock()
        mock_db.get_user_by_username.return_value = None
        set_mysql_client(mock_db)
        result = authenticate("admin", "123456")
        assert result == {"username": "admin", "role": "admin", "dept": ""}

    def test_db_exception_falls_back_to_hardcoded(self):
        mock_db = MagicMock()
        mock_db.get_user_by_username.side_effect = Exception("DB down")
        set_mysql_client(mock_db)
        result = authenticate("admin", "123456")
        assert result == {"username": "admin", "role": "admin", "dept": ""}

    def test_db_password_mismatch_falls_back_to_hardcoded(self):
        mock_db = MagicMock()
        mock_db.get_user_by_username.return_value = {
            "username": "admin",
            "password_hash": "wronghash",
            "role": "admin",
            "dept": "",
            "status": "active",
        }
        set_mysql_client(mock_db)
        with patch("utils.jwt_utils.verify_password", side_effect=[False, True]):
            result = authenticate("admin", "123456")
        assert result == {"username": "admin", "role": "admin", "dept": ""}
