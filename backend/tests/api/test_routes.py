from unittest.mock import MagicMock, patch

import pytest

from api.routes import agent_process, health, query_qa, set_mysql_client, set_service
from models.schemas import AgentProcessRequest, QASearchRequest, QueryRequest

MOCK_SERVICE_RESPONSE = {
    "query": "ETC扣费异常",
    "standardized_query": "ETC扣费异常",
    "confidence": "high",
    "candidates": [],
    "total_candidates": 0,
}


class TestQueryAPI:
    def test_query_returns_response(self):
        mock_service = MagicMock()
        mock_service.query.return_value = MagicMock(**MOCK_SERVICE_RESPONSE)
        set_service(mock_service)

        req = QueryRequest(question="ETC扣费异常")
        result = query_qa(req)
        assert result.confidence == "high"

    def test_query_without_service(self):
        set_service(None)
        req = QueryRequest(question="test")
        with pytest.raises(Exception):
            query_qa(req)

    @patch("api.routes.work_order_client")
    @patch("api.routes.mysql_client")
    def test_query_does_not_auto_create_work_order(self, mock_mysql, mock_wo):
        mock_service = MagicMock()
        low_conf_response = MagicMock(
            query="ETC扣费异常",
            standardized_query="ETC扣费异常",
            confidence="low",
            candidates=[],
            total_candidates=0,
            work_order_id=None,
        )
        mock_service.query.return_value = low_conf_response
        set_service(mock_service)
        mock_wo.create_work_order.return_value = "WO123"

        req = QueryRequest(question="ETC扣费异常")
        result = query_qa(req)
        mock_wo.create_work_order.assert_not_called()


class TestAgentProcessAPI:
    @patch("api.routes.ingest_agent")
    def test_agent_process_returns_response(self, mock_ingest):
        mock_ingest.invoke.return_value = {
            "question": "ETC扣费异常如何处理",
            "answer": "核实后退款",
            "internal_process": "核实扣费记录",
            "feedback_dept": "账单组",
            "is_duplicate": False,
            "duplicate_of": None,
            "similarity_score": 0.75,
            "category_l1": "账单问题",
            "category_l2": "ETC扣费",
            "category_confidence": 0.92,
            "needs_review": False,
            "review_highlights": [],
            "current_step": "classify",
            "error": None,
        }

        req = AgentProcessRequest(question="ETC扣费异常", answer="核实后退款")
        result = agent_process(req)
        assert result.category_l1 == "账单问题"


class TestHealthAPI:
    def test_health_check(self):
        result = health()
        assert result["status"] == "ok"


class TestQAListAPI:
    def test_list_qa(self):
        mock_mysql = MagicMock()
        mock_mysql.get_qa_list.return_value = {
            "items": [
                {"id": 1, "question": "ETC扣费异常", "answer": "核实退款",
                 "category_l1": "账单问题", "category_l2": "ETC扣费",
                 "status": "active", "created_at": "2024-01-01", "updated_at": "2024-01-01"},
            ],
            "total": 1, "page": 1, "page_size": 20,
        }
        set_mysql_client(mock_mysql)

        from api.routes import list_qa
        result = list_qa(page=1, page_size=20)
        assert result.total == 1
        assert len(result.items) == 1

    def test_list_qa_no_service(self):
        set_mysql_client(None)
        from api.routes import list_qa
        with pytest.raises(Exception):
            list_qa()


class TestQADetailAPI:
    def test_get_qa_detail(self):
        mock_mysql = MagicMock()
        mock_mysql.get_qa_detail.return_value = {
            "id": 1, "question": "ETC扣费异常", "answer": "核实退款",
            "category_l1": "账单问题", "category_l2": "ETC扣费",
            "internal_process": "核实", "feedback_dept": "账单组",
            "status": "active", "created_at": "2024-01-01", "updated_at": "2024-01-01",
        }
        set_mysql_client(mock_mysql)

        from api.routes import get_qa_detail
        result = get_qa_detail(1)
        assert result.id == 1

    def test_get_qa_detail_not_found(self):
        mock_mysql = MagicMock()
        mock_mysql.get_qa_detail.return_value = None
        set_mysql_client(mock_mysql)

        from api.routes import get_qa_detail
        with pytest.raises(Exception):
            get_qa_detail(999)


class TestDeleteQAAPI:
    def test_delete_qa(self):
        mock_mysql = MagicMock()
        mock_mysql.delete_qa.return_value = True
        set_mysql_client(mock_mysql)
        mock_service = MagicMock()
        set_service(mock_service)

        from api.routes import delete_qa
        result = delete_qa(1)
        assert result["qa_id"] == 1
        mock_service.invalidate_active_ids_cache.assert_called_once()

    def test_delete_qa_not_found(self):
        mock_mysql = MagicMock()
        mock_mysql.delete_qa.return_value = False
        set_mysql_client(mock_mysql)

        from api.routes import delete_qa
        with pytest.raises(Exception):
            delete_qa(999)


class TestQASearchAPI:
    def test_search_qa(self):
        mock_mysql = MagicMock()
        mock_mysql.search_qa.return_value = {
            "items": [
                {"id": 1, "question": "ETC扣费异常", "answer": "核实退款",
                 "category_l1": "账单问题", "category_l2": "ETC扣费",
                 "status": "active", "created_at": "2024-01-01", "updated_at": "2024-01-01"},
            ],
            "total": 1, "page": 1, "page_size": 20,
        }
        set_mysql_client(mock_mysql)

        from api.routes import search_qa
        req = QASearchRequest(keyword="ETC")
        result = search_qa(req)
        assert result.total == 1


class TestStatsAPI:
    def test_get_stats(self):
        mock_mysql = MagicMock()
        mock_mysql.count_qa.return_value = {"active": 10, "deprecated": 2, "archived": 1, "total": 13}
        mock_mysql.count_work_orders.return_value = {"submitted": 5, "processed": 3, "total": 8}
        mock_mysql.get_category_stats.return_value = {"账单问题": 10, "设备问题": 3}
        set_mysql_client(mock_mysql)

        from api.routes import get_stats
        result = get_stats()
        assert result.qa_total == 13
        assert result.qa_active == 10
        assert result.work_order_total == 8


class TestCategoriesAPI:
    def test_get_categories(self):
        mock_mysql = MagicMock()
        mock_mysql.get_category_tree.return_value = {"账单问题": ["ETC扣费", "发票问题"]}
        set_mysql_client(mock_mysql)

        from api.routes import get_categories
        result = get_categories()
        assert "账单问题" in result["categories"]


class TestWorkOrderListAPI:
    def test_list_work_orders(self):
        mock_mysql = MagicMock()
        mock_mysql.get_work_order_list.return_value = {
            "items": [
                {"id": 1, "external_id": "WO1", "raw_data": "test", "status": "submitted",
                 "created_at": "2024-01-01", "updated_at": "2024-01-01"},
            ],
            "total": 1, "page": 1, "page_size": 20,
        }
        set_mysql_client(mock_mysql)

        from api.routes import list_work_orders
        result = list_work_orders(page=1, page_size=20)
        assert result.total == 1
