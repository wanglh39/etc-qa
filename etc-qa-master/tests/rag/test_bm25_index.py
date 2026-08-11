from rag.bm25_index import BM25Index


class TestBM25Index:
    def test_search_returns_empty_when_not_built(self):
        bm25 = BM25Index()
        result = bm25.search("ETC扣费异常")
        assert result == []

    def test_build_and_search(self):
        bm25 = BM25Index()
        qa_pairs = [
            {"id": 1, "question": "ETC扣费异常如何处理"},
            {"id": 2, "question": "ETC设备不亮怎么处理"},
            {"id": 3, "question": "如何办理ETC新办"},
        ]
        bm25.build(qa_pairs)
        result = bm25.search("ETC扣费异常", top_k=2)
        assert len(result) <= 2
        assert all(isinstance(r, tuple) and len(r) == 2 for r in result)

    def test_search_filters_by_active_qa_ids(self):
        bm25 = BM25Index()
        qa_pairs = [
            {"id": 1, "question": "ETC扣费异常如何处理"},
            {"id": 2, "question": "ETC设备不亮怎么处理"},
            {"id": 3, "question": "如何办理ETC新办"},
        ]
        bm25.build(qa_pairs)
        result = bm25.search("ET8C扣费异常", top_k=10, active_qa_ids=[1, 3])
        for qa_id, score in result:
            assert qa_id in [1, 3]

    def test_add_document(self):
        bm25 = BM25Index()
        bm25.build([{"id": 1, "question": "ETC扣费异常"}, {"id": 2, "question": "如何办理ETC"}])
        result = bm25.search("办理ETC", top_k=2)
        ids = [qid for qid, _ in result]
        assert 2 in ids
