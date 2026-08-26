import threading

import jieba
from rank_bm25 import BM25Okapi


class BM25Index:
    def __init__(self):
        self._bm25 = None
        self._qa_ids = []
        self._tokenized_corpus = []
        self._lock = threading.RLock()

    def build(self, qa_pairs: list[dict]):
        with self._lock:
            self._qa_ids = [qa["id"] for qa in qa_pairs]
            self._tokenized_corpus = [list(jieba.cut(qa["question"])) for qa in qa_pairs]
            self._bm25 = BM25Okapi(self._tokenized_corpus)

    def search(self, query: str, top_k: int = 10, active_qa_ids: list = None) -> list[tuple]:
        with self._lock:
            if self._bm25 is None:
                return []
            query_tokens = list(jieba.cut(query))
            scores = self._bm25.get_scores(query_tokens)
            ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
            results = []
            for i in ranked:
                if len(results) >= top_k:
                    break
                if active_qa_ids is not None and self._qa_ids[i] not in active_qa_ids:
                    continue
                results.append((self._qa_ids[i], float(scores[i])))
            return results

    def add_document(self, qa_id: int, question: str):
        with self._lock:
            self._qa_ids.append(qa_id)
            tokenized = list(jieba.cut(question))
            self._tokenized_corpus.append(tokenized)
            self._bm25 = BM25Okapi(self._tokenized_corpus)
