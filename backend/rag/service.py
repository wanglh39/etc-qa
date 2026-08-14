import time

from agent.graph import preprocess_agent
from agent.state import AgentState
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
    _STANDARDIZE_CACHE_SIZE = 500

    def __init__(self, recall: RecallEngine, threshold: ThresholdJudge,
                 reranker: Reranker, mysql: MySQLClient):
        self.recall = recall
        self.threshold = threshold
        self.reranker = reranker
        self.mysql = mysql
        self._active_ids_cache = None
        self._active_ids_ts = 0
        self._active_ids_ttl = get_config().get("cache", {}).get("active_ids_ttl", 30)
        self._standardize_cache = {}

    def _get_active_ids(self) -> list[int]:
        now = time.time()
        if self._active_ids_cache is not None and (now - self._active_ids_ts) < self._active_ids_ttl:
            return self._active_ids_cache
        self._active_ids_cache = self.mysql.get_active_ids()
        self._active_ids_ts = now
        return self._active_ids_cache

    def invalidate_active_ids_cache(self):
        self._active_ids_cache = None
        self._active_ids_ts = 0

    def add_knowledge(self, req) -> int:
        qa_id = self.mysql.insert_qa(
            question=req.question,
            answer=req.answer,
            category_l1=req.category_l1 or "",
            category_l2=req.category_l2 or "",
            internal_process=req.internal_process or "",
            feedback_dept=req.feedback_dept or "",
        )
        vector = self.recall.encode_query(req.question)
        self.recall.milvus.insert(qa_id, vector, category_l1=req.category_l1 or "")
        all_qa = self.mysql.get_all_questions()
        self.recall.bm25.build(all_qa)
        self.invalidate_active_ids_cache()
        return qa_id

    def _standardize(self, raw_question: str) -> str:
        if raw_question in self._standardize_cache:
            return self._standardize_cache[raw_question]

        try:
            state = AgentState(raw_question=raw_question)
            result = preprocess_agent.invoke(state.model_dump())
            standardized = result.get("question", raw_question) or raw_question
        except Exception as e:
            logger.warning(f"LLM鏍囧噯鍖栧け璐ワ紝闄嶇骇鐢ㄥ師闂: {e}")
            standardized = raw_question

        if len(self._standardize_cache) >= self._STANDARDIZE_CACHE_SIZE:
            oldest_key = next(iter(self._standardize_cache))
            del self._standardize_cache[oldest_key]
        self._standardize_cache[raw_question] = standardized
        return standardized

    @traceable(name="rag_query", run_type="chain")
    def query(self, question: str, category_l1: str | None = None) -> QueryResponse:
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
                results.append(CandidateResult(
                    qa_id=qa_id,
                    question=r["question"],
                    answer=r["answer"],
                    category_l1=r.get("category_l1", ""),
                    category_l2=r.get("category_l2", ""),
                    internal_process=r.get("internal_process", ""),
                    feedback_dept=r.get("feedback_dept", ""),
                    score=round(score, 4),
                ))

        return QueryResponse(
            query=question,
            standardized_query=standardized,
            confidence=confidence,
            candidates=results,
            total_candidates=len(results),
        )