from unittest.mock import MagicMock

from rag.recall import RecallEngine


class TestRecallEngine:
    def setup_method(self):
        self.mock_embed = MagicMock()
        self.mock_milvus = MagicMock()
        self.mock_bm25 = MagicMock()
        self.mock_config = {
            "recall": {
                "vector_top_k": 10,
                "bm25_top_k": 10,
                "merge_method": "rrf",
                "rrf_k": 60,
                "vector_weight": 0.7,
                "bm25_weight": 0.3,
            },
            "models": {"query_prefix": "为这个句子生成表示以用于检索相关文章："},
        }
        import utils.config as cfg_module

        self._original_get = getattr(cfg_module, "get_config", None)
        cfg_module.get_config = lambda: self.mock_config
        self.engine = RecallEngine(self.mock_embed, self.mock_milvus, self.mock_bm25)

    def teardown_method(self):
        import utils.config as cfg_module

        if self._original_get:
            cfg_module.get_config = self._original_get

    def test_encode_query_adds_prefix(self):
        self.mock_embed.encode.return_value = MagicMock(tolist=lambda: [[0.1] * 1024])
        self.engine.encode_query("ETC扣费异常")
        call_args = self.mock_embed.encode.call_args[0][0]
        assert call_args[0].startswith("为这个句子生成表示以用于检索相关文章：")

    def test_vector_recall(self):
        self.mock_milvus.search.return_value = [(1, 0.9), (2, 0.8), (3, 0.7)]
        self.engine.vector_recall([0.1] * 1024, top_k=5)
        self.mock_milvus.search.assert_called_once()

    def test_bm25_recall(self):
        self.mock_bm25.search.return_value = [(1, 5.0), (3, 3.0), (5, 1.0)]
        self.engine.bm25_recall("ETC扣费异常", top_k=5)
        self.mock_bm25.search.assert_called_once_with("ETC扣费异常", top_k=5, active_qa_ids=None)

    def test_rrf_merge_combines_scores(self):
        vec = [(1, 0.9), (2, 0.8), (3, 0.7)]
        bm25 = [(3, 5.0), (4, 3.0), (5, 1.0)]
        result = self.engine.rrf_merge(vec, bm25)
        ids = [qid for qid, score in result]
        assert 3 in ids
        result_dict = dict(result)
        assert result_dict[3] > result_dict[1]

    def test_rrf_merge_deduplicates(self):
        vec = [(1, 0.9), (2, 0.8)]
        bm25 = [(2, 5.0), (3, 3.0)]
        result = self.engine.rrf_merge(vec, bm25)
        ids = [qid for qid, score in result]
        assert len(ids) == len(set(ids))

    def test_weighted_rrf_merge_combines_scores(self):
        self.engine.merge_method = "weighted_rrf"
        self.engine.vector_weight = 0.7
        self.engine.bm25_weight = 0.3
        vec = [(1, 0.9), (2, 0.8), (3, 0.7)]
        bm25 = [(3, 5.0), (4, 3.0), (5, 1.0)]
        result = self.engine.weighted_rrf_merge(vec, bm25)
        ids = [qid for qid, score in result]
        assert 3 in ids
        assert len(ids) == len(set(ids))

    def test_weighted_rrf_vector_dominant(self):
        self.engine.merge_method = "weighted_rrf"
        self.engine.vector_weight = 1.0
        self.engine.bm25_weight = 0.0
        vec = [(1, 0.9), (2, 0.5)]
        bm25 = [(2, 10.0), (3, 5.0)]
        result = self.engine.weighted_rrf_merge(vec, bm25)
        ids = [qid for qid, score in result]
        assert ids[0] == 1

    def test_weighted_rrf_equal_weights_same_as_rrf(self):
        self.engine.vector_weight = 1.0
        self.engine.bm25_weight = 1.0
        vec = [(1, 0.9), (2, 0.8), (3, 0.7)]
        bm25 = [(3, 5.0), (4, 3.0), (5, 1.0)]
        rrf_result = self.engine.rrf_merge(vec, bm25)
        wrrf_result = self.engine.weighted_rrf_merge(vec, bm25)
        rrf_ids = [qid for qid, _ in rrf_result]
        wrrf_ids = [qid for qid, _ in wrrf_result]
        assert rrf_ids == wrrf_ids

    def test_recall_calls_both_paths(self):
        self.mock_embed.encode.return_value = MagicMock(tolist=lambda: [[0.1] * 1024])
        self.mock_milvus.search.return_value = [(1, 0.9), (2, 0.8)]
        self.mock_bm25.search.return_value = [(3, 5.0), (4, 3.0)]
        self.engine.recall("ETC扣费异常")
        self.mock_milvus.search.assert_called_once()
        self.mock_bm25.search.assert_called_once()

    def test_parallel_recall(self):
        self.mock_embed.encode.return_value = MagicMock(tolist=lambda: [[0.1] * 1024])
        self.mock_milvus.search.return_value = [(1, 0.9), (2, 0.8)]
        self.mock_bm25.search.return_value = [(3, 5.0), (4, 3.0)]
        result = self.engine.recall("ETC扣费异常")
        self.mock_milvus.search.assert_called_once()
        self.mock_bm25.search.assert_called_once()
        ids = [qid for qid, _ in result]
        assert 1 in ids
        assert 2 in ids
        assert 3 in ids
        assert 4 in ids
        assert len(ids) == len(set(ids))

    def test_parallel_recall_merges_overlapping_ids(self):
        self.mock_embed.encode.return_value = MagicMock(tolist=lambda: [[0.1] * 1024])
        self.mock_milvus.search.return_value = [(1, 0.9), (2, 0.8), (3, 0.7)]
        self.mock_bm25.search.return_value = [(3, 5.0), (4, 3.0), (5, 1.0)]
        result = self.engine.recall("ETC扣费异常")
        ids = [qid for qid, _ in result]
        assert len(ids) == len(set(ids))
        result_dict = dict(result)
        assert result_dict[3] > result_dict[1]

    def test_parallel_recall_with_weighted_rrf(self):
        self.engine.merge_method = "weighted_rrf"
        self.mock_embed.encode.return_value = MagicMock(tolist=lambda: [[0.1] * 1024])
        self.mock_milvus.search.return_value = [(1, 0.9), (2, 0.8)]
        self.mock_bm25.search.return_value = [(3, 5.0), (4, 3.0)]
        result = self.engine.recall("ETC扣费异常")
        ids = [qid for qid, _ in result]
        assert 1 in ids
        assert 3 in ids
        assert len(ids) == len(set(ids))

    def test_parallel_recall_with_active_qa_ids(self):
        active_ids = ["qa_1", "qa_2"]
        self.mock_embed.encode.return_value = MagicMock(tolist=lambda: [[0.1] * 1024])
        self.mock_milvus.search.return_value = [(1, 0.9)]
        self.mock_bm25.search.return_value = [(2, 5.0)]
        self.engine.recall("ETC扣费异常", active_qa_ids=active_ids)
        milvus_kwargs = self.mock_milvus.search.call_args[1]
        bm25_kwargs = self.mock_bm25.search.call_args[1]
        assert milvus_kwargs["active_qa_ids"] == active_ids
        assert bm25_kwargs["active_qa_ids"] == active_ids

    def test_parallel_recall_uses_provided_query_vector(self):
        custom_vector = [0.5] * 1024
        self.mock_milvus.search.return_value = [(1, 0.9)]
        self.mock_bm25.search.return_value = [(2, 5.0)]
        self.engine.recall("ETC扣费异常", query_vector=custom_vector)
        self.mock_embed.encode.assert_not_called()
        self.mock_milvus.search.assert_called_once()
        self.mock_bm25.search.assert_called_once()
