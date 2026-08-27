import threading
import time

import httpx
import numpy as np

from utils.config import get_config
from utils.logger import get_logger

logger = get_logger("rag.siliconflow")

DEFAULT_BASE_URL = "https://api.siliconflow.cn/v1"
COOLDOWN_SECONDS = 60.0
REQUEST_TIMEOUT = 30.0

_client: httpx.Client | None = None
_client_lock = threading.Lock()


def _get_shared_client() -> httpx.Client:
    """进程级共享 httpx.Client：线程安全、复用连接池，避免每次请求重建 TCP/TLS 连接。"""
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = httpx.Client(timeout=REQUEST_TIMEOUT)
    return _client


class SiliconFlowBalancer:
    """多 key 负载均衡：优先分配给空闲时间最长的 key；单 key 报错/限流后自动切下一个。"""

    def __init__(self, api_keys: list[str], base_url: str, cooldown_seconds: float = COOLDOWN_SECONDS):
        self._keys = [k.strip() for k in api_keys if k and k.strip()]
        if not self._keys:
            raise RuntimeError("未配置 SILICONFLOW_API_KEYS")
        self._base_url = base_url.rstrip("/")
        self._cooldown = cooldown_seconds
        self._lock = threading.Lock()
        self._last_used = {k: 0.0 for k in self._keys}
        self._cooldown_until = {k: 0.0 for k in self._keys}

    def _pick(self) -> str | None:
        now = time.perf_counter()
        with self._lock:
            best = None
            for k in self._keys:
                if self._cooldown_until[k] > now:
                    continue
                if best is None or self._last_used[k] < self._last_used[best]:
                    best = k
            if best is not None:
                self._last_used[best] = now
            return best

    def _mark_cooldown(self, key: str):
        with self._lock:
            self._cooldown_until[key] = time.perf_counter() + self._cooldown
        logger.warning(f"SiliconFlow key {key[:8]}... 触发冷却 {self._cooldown:.0f}s，切换其他 key")

    def post(self, path: str, payload: dict) -> dict:
        errors: list[str] = []
        for _ in range(len(self._keys)):
            key = self._pick()
            if key is None:
                break
            try:
                resp = _get_shared_client().post(
                    f"{self._base_url}{path}",
                    json=payload,
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                )
            except httpx.HTTPError as e:
                self._mark_cooldown(key)
                errors.append(f"网络错误: {e}")
                continue
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code in (429, 500, 502, 503, 504):
                self._mark_cooldown(key)
                errors.append(f"HTTP {resp.status_code}")
                continue
            resp.raise_for_status()
        raise RuntimeError(f"所有 SiliconFlow key 均不可用: {'; '.join(errors)}")


class EmbeddingClient:
    """SentenceTransformer 的接口替身：encode(texts, normalize_embeddings=True) -> np.ndarray。"""

    def __init__(self, balancer: SiliconFlowBalancer, model: str, batch_size: int = 32):
        self._balancer = balancer
        self.model = model
        self.batch_size = batch_size

    def encode(self, texts, normalize_embeddings: bool = True, batch_size: int | None = None):
        if isinstance(texts, str):
            texts = [texts]
        bs = batch_size or self.batch_size
        vecs: list[list[float]] = []
        for i in range(0, len(texts), bs):
            batch = texts[i : i + bs]
            data = self._balancer.post("/embeddings", {"model": self.model, "input": batch})
            items = sorted(data.get("data", []), key=lambda x: x.get("index", 0))
            vecs.extend(item["embedding"] for item in items)
        arr = np.asarray(vecs, dtype="float32")
        if normalize_embeddings:
            norms = np.linalg.norm(arr, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            arr = arr / norms
        return arr


class RerankClient:
    """CrossEncoder 的接口替身：predict(pairs) -> np.ndarray（分数与输入顺序对齐）。"""

    def __init__(self, balancer: SiliconFlowBalancer, model: str):
        self._balancer = balancer
        self.model = model

    def predict(self, pairs):
        pairs = list(pairs)
        if not pairs:
            return np.array([], dtype="float32")
        query = pairs[0][0]
        documents = [p[1] for p in pairs]
        data = self._balancer.post(
            "/rerank",
            {"model": self.model, "query": query, "documents": documents, "top_n": len(documents)},
        )
        scores = [0.0] * len(documents)
        for r in data.get("results", []):
            idx = r.get("index")
            if isinstance(idx, int) and 0 <= idx < len(scores):
                scores[idx] = r.get("relevance_score", 0.0)
        return np.array(scores, dtype="float32")


_balancer_cache: dict = {}


def _parse_keys(raw: str) -> list[str]:
    return [k.strip() for k in (raw or "").split(",") if k.strip() and not k.strip().startswith("${")]


def _get_balancer() -> SiliconFlowBalancer:
    cfg = get_config()["models"]["embed"]
    base_url = cfg.get("api_base") or DEFAULT_BASE_URL
    keys = _parse_keys(cfg.get("api_keys", ""))
    cache_key = (base_url, tuple(keys))
    if cache_key not in _balancer_cache:
        if not keys:
            raise RuntimeError("未配置 SILICONFLOW_API_KEYS，请在 .env 中设置")
        _balancer_cache[cache_key] = SiliconFlowBalancer(keys, base_url)
    return _balancer_cache[cache_key]


def get_embedding_client() -> EmbeddingClient:
    cfg = get_config()["models"]
    return EmbeddingClient(_get_balancer(), cfg["embed"]["name"])


def get_rerank_client() -> RerankClient:
    cfg = get_config()["models"]
    return RerankClient(_get_balancer(), cfg["rerank"]["name"])
