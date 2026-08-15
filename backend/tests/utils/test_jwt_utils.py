from datetime import datetime, timedelta
import time

import jwt
import pytest

from utils.jwt_utils import ALGORITHM, SECRET_KEY, authenticate, create_token, verify_token


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