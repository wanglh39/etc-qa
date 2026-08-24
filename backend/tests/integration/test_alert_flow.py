import time
from unittest.mock import MagicMock, patch

import pytest

from alert import notifier
from alert import monitor
from alert.checker import check_alerts
from alert.monitor import record_metric, get_metric_stats
from alert.notifier import trigger_alert
from alert.rules import ALERT_RULES


@pytest.fixture(autouse=True)
def _clear_caches():
    notifier._dedup_cache.clear()
    notifier._consecutive_failures.clear()
    monitor._records.clear()
    yield
    notifier._dedup_cache.clear()
    notifier._consecutive_failures.clear()
    monitor._records.clear()


def _mock_alert_config(in_app=True, webhook_enabled=True, webhook_url="http://wh.example.com/alert"):
    return {
        "alert": {
            "in_app": in_app,
            "dedup_window": 0,
            "webhook": {
                "enabled": webhook_enabled,
                "url": webhook_url,
                "format": "wechat",
            },
        }
    }


class TestAlertFlowRagFailure:
    @patch("alert.notifier.get_config")
    @patch("alert.notifier._send_webhook")
    @patch("alert.notifier._write_to_db")
    def test_rag_high_failure_triggers_db_and_webhook(self, mock_db, mock_wh, mock_cfg):
        mock_cfg.return_value = _mock_alert_config()
        for _ in range(20):
            record_metric("rag_query", 0.1, False)
        triggered = check_alerts()
        assert triggered > 0
        assert mock_db.call_count > 0
        assert mock_wh.call_count > 0

    @patch("alert.notifier.get_config")
    @patch("alert.notifier._send_webhook")
    @patch("alert.notifier._write_to_db")
    def test_rag_low_failure_no_trigger(self, mock_db, mock_wh, mock_cfg):
        mock_cfg.return_value = _mock_alert_config()
        for _ in range(20):
            record_metric("rag_query_low", 0.1, True)
        triggered = check_alerts()
        assert mock_db.call_count == 0
        assert mock_wh.call_count == 0


class TestAlertFlowLlmFailure:
    @patch("alert.notifier.get_config")
    @patch("alert.notifier._send_webhook")
    @patch("alert.notifier._write_to_db")
    def test_llm_failure_count_triggers(self, mock_db, mock_wh, mock_cfg):
        mock_cfg.return_value = _mock_alert_config()
        for _ in range(10):
            record_metric("llm_call", 0.5, False)
        triggered = check_alerts()
        assert triggered > 0
        assert mock_db.call_count > 0

    @patch("alert.notifier.get_config")
    @patch("alert.notifier._send_webhook")
    @patch("alert.notifier._write_to_db")
    def test_llm_below_threshold_no_trigger(self, mock_db, mock_wh, mock_cfg):
        mock_cfg.return_value = _mock_alert_config()
        for _ in range(3):
            record_metric("llm_call", 0.5, False)
        check_alerts()
        assert mock_db.call_count == 0


class TestAlertFlowSchedulerFailure:
    @patch("alert.notifier.get_config")
    @patch("alert.notifier._send_webhook")
    @patch("alert.notifier._write_to_db")
    def test_scheduler_consecutive_failure_triggers(self, mock_db, mock_wh, mock_cfg):
        mock_cfg.return_value = _mock_alert_config()
        notifier._consecutive_failures["sync_and_ingest"] = 3
        triggered = check_alerts()
        assert triggered > 0
        assert mock_db.call_count > 0

    @patch("alert.notifier.get_config")
    @patch("alert.notifier._send_webhook")
    @patch("alert.notifier._write_to_db")
    def test_scheduler_below_threshold_no_trigger(self, mock_db, mock_wh, mock_cfg):
        mock_cfg.return_value = _mock_alert_config()
        notifier._consecutive_failures["sync_and_ingest"] = 1
        check_alerts()
        assert mock_db.call_count == 0


class TestAlertFlowChannels:
    @patch("alert.notifier.get_config")
    @patch("alert.notifier._send_webhook")
    @patch("alert.notifier._write_to_db")
    def test_in_app_false_skips_db(self, mock_db, mock_wh, mock_cfg):
        mock_cfg.return_value = _mock_alert_config(in_app=False)
        for _ in range(20):
            record_metric("rag_query", 0.1, False)
        check_alerts()
        assert mock_db.call_count == 0
        assert mock_wh.call_count > 0

    @patch("alert.notifier.get_config")
    @patch("alert.notifier._send_webhook")
    @patch("alert.notifier._write_to_db")
    def test_webhook_disabled_skips_wh(self, mock_db, mock_wh, mock_cfg):
        mock_cfg.return_value = _mock_alert_config(webhook_enabled=False)
        for _ in range(20):
            record_metric("rag_query", 0.1, False)
        check_alerts()
        assert mock_db.call_count > 0
        assert mock_wh.call_count == 0

    @patch("alert.notifier.get_config")
    @patch("alert.notifier._send_webhook")
    @patch("alert.notifier._write_to_db")
    def test_both_disabled_no_calls(self, mock_db, mock_wh, mock_cfg):
        mock_cfg.return_value = _mock_alert_config(in_app=False, webhook_enabled=False)
        for _ in range(20):
            record_metric("rag_query", 0.1, False)
        triggered = check_alerts()
        assert triggered > 0
        assert mock_db.call_count == 0
        assert mock_wh.call_count == 0


class TestAlertFlowDedup:
    @patch("alert.notifier.get_config")
    @patch("alert.notifier._send_webhook")
    @patch("alert.notifier._write_to_db")
    def test_dedup_blocks_second_check(self, mock_db, mock_wh, mock_cfg):
        mock_cfg.return_value = _mock_alert_config()
        mock_cfg.return_value["alert"]["dedup_window"] = 300
        for _ in range(20):
            record_metric("rag_query", 0.1, False)
        check_alerts()
        first_count = mock_db.call_count
        check_alerts()
        assert mock_db.call_count == first_count

    @patch("alert.notifier.get_config")
    @patch("alert.notifier._send_webhook")
    @patch("alert.notifier._write_to_db")
    def test_no_dedup_allows_retrigger(self, mock_db, mock_wh, mock_cfg):
        mock_cfg.return_value = _mock_alert_config()
        mock_cfg.return_value["alert"]["dedup_window"] = 0
        for _ in range(20):
            record_metric("rag_query", 0.1, False)
        check_alerts()
        first_count = mock_db.call_count
        time.sleep(0.01)
        check_alerts()
        assert mock_db.call_count > first_count


class TestAlertFlowAllRules:
    @patch("alert.notifier.get_config")
    @patch("alert.notifier._send_webhook")
    @patch("alert.notifier._write_to_db")
    def test_all_6_rules_have_valid_fields(self, mock_db, mock_wh, mock_cfg):
        for rule in ALERT_RULES:
            assert rule.id
            assert rule.name
            assert rule.metric
            assert rule.check_type in ("failure_rate", "failure_count", "p95_latency", "avg_latency", "consecutive_failure")
            assert rule.window > 0
            assert rule.threshold >= 0
            assert rule.severity in ("P0", "P1", "P2")
            assert rule.description

    @patch("alert.notifier.get_config")
    @patch("alert.notifier._send_webhook")
    @patch("alert.notifier._write_to_db")
    def test_milvus_failure_rule_triggers(self, mock_db, mock_wh, mock_cfg):
        mock_cfg.return_value = _mock_alert_config()
        for _ in range(10):
            record_metric("milvus_search", 0.1, False)
        triggered = check_alerts()
        assert triggered > 0

    @patch("alert.notifier.get_config")
    @patch("alert.notifier._send_webhook")
    @patch("alert.notifier._write_to_db")
    def test_mysql_failure_rule_triggers(self, mock_db, mock_wh, mock_cfg):
        mock_cfg.return_value = _mock_alert_config()
        for _ in range(10):
            record_metric("mysql_query", 0.1, False)
        triggered = check_alerts()
        assert triggered > 0

    @patch("alert.notifier.get_config")
    @patch("alert.notifier._send_webhook")
    @patch("alert.notifier._write_to_db")
    def test_rag_p95_latency_rule_triggers(self, mock_db, mock_wh, mock_cfg):
        mock_cfg.return_value = _mock_alert_config()
        for _ in range(20):
            record_metric("rag_query", 5.0, True)
        triggered = check_alerts()
        assert triggered > 0