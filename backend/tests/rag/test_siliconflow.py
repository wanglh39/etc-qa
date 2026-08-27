import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch

import httpx
import numpy as np
import pytest

from rag.siliconflow import EmbeddingClient, RerankClient, SiliconFlowBalancer, _parse_keys


class _Resp:
    def __init__(self, status_code, body=None):
        self.status_code = status_code
        self._body = body or {}

    def json(self):
        return self._body

    def raise_for_status(self):
        raise RuntimeError(f"HTTP {self.status_code}")


def _patch_client_post(fake_post):
    """替换共享 httpx.Client 的 post 方法。"""
    fake_client = MagicMock()
    fake_client.post.side_effect = fake_post
    return patch("rag.siliconflow._get_shared_client", return_value=fake_client)


class TestParseKeys:
    def test_filters_empty_and_unresolved(self):
        assert _parse_keys("a, b ,,${X}, c ") == ["a", "b", "c"]

    def test_empty_string(self):
        assert _parse_keys("") == []


class TestBalancer:
    def test_no_keys_raises(self):
        with pytest.raises(RuntimeError):
            SiliconFlowBalancer([], "https://example.com")

    def test_pick_longest_idle(self):
        used = []

        def fake_post(url, json=None, headers=None, timeout=None):
            used.append(headers["Authorization"].split(" ")[1])
            return _Resp(200, {"ok": True})

        balancer = SiliconFlowBalancer(["A", "B"], "https://example.com")
        with _patch_client_post(fake_post):
            balancer.post("/x", {})
            balancer.post("/x", {})
            balancer.post("/x", {})
        assert used == ["A", "B", "A"]

    def test_failover_on_429(self):
        calls = []

        def fake_post(url, json=None, headers=None, timeout=None):
            key = headers["Authorization"].split(" ")[1]
            calls.append(key)
            if key == "A":
                return _Resp(429)
            return _Resp(200, {"ok": True})

        balancer = SiliconFlowBalancer(["A", "B"], "https://example.com")
        with _patch_client_post(fake_post):
            result = balancer.post("/x", {})
        assert result == {"ok": True}
        assert calls == ["A", "B"]

    def test_all_keys_fail(self):
        def fake_post(url, json=None, headers=None, timeout=None):
            return _Resp(500)

        balancer = SiliconFlowBalancer(["A", "B"], "https://example.com")
        with _patch_client_post(fake_post):
            with pytest.raises(RuntimeError):
                balancer.post("/x", {})


class TestEmbeddingClient:
    def test_encode_normalizes_and_orders(self):
        balancer = SiliconFlowBalancer(["A"], "https://example.com")
        client = EmbeddingClient(balancer, "model")
        fake_data = {
            "data": [
                {"index": 1, "embedding": [0.0, 3.0]},
                {"index": 0, "embedding": [3.0, 0.0]},
            ]
        }
        with patch.object(balancer, "post", return_value=fake_data):
            arr = client.encode(["q1", "q2"])
        assert arr.shape == (2, 2)
        assert np.allclose(np.linalg.norm(arr, axis=1), [1.0, 1.0])
        assert arr[0].tolist() == pytest.approx([1.0, 0.0])
        assert arr[1].tolist() == pytest.approx([0.0, 1.0])


class TestRerankClient:
    def test_predict_maps_index_to_input_order(self):
        balancer = SiliconFlowBalancer(["A"], "https://example.com")
        client = RerankClient(balancer, "model")
        fake_data = {
            "results": [
                {"index": 1, "relevance_score": 0.9},
                {"index": 0, "relevance_score": 0.3},
            ]
        }
        with patch.object(balancer, "post", return_value=fake_data):
            scores = client.predict([["q", "d0"], ["q", "d1"]])
        assert scores.tolist() == pytest.approx([0.3, 0.9])


def _fake_ok_post(record):
    """构造一个返回 200 的 httpx.post 替身，记录被选中的 key。"""

    def fake_post(url, json=None, headers=None, timeout=None):
        key = headers["Authorization"].split(" ")[1]
        record.append(key)
        return _Resp(200, {"ok": True})

    return fake_post


class TestBalancerLoadBalance:
    """压力/均衡：多 key 下请求应均匀分散，而非集中到单个 key。"""

    def test_sequential_round_robin(self):
        used = []
        balancer = SiliconFlowBalancer(["A", "B", "C"], "https://example.com")
        with _patch_client_post(_fake_ok_post(used)):
            for _ in range(30):
                balancer.post("/x", {})
        counts = Counter(used)
        assert counts == {"A": 10, "B": 10, "C": 10}

    def test_concurrent_round_robin(self):
        used = []
        lock = threading.Lock()

        def fake_post(url, json=None, headers=None, timeout=None):
            key = headers["Authorization"].split(" ")[1]
            with lock:
                used.append(key)
            return _Resp(200, {"ok": True})

        balancer = SiliconFlowBalancer(["A", "B", "C"], "https://example.com")
        with _patch_client_post(fake_post):
            with ThreadPoolExecutor(max_workers=16) as ex:
                list(ex.map(lambda _: balancer.post("/x", {}), range(300)))
        counts = Counter(used)
        assert sum(counts.values()) == 300
        for k in ["A", "B", "C"]:
            assert abs(counts[k] - 100) <= 2, f"key {k} count {counts[k]} deviates too much"


class TestBalancerRateLimit:
    """限流：单 key 429 后进入冷却，切到下一个；冷却期内不再选中；到期后恢复。"""

    def test_429_failover_then_cooldown_blocks_reuse(self):
        clock = [0.0]
        calls = []

        def fake_post(url, json=None, headers=None, timeout=None):
            key = headers["Authorization"].split(" ")[1]
            calls.append(key)
            if key == "A":
                return _Resp(429)
            return _Resp(200, {"ok": True})

        balancer = SiliconFlowBalancer(["A", "B"], "https://example.com", cooldown_seconds=60.0)
        with patch("rag.siliconflow.time.perf_counter", side_effect=lambda: clock[0]), _patch_client_post(fake_post):
            # 第一次：A 429 → 冷却 A → 切 B
            assert balancer.post("/x", {}) == {"ok": True}
            assert calls == ["A", "B"]
            # 冷却期内（clock 未推进）再次调用：A 被跳过，直接用 B
            assert balancer.post("/x", {}) == {"ok": True}
            assert calls == ["A", "B", "B"]

    def test_cooldown_expires_restores_key(self):
        clock = [0.0]
        calls = []

        def fake_post(url, json=None, headers=None, timeout=None):
            key = headers["Authorization"].split(" ")[1]
            calls.append(key)
            if key == "A":
                return _Resp(429)
            return _Resp(200, {"ok": True})

        balancer = SiliconFlowBalancer(["A", "B"], "https://example.com", cooldown_seconds=60.0)
        with patch("rag.siliconflow.time.perf_counter", side_effect=lambda: clock[0]), _patch_client_post(fake_post):
            balancer.post("/x", {})  # A 冷却
            clock[0] = 61.0  # 冷却到期
            balancer.post("/x", {})  # A 恢复可用，被重新选中（仍 429，再切 B）
            assert calls == ["A", "B", "A", "B"]

    @pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
    def test_retryable_statuses_trigger_cooldown(self, status):
        calls = []

        def fake_post(url, json=None, headers=None, timeout=None):
            key = headers["Authorization"].split(" ")[1]
            calls.append(key)
            if key == "A":
                return _Resp(status)
            return _Resp(200, {"ok": True})

        balancer = SiliconFlowBalancer(["A", "B"], "https://example.com")
        with _patch_client_post(fake_post):
            assert balancer.post("/x", {}) == {"ok": True}
        assert calls == ["A", "B"]

    def test_network_error_marks_cooldown(self):
        calls = []

        def fake_post(url, json=None, headers=None, timeout=None):
            key = headers["Authorization"].split(" ")[1]
            calls.append(key)
            if key == "A":
                raise httpx.ConnectError("connection refused")
            return _Resp(200, {"ok": True})

        balancer = SiliconFlowBalancer(["A", "B"], "https://example.com")
        with _patch_client_post(fake_post):
            assert balancer.post("/x", {}) == {"ok": True}
        assert calls == ["A", "B"]

    def test_all_keys_in_cooldown_raises(self):
        def fake_post(url, json=None, headers=None, timeout=None):
            return _Resp(429)

        balancer = SiliconFlowBalancer(["A", "B"], "https://example.com")
        with _patch_client_post(fake_post):
            with pytest.raises(RuntimeError, match="所有 SiliconFlow key 均不可用"):
                balancer.post("/x", {})
