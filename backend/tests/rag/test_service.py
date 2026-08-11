from unittest.mock import MagicMock, patch

from rag.service import QAService


def _make_service(**overrides):
    mock_recall = MagicMock()
    mock_threshold = MagicMock()
    mock_reranker = MagicMock()
    mock_mysql = MagicMock()
    mock_mysql.get_active_ids.return_value = [1, 2]
    svc = QAService(mock_recall, mock_threshold, mock_reranker, mock_mysql)
    for k, v in overrides.items():
        setattr(svc, k, v)
    return svc, mock_recall, mock_threshold, mock_reranker, mock_mysql


class TestQAServiceQuery:
    @patch("rag.service.preprocess_agent")
    def test_query_none_confidence(self, mock_agent):
        mock_agent.invoke.return_value = {"question": "ETC扣费异常"}
        svc, mock_recall, mock_threshold, mock_reranker, mock_mysql = _make_service()
        mock_recall.encode_query.return_value = [0.1] * 1024
        mock_recall.recall.return_value = []
        mock_reranker.rerank.return_value = []
        mock_threshold.filter_candidates.return_value = ("none", [])

        result = svc.query("ETC扣费异常")
        assert result.confidence == "none"
        assert result.candidates == []

    @patch("rag.service.preprocess_agent")
    def test_query_high_confidence_with_candidates(self, mock_agent):
        mock_agent.invoke.return_value = {"question": "ETC扣费异常"}
        svc, mock_recall, mock_threshold, mock_reranker, mock_mysql = _make_service()
        mock_recall.encode_query.return_value = [0.1] * 1024
        mock_recall.recall.return_value = [(1, 0.9), (2, 0.7)]
        mock_reranker.rerank.return_value = [(1, 0.95), (2, 0.6)]
        mock_threshold.filter_candidates.return_value = ("high", [(1, 0.95), (2, 0.6)])
        mock_mysql.get_by_ids.return_value = [
            {"id": 1, "question": "ETC扣费异常", "answer": "核实退款", "category_l1": "售后", "category_l2": "扣费", "internal_process": "", "feedback_dept": ""},
            {"id": 2, "question": "ETC注销", "answer": "联系客服", "category_l1": "售前", "category_l2": "注销", "internal_process": "", "feedback_dept": ""},
        ]

        result = svc.query("ETC扣费异常")
        assert result.confidence == "high"
        assert len(result.candidates) == 2
        assert result.candidates[0].qa_id == 1
        assert result.candidates[0].score == 0.95
        assert result.total_candidates == 2

    @patch("rag.service.preprocess_agent")
    def test_query_skips_missing_qa_id(self, mock_agent):
        mock_agent.invoke.return_value = {"question": "test"}
        svc, mock_recall, mock_threshold, mock_reranker, mock_mysql = _make_service()
        mock_recall.encode_query.return_value = [0.1] * 1024
        mock_recall.recall.return_value = [(1, 0.9)]
        mock_reranker.rerank.return_value = [(1, 0.9)]
        mock_threshold.filter_candidates.return_value = ("high", [(1, 0.9)])
        mock_mysql.get_by_ids.return_value = []

        result = svc.query("test")
        assert result.candidates == []

    @patch("rag.service.preprocess_agent")
    def test_query_passes_category_l1_to_recall(self, mock_agent):
        mock_agent.invoke.return_value = {"question": "test"}
        svc, mock_recall, mock_threshold, mock_reranker, mock_mysql = _make_service()
        mock_recall.encode_query.return_value = [0.1] * 1024
        mock_recall.recall.return_value = []
        mock_reranker.rerank.return_value = []
        mock_threshold.filter_candidates.return_value = ("none", [])

        svc.query("test", category_l1="售后业务")
        mock_recall.recall.assert_called_once()

    @patch("rag.service.preprocess_agent")
    def test_query_standardize_fallback(self, mock_agent):
        mock_agent.invoke.return_value = {"question": ""}
        svc, mock_recall, mock_threshold, mock_reranker, mock_mysql = _make_service()
        mock_recall.encode_query.return_value = [0.1] * 1024
        mock_recall.recall.return_value = []
        mock_reranker.rerank.return_value = []
        mock_threshold.filter_candidates.return_value = ("none", [])

        result = svc.query("原始问题")
        assert result.standardized_query == "原始问题"


class TestQAServiceActiveIdsCache:
    def test_cache_hit(self):
        svc, _, _, _, mock_mysql = _make_service()
        svc._active_ids_cache = [1, 2, 3]
        svc._active_ids_ts = 9999999999
        svc._active_ids_ttl = 9999

        ids = svc._get_active_ids()
        assert ids == [1, 2, 3]
        mock_mysql.get_active_ids.assert_not_called()

    def test_cache_miss(self):
        svc, _, _, _, mock_mysql = _make_service()
        svc._active_ids_cache = None
        svc._active_ids_ts = 0

        mock_mysql.get_active_ids.return_value = [4, 5]
        ids = svc._get_active_ids()
        assert ids == [4, 5]
        mock_mysql.get_active_ids.assert_called_once()

    def test_cache_expired(self):
        svc, _, _, _, mock_mysql = _make_service()
        svc._active_ids_cache = [1]
        svc._active_ids_ts = 0
        svc._active_ids_ttl = 30

        mock_mysql.get_active_ids.return_value = [2, 3]
        ids = svc._get_active_ids()
        assert ids == [2, 3]

    def test_invalidate_cache(self):
        svc = _make_service()[0]
        svc._active_ids_cache = [1, 2, 3]
        svc._active_ids_ts = 999

        svc.invalidate_active_ids_cache()
        assert svc._active_ids_cache is None
        assert svc._active_ids_ts == 0


class TestQAServiceAddKnowledge:
    def test_add_knowledge(self):
        svc, mock_recall, _, _, mock_mysql = _make_service()
        mock_mysql.insert_qa.return_value = 42
        mock_recall.encode_query.return_value = [0.1] * 1024
        mock_mysql.get_all_questions.return_value = [{"id": 42, "question": "test"}]

        req = MagicMock()
        req.question = "新问题"
        req.answer = "新答案"
        req.category_l1 = "售后"
        req.category_l2 = "扣费"
        req.internal_process = ""
        req.feedback_dept = ""

        qa_id = svc.add_knowledge(req)
        assert qa_id == 42
        mock_mysql.insert_qa.assert_called_once()
        mock_recall.milvus.insert.assert_called_once()
        mock_recall.bm25.build.assert_called_once()

    def test_add_knowledge_no_categories(self):
        svc, mock_recall, _, _, mock_mysql = _make_service()
        mock_mysql.insert_qa.return_value = 1
        mock_recall.encode_query.return_value = [0.1] * 1024
        mock_mysql.get_all_questions.return_value = []

        req = MagicMock()
        req.question = "q"
        req.answer = "a"
        req.category_l1 = None
        req.category_l2 = None
        req.internal_process = None
        req.feedback_dept = None

        qa_id = svc.add_knowledge(req)
        assert qa_id == 1
        call_kwargs = mock_mysql.insert_qa.call_args
        assert call_kwargs[1]["category_l1"] == ""
