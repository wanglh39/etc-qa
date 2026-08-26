import pytest

from utils.jwt_utils import create_token, verify_token
from utils.password import hash_password, verify_password
from utils.rate_limit import RateLimiter


class TestJWTBenchmark:
    def test_create_token(self, benchmark):
        benchmark(create_token, "admin", "admin", "aftersale")

    def test_verify_token(self, benchmark):
        token = create_token("admin", "admin", "aftersale")
        benchmark(verify_token, token)


class TestPasswordBenchmark:
    def test_hash_password(self, benchmark):
        benchmark(hash_password, "test_password_123")

    def test_verify_password_correct(self, benchmark):
        hashed = hash_password("test_password_123")
        benchmark(verify_password, "test_password_123", hashed)


class TestRateLimitBenchmark:
    def test_rate_limit_check(self, benchmark):
        limiter = RateLimiter()

        def do_check():
            return limiter.check("test_key", limit=100, window_seconds=60)

        benchmark(do_check)