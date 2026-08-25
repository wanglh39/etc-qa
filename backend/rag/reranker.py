from utils.config import get_config

try:
    from langsmith import traceable
except ImportError:
    def traceable(name=None, run_type=None):
        def decorator(func):
            return func
        return decorator


class Reranker:
    def __init__(self, model=None, mysql_client=None):
        self.model = model
        self.mysql_client = mysql_client
        cfg = get_config()["rerank"]
        self.enabled = cfg["enabled"]
        self.top_k = cfg["top_k"]

    def update_config(self):
        cfg = get_config()["rerank"]
        self.enabled = cfg["enabled"]
        self.top_k = cfg["top_k"]

    @traceable(name="rerank", run_type="retriever")
    def rerank(self, query_text: str, candidates: list[tuple]) -> list[tuple]:
        if not self.enabled or not self.model or not candidates:
            return candidates

        candidate_ids = [qa_id for qa_id, _ in candidates]

        if self.mysql_client:
            qa_records = self.mysql_client.get_by_ids(candidate_ids)
            qa_map = {r["id"]: r for r in qa_records}
        else:
            qa_map = {}

        candidate_questions = []
        valid_ids = []
        for qa_id in candidate_ids:
            if qa_id in qa_map:
                candidate_questions.append(qa_map[qa_id]["question"])
                valid_ids.append(qa_id)

        if not candidate_questions:
            return candidates

        pairs = [[query_text, q] for q in candidate_questions]
        scores = self.model.predict(pairs)

        ranked = sorted(zip(valid_ids, scores), key=lambda x: x[1], reverse=True)
        return ranked[:self.top_k]
