import atexit
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout

from db.milvus_client import MilvusQA
from rag.bm25_index import BM25Index
from utils.config import get_config
from utils.logger import get_logger

logger = get_logger("rag.recall")

try:
    from langsmith import traceable
except ImportError:
    def traceable(name=None, run_type=None):
        def decorator(func):
            return func
        return decorator


class RecallEngine:
    _executor = ThreadPoolExecutor(max_workers=2)
    atexit.register(_executor.shutdown, wait=False)

    _RECALL_TIMEOUT = 30

    def __init__(self, embed_model, milvus: MilvusQA, bm25: BM25Index):
        self.embed_model = embed_model
        self.milvus = milvus
        self.bm25 = bm25
        cfg = get_config()["recall"]
        self.vector_top_k = cfg["vector_top_k"]
        self.bm25_top_k = cfg["bm25_top_k"]
        self.merge_method = cfg["merge_method"]
        self.rrf_k = cfg["rrf_k"]
        self.vector_weight = cfg.get("vector_weight", 0.7)
        self.bm25_weight = cfg.get("bm25_weight", 0.3)
        self.query_prefix = get_config()["models"]["query_prefix"]

    def update_config(self):
        cfg = get_config()["recall"]
        self.vector_top_k = cfg["vector_top_k"]
        self.bm25_top_k = cfg["bm25_top_k"]
        self.merge_method = cfg["merge_method"]
        self.rrf_k = cfg["rrf_k"]
        self.vector_weight = cfg.get("vector_weight", 0.7)
        self.bm25_weight = cfg.get("bm25_weight", 0.3)
        self.query_prefix = get_config()["models"]["query_prefix"]
        logger.info(f"RecallEngine配置已热更新: top_k=({self.vector_top_k},{self.bm25_top_k}) weight=({self.vector_weight},{self.bm25_weight})")

    def encode_query(self, query_text: str):
        return self.embed_model.encode(
            [self.query_prefix + query_text], normalize_embeddings=True
        ).tolist()[0]

    @traceable(name="vector_recall", run_type="retriever")
    def vector_recall(self, query_vector, top_k=None, use_hyde=True, active_qa_ids=None):
        k = top_k or self.vector_top_k
        return self.milvus.search(query_vector, top_k=k, use_hyde=use_hyde, active_qa_ids=active_qa_ids)

    @traceable(name="bm25_recall", run_type="retriever")
    def bm25_recall(self, query_text: str, top_k=None, active_qa_ids=None):
        k = top_k or self.bm25_top_k
        return self.bm25.search(query_text, top_k=k, active_qa_ids=active_qa_ids)

    def rrf_merge(self, vec_results, bm25_results):
        scores = {}
        for rank, (qid, _) in enumerate(vec_results):
            scores[qid] = scores.get(qid, 0) + 1.0 / (self.rrf_k + rank + 1)
        for rank, (qid, _) in enumerate(bm25_results):
            scores[qid] = scores.get(qid, 0) + 1.0 / (self.rrf_k + rank + 1)
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked

    def weighted_rrf_merge(self, vec_results, bm25_results):
        scores = {}
        for rank, (qid, _) in enumerate(vec_results):
            scores[qid] = scores.get(qid, 0) + self.vector_weight / (self.rrf_k + rank + 1)
        for rank, (qid, _) in enumerate(bm25_results):
            scores[qid] = scores.get(qid, 0) + self.bm25_weight / (self.rrf_k + rank + 1)
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked

    @traceable(name="recall", run_type="retriever")
    def recall(self, query_text: str, query_vector=None, use_hyde=True, active_qa_ids=None):
        if query_vector is None:
            query_vector = self.encode_query(query_text)

        vec_future = self._executor.submit(
            self.vector_recall, query_vector, use_hyde=use_hyde, active_qa_ids=active_qa_ids
        )
        bm25_future = self._executor.submit(
            self.bm25_recall, query_text, active_qa_ids=active_qa_ids
        )
        try:
            vec_results = vec_future.result(timeout=self._RECALL_TIMEOUT)
        except FutureTimeout:
            logger.warning(f"向量召回超时({self._RECALL_TIMEOUT}s)，降级返回空 query='{query_text[:30]}'")
            vec_results = []
        try:
            bm25_results = bm25_future.result(timeout=self._RECALL_TIMEOUT)
        except FutureTimeout:
            logger.warning(f"BM25召回超时({self._RECALL_TIMEOUT}s)，降级返回空 query='{query_text[:30]}'")
            bm25_results = []
        logger.info(f"并行召回完成: vector={len(vec_results)}条 bm25={len(bm25_results)}条 query='{query_text[:30]}'")

        if self.merge_method == "weighted_rrf":
            return self.weighted_rrf_merge(vec_results, bm25_results)
        else:
            return self.rrf_merge(vec_results, bm25_results)
