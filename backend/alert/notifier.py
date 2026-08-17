import json
import time
from datetime import datetime

import requests

from db.mysql_client import MySQLClient
from utils.config import get_config
from utils.logger import get_logger

logger = get_logger("alert.notifier")

_dedup_cache: dict[str, float] = {}
_consecutive_failures: dict[str, int] = {}


def trigger_alert(rule_id: str, severity: str, description: str, current_value: float, threshold: float):
    cfg = get_config().get("alert", {})
    dedup_window = cfg.get("dedup_window", 300)

    now = time.time()
    if rule_id in _dedup_cache and now - _dedup_cache[rule_id] < dedup_window:
        return
    _dedup_cache[rule_id] = now

    message = f"[{severity}] {description} (当前值={current_value:.2f}, 阈值={threshold:.2f})"
    logger.warning(f"告警触发: {message}")

    if cfg.get("in_app", True):
        _write_to_db(rule_id, severity, message, current_value, threshold)

    webhook_cfg = cfg.get("webhook", {})
    if webhook_cfg.get("enabled", False) and webhook_cfg.get("url"):
        _send_webhook(webhook_cfg, severity, message)


def record_task_result(task_name: str, success: bool):
    if success:
        _consecutive_failures[task_name] = 0
    else:
        _consecutive_failures[task_name] = _consecutive_failures.get(task_name, 0) + 1
    return _consecutive_failures[task_name]


def get_consecutive_failures(task_name: str) -> int:
    return _consecutive_failures.get(task_name, 0)


def _write_to_db(rule_id: str, severity: str, message: str, current_value: float, threshold: float):
    try:
        mysql = MySQLClient()
        mysql.insert_alert_event(rule_id, severity, message, current_value, threshold)
    except Exception as e:
        logger.error(f"写入告警事件失败: {e}")


def _send_webhook(webhook_cfg: dict, severity: str, message: str):
    url = webhook_cfg["url"]
    fmt = webhook_cfg.get("format", "wechat")
    try:
        if fmt == "wechat":
            payload = {"msgtype": "markdown", "markdown": {"content": f"### 告警通知\n> {message}"}}
        elif fmt == "dingtalk":
            payload = {"msgtype": "markdown", "markdown": {"title": "告警通知", "text": f"### 告警通知\n{message}"}}
        elif fmt == "feishu":
            payload = {"msg_type": "text", "content": {"text": message}}
        else:
            payload = {"text": message}

        requests.post(url, json=payload, timeout=5)
        logger.info(f"Webhook通知已发送: {severity}")
    except Exception as e:
        logger.error(f"Webhook发送失败: {e}")