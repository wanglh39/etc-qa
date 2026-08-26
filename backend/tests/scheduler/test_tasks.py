import json
from unittest.mock import MagicMock, patch

import pytest

from scheduler.tasks import (
    _check_dedup,
    _question_similarity,
    cleanup_task,
    sync_and_ingest_task,
)


class TestQuestionSimilarity:
    def test_identical_questions(self):
        score = _question_similarity("ETC扣费异常怎么处理", "ETC扣费异常怎么处理")
        assert score == 1.0

    def test_empty_question(self):
        assert _question_similarity("", "test") == 0.0
        assert _question_similarity("test", "") == 0.0
        assert _question_similarity("", "") == 0.0

    def test_similar_questions(self):
        score = _question_similarity("ETC扣费异常怎么处理", "ETC扣费异常如何处理")
        assert 0.7 < score < 1.0

    def test_different_questions(self):
        score = _question_similarity("ETC扣费异常怎么处理", "高速公路限速是多少")
        assert score < 0.5


class TestCheckDedup:
    def test_duplicate_above_threshold(self):
        existing = ["ETC扣费异常怎么处理", "ETC设备故障怎么办"]
        is_dup, score = _check_dedup("ETC扣费异常怎么处理", existing, 0.85)
        assert is_dup is True
        assert score == 1.0

    def test_not_duplicate_below_threshold(self):
        existing = ["高速公路限速是多少"]
        is_dup, score = _check_dedup("ETC扣费异常怎么处理", existing, 0.85)
        assert is_dup is False
        assert score < 0.85

    def test_empty_existing(self):
        is_dup, score = _check_dedup("ETC扣费异常", [], 0.85)
        assert is_dup is False
        assert score == 0.0

    def test_best_score_returned(self):
        existing = ["ETC设备故障怎么办", "ETC扣费异常如何处理", "高速收费问题"]
        is_dup, score = _check_dedup("ETC扣费异常怎么处理", existing, 0.99)
        assert is_dup is False
        assert 0.7 < score < 0.99


class TestSyncAndIngestTask:
    @patch("scheduler.tasks._log_task_execution")
    @patch("scheduler.tasks.MySQLClient")
    @patch("scheduler.tasks.WorkOrderClient")
    @patch("scheduler.tasks.ingest_agent")
    @patch("scheduler.tasks.get_config")
    def test_no_work_orders(self, mock_cfg, mock_agent, mock_wo, mock_mysql, mock_log):
        mock_cfg.return_value = {
            "work_order": {"use_mock": True},
            "scheduler": {"jobs": {"sync_and_ingest": {"dedup_threshold": 0.85}}},
        }
        mock_mysql_inst = MagicMock()
        mock_mysql.return_value = mock_mysql_inst
        mock_mysql_inst.get_work_orders_by_status.return_value = []
        mock_wo_inst = MagicMock()
        mock_wo.return_value = mock_wo_inst
        mock_wo_inst.fetch_processed_work_orders.return_value = []

        stats = sync_and_ingest_task()

        assert stats["fetched"] == 0
        assert stats["preprocessed"] == 0
        assert stats["deduped"] == 0
        assert stats["rejected_dup"] == 0

    @patch("scheduler.tasks._log_task_execution")
    @patch("scheduler.tasks.MySQLClient")
    @patch("scheduler.tasks.WorkOrderClient")
    @patch("scheduler.tasks.ingest_agent")
    @patch("scheduler.tasks.get_config")
    def test_full_flow_with_dedup(self, mock_cfg, mock_agent, mock_wo, mock_mysql, mock_log):
        mock_cfg.return_value = {
            "work_order": {"use_mock": True},
            "scheduler": {"jobs": {"sync_and_ingest": {"dedup_threshold": 0.85}}},
        }
        mock_mysql_inst = MagicMock()
        mock_mysql.return_value = mock_mysql_inst

        mock_mysql_inst.get_work_orders_by_status.side_effect = [
            [],
            [
                {
                    "id": 1,
                    "external_id": "WO-001",
                    "raw_data": json.dumps({"question": "ETC扣费异常", "answer": "检查设备"}),
                }
            ],
            [
                {
                    "id": 1,
                    "external_id": "WO-001",
                    "raw_data": json.dumps({"question": "ETC扣费异常", "answer": "检查设备", "category_l1": "扣费"}),
                }
            ],
        ]
        mock_mysql_inst.get_all_questions.return_value = [{"question": "高速公路限速是多少"}]
        mock_mysql_inst.insert_qa_with_status.return_value = 99

        mock_wo_inst = MagicMock()
        mock_wo.return_value = mock_wo_inst
        mock_wo_inst.fetch_processed_work_orders.return_value = [
            {"external_id": "WO-001", "question": "ETC扣费异常", "answer": "检查设备"}
        ]

        mock_agent.invoke.return_value = {"question": "ETC扣费异常", "answer": "检查设备", "category_l1": "扣费"}

        stats = sync_and_ingest_task()

        assert stats["fetched"] == 1
        assert stats["deduped"] == 1
        mock_mysql_inst.insert_qa_with_status.assert_called_once()

    @patch("scheduler.tasks._log_task_execution")
    @patch("scheduler.tasks.MySQLClient")
    @patch("scheduler.tasks.WorkOrderClient")
    @patch("scheduler.tasks.ingest_agent")
    @patch("scheduler.tasks.get_config")
    def test_duplicate_rejected(self, mock_cfg, mock_agent, mock_wo, mock_mysql, mock_log):
        mock_cfg.return_value = {
            "work_order": {"use_mock": True},
            "scheduler": {"jobs": {"sync_and_ingest": {"dedup_threshold": 0.85}}},
        }
        mock_mysql_inst = MagicMock()
        mock_mysql.return_value = mock_mysql_inst

        mock_mysql_inst.get_work_orders_by_status.side_effect = [
            [],
            [
                {
                    "id": 1,
                    "external_id": "WO-001",
                    "raw_data": json.dumps({"question": "ETC扣费异常怎么处理", "answer": "检查设备"}),
                }
            ],
        ]
        mock_mysql_inst.get_all_questions.return_value = [{"question": "ETC扣费异常怎么处理"}]

        mock_wo_inst = MagicMock()
        mock_wo.return_value = mock_wo_inst
        mock_wo_inst.fetch_processed_work_orders.return_value = []

        stats = sync_and_ingest_task()

        assert stats["rejected_dup"] == 1
        assert stats["deduped"] == 0


class TestCleanupTask:
    @patch("scheduler.tasks._log_task_execution")
    @patch("scheduler.tasks.MySQLClient")
    def test_cleanup_success(self, mock_mysql, mock_log):
        mock_mysql_inst = MagicMock()
        mock_mysql.return_value = mock_mysql_inst

        stats = cleanup_task()

        assert stats["cleaned"] == 1
        mock_mysql_inst.delete_work_orders_by_status.assert_called_once_with(["imported", "rejected"])

    @patch("scheduler.tasks._log_task_execution")
    @patch("scheduler.tasks.MySQLClient")
    def test_cleanup_failure(self, mock_mysql, mock_log):
        mock_mysql_inst = MagicMock()
        mock_mysql.return_value = mock_mysql_inst
        mock_mysql_inst.delete_work_orders_by_status.side_effect = Exception("DB error")

        stats = cleanup_task()

        assert stats["cleaned"] == 0
