from utils.rate_limit import RateLimiter


class TestRateLimiter:
    def test_allows_under_limit(self):
        rl = RateLimiter()
        assert rl.check("k", 3, 60) is True
        assert rl.check("k", 3, 60) is True
        assert rl.check("k", 3, 60) is True

    def test_blocks_over_limit(self):
        rl = RateLimiter()
        for _ in range(3):
            assert rl.check("k2", 3, 60) is True
        assert rl.check("k2", 3, 60) is False

    def test_reset_single_key(self):
        rl = RateLimiter()
        for _ in range(3):
            rl.check("k3", 3, 60)
        assert rl.check("k3", 3, 60) is False
        rl.reset("k3")
        assert rl.check("k3", 3, 60) is True

    def test_window_isolation(self):
        rl = RateLimiter()
        for _ in range(3):
            rl.check("k4", 3, 60)
        assert rl.check("k5", 3, 60) is True
