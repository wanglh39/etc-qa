import time
from unittest.mock import MagicMock, patch

import pytest

from alert import notifier
from alert.notifier import (
    get_consecutive_failures,
    record_task_result,
    trigger_alert,
    _send_webhook,
    _write_to_db,
)


@pytest.fixture(autouse=True)
def _clear_caches():
    notifier._dedup_cache.clear()
    notifier._consecutive_failures.clear()
    yield
    notifier._dedup_cache.clear()
    notifier._consecutive_failures.clear()


def _mock_config(in_app=True, webhook_enabled=False, webhook_url="", fmt="wechat", dedup_window=300):
    cfg = {
        "alert": {
            "in_app": in_app,
            "dedup_window": dedup_window,
            "webhook": {
                "enabled": webhook_enabled,
                "url": webhook_url,
                "format": fmt,
            },
        }
    }
    return cfg


class TestTriggerAlertDedup:
    @patch("alert.notifier.get_config")
    @patch("alert.notifier._write_to_db")
    @patch("alert.notifier._send_webhook")
    def test_first_trigger_passes(self, mock_wh, mock_db, mock_cfg):
        mock_cfg.return_value = _mock_config()
        trigger_alert("rule_1", "P0", "test", 0.5, 0.1)
        mock_db.assert_called_once()

    @patch("alert.notifier.get_config")
    @patch("alert.notifier._write_to_db")
    @patch("alert.notifier._send_webhook")
    def test_dedup_blocks_second(self, mock_wh, mock_db, mock_cfg):
        mock_cfg.return_value = _mock_config(dedup_window=300)
        trigger_alert("rule_1", "P0", "test", 0.5, 0.1)
        trigger_alert("rule_1", "P0", "test", 0.5, 0.1)
        assert mock_db.call_count == 1

    @patch("alert.notifier.get_config")
    @patch("alert.notifier._write_to_db")
    @patch("alert.notifier._send_webhook")
    def test_different_rules_not_deduped(self, mock_wh, mock_db, mock_cfg):
        mock_cfg.return_value = _mock_config()
        trigger_alert("rule_1", "P0", "test", 0.5, 0.1)
        trigger_alert("rule_2", "P0", "test", 0.5, 0.1)
        assert mock_db.call_count == 2

    @patch("alert.notifier.get_config")
    @patch("alert.notifier._write_to_db")
    @patch("alert.notifier._send_webhook")
    def test_dedup_expired_allows_retry(self, mock_wh, mock_db, mock_cfg):
        mock_cfg.return_value = _mock_config(dedup_window=0)
        trigger_alert("rule_1", "P0", "test", 0.5, 0.1)
        time.sleep(0.01)
        trigger_alert("rule_1", "P0", "test", 0.5, 0.1)
        assert mock_db.call_count == 2


class TestTriggerAlertChannels:
    @patch("alert.notifier.get_config")
    @patch("alert.notifier._write_to_db")
    @patch("alert.notifier._send_webhook")
    def test_in_app_true_calls_db(self, mock_wh, mock_db, mock_cfg):
        mock_cfg.return_value = _mock_config(in_app=True)
        trigger_alert("rule_1", "P0", "test", 0.5, 0.1)
        mock_db.assert_called_once()

    @patch("alert.notifier.get_config")
    @patch("alert.notifier._write_to_db")
    @patch("alert.notifier._send_webhook")
    def test_in_app_false_skips_db(self, mock_wh, mock_db, mock_cfg):
        mock_cfg.return_value = _mock_config(in_app=False)
        trigger_alert("rule_1", "P0", "test", 0.5, 0.1)
        mock_db.assert_not_called()

    @patch("alert.notifier.get_config")
    @patch("alert.notifier._write_to_db")
    @patch("alert.notifier._send_webhook")
    def test_webhook_enabled_calls_send(self, mock_wh, mock_db, mock_cfg):
        mock_cfg.return_value = _mock_config(webhook_enabled=True, webhook_url="http://example.com/wh")
        trigger_alert("rule_1", "P0", "test", 0.5, 0.1)
        mock_wh.assert_called_once()

    @patch("alert.notifier.get_config")
    @patch("alert.notifier._write_to_db")
    @patch("alert.notifier._send_webhook")
    def test_webhook_disabled_skips_send(self, mock_wh, mock_db, mock_cfg):
        mock_cfg.return_value = _mock_config(webhook_enabled=False)
        trigger_alert("rule_1", "P0", "test", 0.5, 0.1)
        mock_wh.assert_not_called()

    @patch("alert.notifier.get_config")
    @patch("alert.notifier._write_to_db")
    @patch("alert.notifier._send_webhook")
    def test_webhook_enabled_but_no_url_skips(self, mock_wh, mock_db, mock_cfg):
        mock_cfg.return_value = _mock_config(webhook_enabled=True, webhook_url="")
        trigger_alert("rule_1", "P0", "test", 0.5, 0.1)
        mock_wh.assert_not_called()

    @patch("alert.notifier.get_config")
    @patch("alert.notifier._write_to_db")
    @patch("alert.notifier._send_webhook")
    def test_db_call_args(self, mock_wh, mock_db, mock_cfg):
        mock_cfg.return_value = _mock_config()
        trigger_alert("rule_1", "P1", "desc here", 0.55, 0.10)
        args = mock_db.call_args[0]
        assert args[0] == "rule_1"
        assert args[1] == "P1"
        assert "desc here" in args[2]
        assert args[3] == 0.55
        assert args[4] == 0.10


class TestSendWebhook:
    @patch("alert.notifier.requests.post")
    def test_wechat_format(self, mock_post):
        cfg = {"url": "http://wh", "format": "wechat"}
        _send_webhook(cfg, "P0", "msg")
        mock_post.assert_called_once()
        payload = mock_post.call_args[1]["json"]
        assert payload["msgtype"] == "markdown"
        assert "msg" in payload["markdown"]["content"]

    @patch("alert.notifier.requests.post")
    def test_dingtalk_format(self, mock_post):
        cfg = {"url": "http://wh", "format": "dingtalk"}
        _send_webhook(cfg, "P0", "msg")
        payload = mock_post.call_args[1]["json"]
        assert payload["msgtype"] == "markdown"
        assert "title" in payload["markdown"]
        assert "text" in payload["markdown"]

    @patch("alert.notifier.requests.post")
    def test_feishu_format(self, mock_post):
        cfg = {"url": "http://wh", "format": "feishu"}
        _send_webhook(cfg, "P0", "msg")
        payload = mock_post.call_args[1]["json"]
        assert payload["msg_type"] == "text"
        assert payload["content"]["text"] == "msg"

    @patch("alert.notifier.requests.post")
    def test_default_format(self, mock_post):
        cfg = {"url": "http://wh", "format": "unknown"}
        _send_webhook(cfg, "P0", "msg")
        payload = mock_post.call_args[1]["json"]
        assert payload == {"text": "msg"}

    @patch("alert.notifier.requests.post")
    def test_post_called_with_timeout(self, mock_post):
        cfg = {"url": "http://wh", "format": "wechat"}
        _send_webhook(cfg, "P0", "msg")
        assert mock_post.call_args[1]["timeout"] == 5

    @patch("alert.notifier.requests.post", side_effect=Exception("network error"))
    def test_exception_does_not_raise(self, mock_post):
        cfg = {"url": "http://wh", "format": "wechat"}
        _send_webhook(cfg, "P0", "msg")


class TestWriteToDb:
    @patch("alert.notifier.MySQLClient")
    def test_insert_called(self, mock_client_cls):
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance
        _write_to_db("rule_1", "P0", "msg", 0.5, 0.1)
        mock_instance.insert_alert_event.assert_called_once_with("rule_1", "P0", "msg", 0.5, 0.1)

    @patch("alert.notifier.MySQLClient")
    def test_exception_does_not_raise(self, mock_client_cls):
        mock_instance = MagicMock()
        mock_instance.insert_alert_event.side_effect = Exception("db down")
        mock_client_cls.return_value = mock_instance
        _write_to_db("rule_1", "P0", "msg", 0.5, 0.1)


class TestRecordTaskResult:
    def test_success_resets_to_zero(self):
        record_task_result("task_a", False)
        record_task_result("task_a", False)
        result = record_task_result("task_a", True)
        assert result == 0

    def test_failure_increments(self):
        assert record_task_result("task_b", False) == 1
        assert record_task_result("task_b", False) == 2
        assert record_task_result("task_b", False) == 3

    def test_different_tasks_independent(self):
        record_task_result("task_x", False)
        record_task_result("task_y", False)
        record_task_result("task_y", False)
        assert get_consecutive_failures("task_x") == 1
        assert get_consecutive_failures("task_y") == 2

    def test_get_failures_unknown_task(self):
        assert get_consecutive_failures("nonexistent") == 0

    def test_mixed_success_failure_sequence(self):
        assert record_task_result("task_c", False) == 1
        assert record_task_result("task_c", False) == 2
        assert record_task_result("task_c", True) == 0
        assert record_task_result("task_c", False) == 1
        assert record_task_result("task_c", False) == 2