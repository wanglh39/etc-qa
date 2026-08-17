import time
from unittest.mock import MagicMock, patch

import pytest

from alert.monitor import record_metric, get_metric_stats, get_all_metrics


class TestMonitor:
    def test_record_and_stats(self):
        record_metric("test_metric", 0.5, True)
        record_metric("test_metric", 1.0, True)
        record_metric("test_metric", 0.3, False)
        stats = get_metric_stats("test_metric", window=10)
        assert stats["count"] == 3
        assert stats["failure_count"] == 1
        assert 0.0 < stats["failure_rate"] < 1.0

    def test_empty_metric(self):
        stats = get_metric_stats("nonexistent", window=10)
        assert stats["count"] == 0
        assert stats["failure_rate"] == 0.0

    def test_all_success(self):
        for _ in range(5):
            record_metric("all_success", 0.1, True)
        stats = get_metric_stats("all_success", window=10)
        assert stats["failure_count"] == 0
        assert stats["failure_rate"] == 0.0

    def test_all_failure(self):
        for _ in range(3):
            record_metric("all_fail", 0.1, False)
        stats = get_metric_stats("all_fail", window=10)
        assert stats["failure_count"] == 3
        assert stats["failure_rate"] == 1.0

    def test_window_expiry(self):
        record_metric("expire_test", 0.1, True)
        time.sleep(0.1)
        stats = get_metric_stats("expire_test", window=0)
        assert stats["count"] == 0

    def test_get_all_metrics(self):
        record_metric("metric_a", 0.1, True)
        record_metric("metric_b", 0.2, False)
        all_metrics = get_all_metrics()
        assert "metric_a" in all_metrics or "metric_b" in all_metrics