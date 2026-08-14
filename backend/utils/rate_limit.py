import threading
import time


class RateLimiter:
    """内存固定窗口限流器（单 worker 部署适用；多 worker 需换 Redis）。"""

    def __init__(self):
        self._hits: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str, limit: int, window_seconds: float) -> bool:
        now = time.time()
        with self._lock:
            hits = [t for t in self._hits.get(key, []) if now - t < window_seconds]
            if len(hits) >= limit:
                self._hits[key] = hits
                return False
            hits.append(now)
            self._hits[key] = hits
            return True

    def reset(self, key: str | None = None):
        with self._lock:
            if key is None:
                self._hits.clear()
            else:
                self._hits.pop(key, None)


limiter = RateLimiter()
