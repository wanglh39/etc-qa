from alert.monitor import get_metric_stats
from alert.notifier import get_consecutive_failures, trigger_alert
from alert.rules import ALERT_RULES
from utils.logger import get_logger

logger = get_logger("alert.checker")


def check_alerts():
    triggered = 0
    for rule in ALERT_RULES:
        try:
            value = _evaluate_rule(rule)
            if value is not None and value > rule.threshold:
                trigger_alert(rule.id, rule.severity, rule.description, value, rule.threshold)
                triggered += 1
        except Exception as e:
            logger.error(f"规则检查异常 {rule.id}: {e}")
    if triggered > 0:
        logger.info(f"告警检查完成, 触发{triggered}条告警")
    return triggered


def _evaluate_rule(rule) -> float | None:
    if rule.check_type == "consecutive_failure":
        return float(get_consecutive_failures("sync_and_ingest"))

    stats = get_metric_stats(rule.metric, rule.window)
    if stats["count"] == 0:
        return None

    if rule.check_type == "failure_rate":
        return stats["failure_rate"]
    elif rule.check_type == "failure_count":
        return float(stats["failure_count"])
    elif rule.check_type == "p95_latency":
        return stats["p95_latency"]
    elif rule.check_type == "avg_latency":
        return stats["avg_latency"]
    return None
