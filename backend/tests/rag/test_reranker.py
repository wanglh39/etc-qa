from unittest.mock import MagicMock, patch

from rag.reranker import Reranker

MOCK_CONFIG = {
    "rerank": {"enabled": True, "top_k": 3},
}


class TestReranker:
    @patch("rag.reranker.get_config", return_value=MOCK_CONFIG)
    def test_rerank_returns_candidates_when_disabled(self, mock_cfg):
        mock_cfg.return_value = {"rerank": {"enabled": False, "top_k": 3}}
        reranker = Reranker(model=None)
        candidates = [(1, 0.5), (2, 0.3)]
        result = reranker.rerank("test", candidates)
        assert result == candidates

    @patch("rag.reranker.get_config", return_value=MOCK_CONFIG)
    def test_rerank_returns_empty_when_no_candidates(self, mock_cfg):
        mock_model = MagicMock()
        reranker = Reranker(model=mock_model)
        result = reranker.rerank("test", [])
        assert result == []

    @patch("rag.reranker.get_config", return_value=MOCK_CONFIG)
    def test_rerank_sorts_by_score(self, mock_cfg):
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.3, 0.9, 0.6]
        mock_mysql = MagicMock()
        mock_mysql.get_by_ids.return_value = [
            {"id": 1, "question": "问题1"},
            {"id": 2, "question": "问题2"},
            {"id": 3, "question": "问题3"},
        ]
        reranker = Reranker(model=mock_model, mysql_client=mock_mysql)
        candidates = [(1, 0.5), (2, 0.3), (3, 0.1)]
        result = reranker.rerank("test", candidates)
        assert result[0][0] == 2

    @patch("rag.reranker.get_config", return_value=MOCK_CONFIG)
    def test_rerank_respects_top_k(self, mock_cfg):
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.9, 0.8, 0.7, 0.6, 0.5]
        mock_mysql = MagicMock()
        mock_mysql.get_by_ids.return_value = [{"id": i, "question": f"问题{i}"} for i in range(1, 6)]
        reranker = Reranker(model=mock_model, mysql_client=mock_mysql)
        candidates = [(i, 0.5) for i in range(1, 6)]
        result = reranker.rerank("test", candidates)
        assert len(result) == 3

    @patch("rag.reranker.get_config", return_value=MOCK_CONFIG)
    def test_rerank_skips_missing_qa_ids(self, mock_cfg):
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.9]
        mock_mysql = MagicMock()
        mock_mysql.get_by_ids.return_value = [{"id": 1, "question": "问题1"}]
        reranker = Reranker(model=mock_model, mysql_client=mock_mysql)
        candidates = [(1, 0.5), (2, 0.3)]
        result = reranker.rerank("test", candidates)
        assert len(result) == 1

    @patch("rag.reranker.get_config", return_value=MOCK_CONFIG)
    def test_rerank_empty_qa_map_when_no_mysql_client(self, mock_cfg):
        mock_model = MagicMock()
        reranker = Reranker(model=mock_model, mysql_client=None)
        candidates = [(1, 0.5), (2, 0.3)]
        result = reranker.rerank("test", candidates)
        assert result == candidates

    @patch("rag.reranker.get_config", return_value=MOCK_CONFIG)
    def test_rerank_returns_candidates_when_no_matching_questions(self, mock_cfg):
        mock_model = MagicMock()
        mock_mysql = MagicMock()
        mock_mysql.get_by_ids.return_value = []
        reranker = Reranker(model=mock_model, mysql_client=mock_mysql)
        candidates = [(1, 0.5), (2, 0.3)]
        result = reranker.rerank("test", candidates)
        assert result == candidates

    def test_traceable_import_error_fallback(self):
        import importlib
        import sys

        import rag.reranker as reranker_module

        original_langsmith = sys.modules.get("langsmith")
        sys.modules["langsmith"] = None
        try:
            importlib.reload(reranker_module)
            deco = reranker_module.traceable(name="x", run_type="y")

            def sample():
                return 42

            assert deco(sample)() == 42
        finally:
            sys.modules["langsmith"] = original_langsmith
            importlib.reload(reranker_module)
