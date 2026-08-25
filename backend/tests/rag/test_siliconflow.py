from unittest.mock import patch

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
        with patch("rag.siliconflow.httpx.post", side_effect=fake_post):
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
        with patch("rag.siliconflow.httpx.post", side_effect=fake_post):
            result = balancer.post("/x", {})
        assert result == {"ok": True}
        assert calls == ["A", "B"]

    def test_all_keys_fail(self):
        def fake_post(url, json=None, headers=None, timeout=None):
            return _Resp(500)

        balancer = SiliconFlowBalancer(["A", "B"], "https://example.com")
        with patch("rag.siliconflow.httpx.post", side_effect=fake_post):
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
