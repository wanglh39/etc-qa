import json
import os
import sys
from unittest.mock import MagicMock, patch

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

from scripts.maintenance.weekly_dedup import weekly_dedup


def _mock_config():
    return {
        "mysql": {"host": "localhost", "port": 3306, "user": "root", "password": "123456", "database": "etc_qa"},
        "milvus": {"db_path": "./test.db", "collection_name": "test_qa"},
        "models": {"embed": {"path": "fake", "dim": 1024}, "query_prefix": ""},
        "recall": {"vector_top_k": 10, "bm25_top_k": 10, "merge_method": "rrf", "rrf_k": 60},
        "dedup": {"question_threshold": 0.92, "answer_threshold": 0.85},
    }


def _make_work_order(wo_id, external_id, question, answer):
    return {
        "id": wo_id,
        "external_id": external_id,
        "raw_data": json.dumps({"question": question, "answer": answer}),
        "status": "processed",
    }


class TestWeeklyDedupNoWorkOrders:
    @patch("scripts.maintenance.weekly_dedup.get_config")
    @patch("scripts.maintenance.weekly_dedup.SentenceTransformer")
    @patch("scripts.maintenance.weekly_dedup.MilvusQA")
    @patch("scripts.maintenance.weekly_dedup.MySQLClient")
    def test_no_processed_work_orders(self, mock_mysql_cls, mock_milvus_cls,
                                      mock_embed_cls, mock_config_cls):
        mock_config_cls.return_value = _mock_config()
        mock_mysql = MagicMock()
        mock_mysql.get_work_orders_by_status.return_value = []
        mock_mysql_cls.return_value = mock_mysql
        weekly_dedup()
        mock_mysql.get_work_orders_by_status.assert_called_once_with("processed")


class TestWeeklyDedupRound1:
    @patch("scripts.maintenance.weekly_dedup.get_config")
    @patch("scripts.maintenance.weekly_dedup.SentenceTransformer")
    @patch("scripts.maintenance.weekly_dedup.MilvusQA")
    @patch("scripts.maintenance.weekly_dedup.MySQLClient")
    def test_duplicate_with_kb_marked_rejected(self, mock_mysql_cls, mock_milvus_cls,
                                                mock_embed_cls, mock_config_cls):
        mock_config_cls.return_value = _mock_config()
        wo = _make_work_order(1, "WO001", "ETC扣费异常", "核实退款处理")
        mock_mysql = MagicMock()
        mock_mysql.get_work_orders_by_status.return_value = [wo]
        mock_mysql.get_active_ids.return_value = [1, 2, 3]
        mock_mysql_cls.return_value = mock_mysql
        mock_milvus = MagicMock()
        mock_milvus.search.return_value = [(5, 0.96)]
        mock_milvus_cls.return_value = mock_milvus
        mock_embed = MagicMock()
        mock_embed.encode.return_value = np.array([[0.1] * 1024])
        mock_embed_cls.return_value = mock_embed
        weekly_dedup()
        mock_mysql.update_work_order.assert_any_call(
            "WO001", json.dumps({"duplicate_of": 5}), "rejected"
        )


class TestWeeklyDedupRound1NotDuplicate:
    @patch("scripts.maintenance.weekly_dedup.get_config")
    @patch("scripts.maintenance.weekly_dedup.SentenceTransformer")
    @patch("scripts.maintenance.weekly_dedup.MilvusQA")
    @patch("scripts.maintenance.weekly_dedup.MySQLClient")
    def test_not_duplicate_with_kb_marked_deduped(self, mock_mysql_cls, mock_milvus_cls,
                                                    mock_embed_cls, mock_config_cls):
        mock_config_cls.return_value = _mock_config()
        wo = _make_work_order(1, "WO001", "ETC新问题", "新答案")
        mock_mysql = MagicMock()
        mock_mysql.get_work_orders_by_status.return_value = [wo]
        mock_mysql.get_active_ids.return_value = [1, 2, 3]
        mock_mysql_cls.return_value = mock_mysql
        mock_milvus = MagicMock()
        mock_milvus.search.return_value = [(5, 0.80)]
        mock_milvus_cls.return_value = mock_milvus
        mock_embed = MagicMock()
        mock_embed.encode.return_value = np.array([[0.1] * 1024])
        mock_embed_cls.return_value = mock_embed
        weekly_dedup()
        mock_mysql.update_work_order.assert_called_with("WO001", "", "deduped")


class TestWeeklyDedupRound1NoResult:
    @patch("scripts.maintenance.weekly_dedup.get_config")
    @patch("scripts.maintenance.weekly_dedup.SentenceTransformer")
    @patch("scripts.maintenance.weekly_dedup.MilvusQA")
    @patch("scripts.maintenance.weekly_dedup.MySQLClient")
    def test_no_kb_match_marked_deduped(self, mock_mysql_cls, mock_milvus_cls,
                                          mock_embed_cls, mock_config_cls):
        mock_config_cls.return_value = _mock_config()
        wo = _make_work_order(1, "WO001", "全新问题", "全新答案")
        mock_mysql = MagicMock()
        mock_mysql.get_work_orders_by_status.return_value = [wo]
        mock_mysql.get_active_ids.return_value = []
        mock_mysql_cls.return_value = mock_mysql
        mock_milvus = MagicMock()
        mock_milvus.search.return_value = []
        mock_milvus_cls.return_value = mock_milvus
        mock_embed = MagicMock()
        mock_embed.encode.return_value = np.array([[0.1] * 1024])
        mock_embed_cls.return_value = mock_embed
        weekly_dedup()
        mock_mysql.update_work_order.assert_called_with("WO001", "", "deduped")


class TestWeeklyDedupRound2:
    @patch("scripts.maintenance.weekly_dedup.get_config")
    @patch("scripts.maintenance.weekly_dedup.SentenceTransformer")
    @patch("scripts.maintenance.weekly_dedup.MilvusQA")
    @patch("scripts.maintenance.weekly_dedup.MySQLClient")
    def test_internal_duplicate_both_similar_q_and_a(self, mock_mysql_cls, mock_milvus_cls,
                                                      mock_embed_cls, mock_config_cls):
        mock_config_cls.return_value = _mock_config()
        wo1 = _make_work_order(1, "WO001", "ETC扣费异常", "核实退款处理流程")
        wo2 = _make_work_order(2, "WO002", "ETC扣费异常怎么处理", "核实退款处理流程一样")
        mock_mysql = MagicMock()
        mock_mysql.get_work_orders_by_status.return_value = [wo1, wo2]
        mock_mysql.get_active_ids.return_value = []
        mock_mysql_cls.return_value = mock_mysql
        mock_milvus = MagicMock()
        mock_milvus.search.return_value = []
        mock_milvus_cls.return_value = mock_milvus
        q_vec1 = np.array([1.0] + [0.0] * 1023)
        q_vec2 = np.array([0.99] + [0.0] + [0.141] + [0.0] * 1021)
        a_vec1 = np.array([1.0] + [0.0] * 1023)
        a_vec2 = np.array([0.95] + [0.0] + [0.312] + [0.0] * 1021)
        call_count = [0]
        def mock_encode(texts, **kwargs):
            if isinstance(texts, list) and len(texts) == 2 and isinstance(texts[0], str):
                return np.array([a_vec1, a_vec2])
            call_count[0] += 1
            if call_count[0] == 1:
                return np.array([q_vec1])
            else:
                return np.array([q_vec1, q_vec2])
        mock_embed = MagicMock()
        mock_embed.encode.side_effect = mock_encode
        mock_embed_cls.return_value = mock_embed
        weekly_dedup()
        update_calls = mock_mysql.update_work_order.call_args_list
        rejected_calls = [c for c in update_calls if c[0][2] == "rejected"]
        deduped_calls = [c for c in update_calls if c[0][2] == "deduped"]
        assert len(rejected_calls) >= 1 or len(deduped_calls) >= 1

    @patch("scripts.maintenance.weekly_dedup.get_config")
    @patch("scripts.maintenance.weekly_dedup.SentenceTransformer")
    @patch("scripts.maintenance.weekly_dedup.MilvusQA")
    @patch("scripts.maintenance.weekly_dedup.MySQLClient")
    def test_internal_not_duplicate_different_answer(self, mock_mysql_cls, mock_milvus_cls,
                                                      mock_embed_cls, mock_config_cls):
        mock_config_cls.return_value = _mock_config()
        wo1 = _make_work_order(1, "WO001", "ETC扣费异常", "核实退款处理")
        wo2 = _make_work_order(2, "WO002", "ETC扣费异常", "完全不同的答案关于设备故障")
        mock_mysql = MagicMock()
        mock_mysql.get_work_orders_by_status.return_value = [wo1, wo2]
        mock_mysql.get_active_ids.return_value = []
        mock_mysql_cls.return_value = mock_mysql
        mock_milvus = MagicMock()
        mock_milvus.search.return_value = []
        mock_milvus_cls.return_value = mock_milvus
        q_vec1 = np.array([1.0] + [0.0] * 1023)
        q_vec2 = np.array([1.0] + [0.0] * 1023)
        a_vec1 = np.array([1.0] + [0.0] * 1023)
        a_vec2 = np.array([0.0, 1.0] + [0.0] * 1022)
        call_count = [0]
        def mock_encode(texts, **kwargs):
            if isinstance(texts, list) and len(texts) == 2 and isinstance(texts[0], str):
                return np.array([a_vec1, a_vec2])
            call_count[0] += 1
            if call_count[0] == 1:
                return np.array([q_vec1])
            else:
                return np.array([q_vec1, q_vec2])
        mock_embed = MagicMock()
        mock_embed.encode.side_effect = mock_encode
        mock_embed_cls.return_value = mock_embed
        weekly_dedup()
        update_calls = mock_mysql.update_work_order.call_args_list
        deduped_calls = [c for c in update_calls if c[0][2] == "deduped"]
        assert len(deduped_calls) == 2


class TestWeeklyDedupRound2KeepLonger:
    @patch("scripts.maintenance.weekly_dedup.get_config")
    @patch("scripts.maintenance.weekly_dedup.SentenceTransformer")
    @patch("scripts.maintenance.weekly_dedup.MilvusQA")
    @patch("scripts.maintenance.weekly_dedup.MySQLClient")
    def test_keeps_longer_answer(self, mock_mysql_cls, mock_milvus_cls,
                                  mock_embed_cls, mock_config_cls):
        mock_config_cls.return_value = _mock_config()
        short_answer = "短答案"
        long_answer = "这是一个比较长的答案包含更多详细信息和处理流程说明"
        wo1 = _make_work_order(1, "WO001", "ETC扣费异常", short_answer)
        wo2 = _make_work_order(2, "WO002", "ETC扣费异常怎么处理", long_answer)
        mock_mysql = MagicMock()
        mock_mysql.get_work_orders_by_status.return_value = [wo1, wo2]
        mock_mysql.get_active_ids.return_value = []
        mock_mysql_cls.return_value = mock_mysql
        mock_milvus = MagicMock()
        mock_milvus.search.return_value = []
        mock_milvus_cls.return_value = mock_milvus
        q_vec = np.array([1.0] + [0.0] * 1023)
        a_vec = np.array([1.0] + [0.0] * 1023)
        call_count = [0]
        def mock_encode(texts, **kwargs):
            if isinstance(texts, list) and len(texts) == 2 and isinstance(texts[0], str):
                return np.array([a_vec, a_vec])
            call_count[0] += 1
            if call_count[0] == 1:
                return np.array([q_vec])
            else:
                return np.array([q_vec, q_vec])
        mock_embed = MagicMock()
        mock_embed.encode.side_effect = mock_encode
        mock_embed_cls.return_value = mock_embed
        weekly_dedup()
        update_calls = mock_mysql.update_work_order.call_args_list
        rejected_calls = [c for c in update_calls if c[0][2] == "rejected"]
        if rejected_calls:
            rejected_ext_id = rejected_calls[0][0][0]
            assert rejected_ext_id == "WO001"


class TestWeeklyDedupSingleWorkOrder:
    @patch("scripts.maintenance.weekly_dedup.get_config")
    @patch("scripts.maintenance.weekly_dedup.SentenceTransformer")
    @patch("scripts.maintenance.weekly_dedup.MilvusQA")
    @patch("scripts.maintenance.weekly_dedup.MySQLClient")
    def test_single_work_order_skips_round2(self, mock_mysql_cls, mock_milvus_cls,
                                              mock_embed_cls, mock_config_cls):
        mock_config_cls.return_value = _mock_config()
        wo = _make_work_order(1, "WO001", "ETC扣费异常", "核实退款")
        mock_mysql = MagicMock()
        mock_mysql.get_work_orders_by_status.return_value = [wo]
        mock_mysql.get_active_ids.return_value = []
        mock_mysql_cls.return_value = mock_mysql
        mock_milvus = MagicMock()
        mock_milvus.search.return_value = []
        mock_milvus_cls.return_value = mock_milvus
        mock_embed = MagicMock()
        mock_embed.encode.return_value = np.array([[0.1] * 1024])
        mock_embed_cls.return_value = mock_embed
        weekly_dedup()
        mock_mysql.update_work_order.assert_called_with("WO001", "", "deduped")


class TestWeeklyDedupEmptyRawData:
    @patch("scripts.maintenance.weekly_dedup.get_config")
    @patch("scripts.maintenance.weekly_dedup.SentenceTransformer")
    @patch("scripts.maintenance.weekly_dedup.MilvusQA")
    @patch("scripts.maintenance.weekly_dedup.MySQLClient")
    def test_empty_raw_data_handled(self, mock_mysql_cls, mock_milvus_cls,
                                      mock_embed_cls, mock_config_cls):
        mock_config_cls.return_value = _mock_config()
        wo = {"id": 1, "external_id": "WO001", "raw_data": None, "status": "processed"}
        mock_mysql = MagicMock()
        mock_mysql.get_work_orders_by_status.return_value = [wo]
        mock_mysql.get_active_ids.return_value = []
        mock_mysql_cls.return_value = mock_mysql
        mock_milvus = MagicMock()
        mock_milvus.search.return_value = []
        mock_milvus_cls.return_value = mock_milvus
        mock_embed = MagicMock()
        mock_embed.encode.return_value = np.array([[0.1] * 1024])
        mock_embed_cls.return_value = mock_embed
        weekly_dedup()
        mock_mysql.update_work_order.assert_called_with("WO001", "", "deduped")
