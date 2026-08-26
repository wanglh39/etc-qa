import time
from collections import defaultdict, deque
from threading import Lock

from utils.logger import get_logger

logger = get_logger("alert.monitor")

_window = 600
_records: dict[str, deque] = defaultdict(lambda: deque())
_lock = Lock()


def record_metric(name: str, latency: float = 0.0, success: bool = True):
    ts = time.time()
    with _lock:
        dq = _records[name]
        dq.append((ts, latency, success))
        cutoff = ts - _window
        while dq and dq[0][0] < cutoff:
            dq.popleft()


def _get_records(name: str, window: int) -> list[tuple]:
    cutoff = time.time() - window
    with _lock:
        return [(ts, lat, ok) for ts, lat, ok in _records[name] if ts >= cutoff]


def get_metric_stats(name: str, window: int = 300) -> dict:
    recs = _get_records(name, window)
    total = len(recs)
    if total == 0:
        return {"count": 0, "failure_count": 0, "failure_rate": 0.0, "p95_latency": 0.0, "avg_latency": 0.0}
    failures = sum(1 for _, _, ok in recs if not ok)
    latencies = sorted([lat for _, lat, _ in recs if lat > 0])
    p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0.0
    avg = sum(latencies) / len(latencies) if latencies else 0.0
    return {
        "count": total,
        "failure_count": failures,
        "failure_rate": failures / total,
        "p95_latency": p95,
        "avg_latency": avg,
    }


def get_all_metrics() -> dict[str, dict]:
    names = set()
    with _lock:
        for name in _records:
            names.add(name)
    return {name: get_metric_stats(name) for name in names}
