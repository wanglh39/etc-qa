import threading
import time

from cachetools import TTLCache

from agent.graph import preprocess_agent
from agent.state import AgentState
from alert.monitor import record_metric
from db.mysql_client import MySQLClient
from models.schemas import CandidateResult, QueryResponse
from rag.recall import RecallEngine
from rag.reranker import Reranker
from rag.threshold import ThresholdJudge
from utils.config import get_config
from utils.logger import get_logger

try:
    from langsmith import traceable
except ImportError:

    def traceable(name=None, run_type=None):
        def decorator(func):
            return func

        return decorator


logger = get_logger("rag.service")


class QAService:
    _STANDARDIZE_CACHE_SIZE = 2000
    _STANDARDIZE_TTL = 3600

    def __init__(self, recall: RecallEngine, threshold: ThresholdJudge, reranker: Reranker, mysql: MySQLClient):
        self.recall = recall
        self.threshold = threshold
        self.reranker = reranker
        self.mysql = mysql
        self._active_ids_cache = None
        self._active_ids_ts = 0
        self._active_ids_ttl = get_config().get("cache", {}).get("active_ids_ttl", 30)
        self._active_ids_lock = threading.Lock()
        self._standardize_cache = TTLCache(maxsize=self._STANDARDIZE_CACHE_SIZE, ttl=self._STANDARDIZE_TTL)
        self._standardize_lock = threading.Lock()

    def reload_config(self):
        self.recall.update_config()
        self.threshold.update_config()
        self.reranker.update_config()
        self._active_ids_cache = None

    def _get_active_ids(self) -> list[int]:
        now = time.time()
        with self._active_ids_lock:
            if self._active_ids_cache is not None and (now - self._active_ids_ts) < self._active_ids_ttl:
                return self._active_ids_cache
            self._active_ids_cache = self.mysql.get_active_ids()
            self._active_ids_ts = now
        return self._active_ids_cache

    def invalidate_active_ids_cache(self):
        with self._active_ids_lock:
            self._active_ids_cache = None
            self._active_ids_ts = 0

    @traceable(name="add_knowledge", run_type="chain")
    def add_knowledge(self, req) -> int:
        qa_id = self.mysql.insert_qa(
            question=req.question,
            answer=req.answer,
            category_l1=req.category_l1 or "",
            category_l2=req.category_l2 or "",
            internal_process=req.internal_process or "",
            feedback_dept=req.feedback_dept or "",
        )
        try:
            vector = self.recall.encode_query(req.question)
            self._insert_milvus_with_retry(qa_id, vector, req.category_l1 or "")
        except Exception as e:
            logger.error(f"向量库写入失败，回滚MySQL qa_id={qa_id}: {e}")
            try:
                self.mysql.delete_qa(qa_id)
            except Exception as del_e:
                logger.error(f"回滚MySQL失败! qa_id={qa_id} 残留数据需人工清理: {del_e}")
            raise
        try:
            all_qa = self.mysql.get_all_questions()
            self.recall.bm25.build(all_qa)
        except Exception as e:
            logger.warning(f"BM25索引重建失败(不影响已入库数据): {e}")
        self.invalidate_active_ids_cache()
        return qa_id

    @traceable(name="activate_qa", run_type="chain")
    def activate_qa(self, qa_id: int) -> None:
        detail = self.mysql.get_qa_detail(qa_id) or {}
        question = detail.get("question", "")
        if not question:
            logger.warning(f"审核激活 qa_id={qa_id} 但无 question，跳过向量写入")
            return
        vector = self.recall.encode_query(question)
        self._insert_milvus_with_retry(qa_id, vector, detail.get("category_l1", ""))
        try:
            all_qa = self.mysql.get_all_questions()
            self.recall.bm25.build(all_qa)
        except Exception as e:
            logger.warning(f"BM25索引重建失败(不影响已入库数据): {e}")
        self.invalidate_active_ids_cache()

    def _insert_milvus_with_retry(self, qa_id: int, vector: list[float], category_l1: str, max_retries: int = 2):
        for attempt in range(max_retries + 1):
            try:
                self.recall.milvus.insert(qa_id, vector, category_l1=category_l1)
                return
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"Milvus写入失败(第{attempt + 1}次)qa_id={qa_id}，重试: {e}")
                    time.sleep(0.5 * (attempt + 1))
                    continue
                raise

    def _standardize(self, raw_question: str) -> str:
        with self._standardize_lock:
            if raw_question in self._standardize_cache:
                return self._standardize_cache[raw_question]

        llm_standardize_enabled = get_config().get("llm", {}).get("standardize_enabled", True)
        if llm_standardize_enabled:
            try:
                state = AgentState(raw_question=raw_question)
                result = preprocess_agent.invoke(state.model_dump())
                standardized = result.get("question", raw_question) or raw_question
            except Exception as e:
                logger.warning(f"LLM标准化失败，降级用原问题: {e}")
                standardized = raw_question
        else:
            from agent.processors.standardize_query import _rule_based_standardize

            standardized = _rule_based_standardize(raw_question)
            logger.info(f"规则标准化(跳过LLM): '{raw_question}' -> '{standardized}'")

        with self._standardize_lock:
            self._standardize_cache[raw_question] = standardized
        return standardized

    @traceable(name="rag_query", run_type="chain")
    def query(self, question: str, category_l1: str | None = None) -> QueryResponse:
        start = time.time()
        try:
            standardized = self._standardize(question)
            logger.info(f"query: '{question}' -> standardized: '{standardized}'")

            active_qa_ids = self._get_active_ids()

            query_vector = self.recall.encode_query(standardized)
            candidates = self.recall.recall(standardized, query_vector, active_qa_ids=active_qa_ids)

            candidates = self.reranker.rerank(standardized, candidates)

            confidence, filtered = self.threshold.filter_candidates(candidates)
            logger.info(f"confidence={confidence}, candidates={len(filtered)}")

            qa_ids = [qa_id for qa_id, score in filtered]
            qa_records = self.mysql.get_by_ids(qa_ids)
            qa_map = {r["id"]: r for r in qa_records}

            results = []
            for qa_id, score in filtered:
                if qa_id in qa_map:
                    r = qa_map[qa_id]
                    results.append(
                        CandidateResult(
                            qa_id=qa_id,
                            question=r["question"],
                            answer=r["answer"],
                            category_l1=r.get("category_l1", ""),
                            category_l2=r.get("category_l2", ""),
                            internal_process=r.get("internal_process", ""),
                            feedback_dept=r.get("feedback_dept", ""),
                            score=round(score, 4),
                        )
                    )

            resp = QueryResponse(
                query=question,
                standardized_query=standardized,
                confidence=confidence,
                candidates=results,
                total_candidates=len(results),
            )
            record_metric("rag_query", time.time() - start, True)
            return resp
        except Exception as e:
            record_metric("rag_query", time.time() - start, False)
            raise
