from unittest.mock import MagicMock, patch

import pytest

from alert.checker import _evaluate_rule, check_alerts
from alert.monitor import record_metric
from alert.rules import ALERT_RULES, AlertRule


class TestAlertRules:
    def test_rules_defined(self):
        assert len(ALERT_RULES) > 0
        for rule in ALERT_RULES:
            assert rule.id
            assert rule.metric
            assert rule.severity in ("P0", "P1", "P2")

    def test_rag_failure_rate_rule(self):
        rule = next(r for r in ALERT_RULES if r.id == "rag_failure_rate")
        assert rule.check_type == "failure_rate"
        assert rule.threshold == 0.10

    def test_llm_failure_count_rule(self):
        rule = next(r for r in ALERT_RULES if r.id == "llm_failure_count")
        assert rule.check_type == "failure_count"
        assert rule.threshold == 5


class TestEvaluateRule:
    def test_failure_rate(self):
        for _ in range(10):
            record_metric("test_eval_rate", 0.1, True)
        for _ in range(5):
            record_metric("test_eval_rate", 0.1, False)
        rule = AlertRule("test", "test", "test_eval_rate", "failure_rate", 10, 0.10, "P0", "test")
        value = _evaluate_rule(rule)
        assert value is not None
        assert value > 0

    def test_no_data_returns_none(self):
        rule = AlertRule("test", "test", "empty_metric_xyz", "failure_rate", 10, 0.10, "P0", "test")
        value = _evaluate_rule(rule)
        assert value is None


class TestCheckAlerts:
    @patch("alert.checker.trigger_alert")
    def test_no_metrics_no_alerts(self, mock_trigger):
        result = check_alerts()
        assert result == 0
        mock_trigger.assert_not_called()

    @patch("alert.checker.trigger_alert")
    def test_high_failure_rate_triggers(self, mock_trigger):
        for _ in range(20):
            record_metric("rag_query", 0.1, False)
        check_alerts()
        assert mock_trigger.call_count > 0