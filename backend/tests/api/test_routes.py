import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from api.routes import (
    _current_operator,
    _fmt_dt,
    _parse_raw_data,
    _serialize_row,
    agent_process,
    asr_query,
    audit_history,
    create_category,
    create_role,
    create_user,
    create_work_order,
    delete_category,
    delete_role,
    delete_user,
    get_categories,
    get_work_order,
    list_roles,
    list_users,
    query_qa,
    reply_work_order,
    reset_password,
    set_mysql_client,
    set_service,
    stats_trend,
    update_category,
    update_qa_status,
    update_role,
    update_user,
)
from asr.models import ASRResponse
from models.schemas import (
    AgentProcessRequest,
    CategoryCreateRequest,
    CategoryUpdateRequest,
    QASearchRequest,
    QueryRequest,
    ResetPasswordRequest,
    RoleCreateRequest,
    RoleUpdateRequest,
    UpdateStatusRequest,
    UserCreateRequest,
    UserUpdateRequest,
    WorkOrderCreateRequest,
    WorkOrderReplyRequest,
)

MOCK_SERVICE_RESPONSE = {
    "query": "ETC扣费异常",
    "standardized_query": "ETC扣费异常",
    "confidence": "high",
    "candidates": [],
    "total_candidates": 0,
}

MOCK_USER = {"sub": "test_user", "role": "admin"}


class TestQueryAPI:
    def test_query_returns_response(self):
        mock_service = MagicMock()
        mock_service.query.return_value = MagicMock(**MOCK_SERVICE_RESPONSE)
        set_service(mock_service)

        req = QueryRequest(question="ETC扣费异常")
        result = query_qa(req, MOCK_USER)
        assert result.confidence == "high"

    def test_query_without_service(self):
        set_service(None)
        req = QueryRequest(question="test")
        with pytest.raises(Exception):
            query_qa(req, MOCK_USER)

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
        result = query_qa(req, MOCK_USER)
        mock_wo.create_work_order.assert_not_called()

    @patch("api.routes.limiter")
    def test_query_rate_limited(self, mock_limiter):
        mock_limiter.check.return_value = False
        req = QueryRequest(question="test")
        with pytest.raises(HTTPException) as exc:
            query_qa(req, MOCK_USER)
        assert exc.value.status_code == 429


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
        result = agent_process(req, MOCK_USER)
        assert result.category_l1 == "账单问题"

    @patch("api.routes.limiter")
    def test_agent_process_rate_limited(self, mock_limiter):
        mock_limiter.check.return_value = False
        req = AgentProcessRequest(question="test")
        with pytest.raises(HTTPException) as exc:
            agent_process(req, MOCK_USER)
        assert exc.value.status_code == 429


class TestQAListAPI:
    def test_list_qa(self):
        mock_mysql = MagicMock()
        mock_mysql.get_qa_list.return_value = {
            "items": [
                {
                    "id": 1,
                    "question": "ETC扣费异常",
                    "answer": "核实退款",
                    "category_l1": "账单问题",
                    "category_l2": "ETC扣费",
                    "status": "active",
                    "created_at": "2024-01-01",
                    "updated_at": "2024-01-01",
                },
            ],
            "total": 1,
            "page": 1,
            "page_size": 20,
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
            "id": 1,
            "question": "ETC扣费异常",
            "answer": "核实退款",
            "category_l1": "账单问题",
            "category_l2": "ETC扣费",
            "internal_process": "核实",
            "feedback_dept": "账单组",
            "status": "active",
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01",
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
        mock_service.deactivate_qa.assert_called_once_with(1)

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
                {
                    "id": 1,
                    "question": "ETC扣费异常",
                    "answer": "核实退款",
                    "category_l1": "账单问题",
                    "category_l2": "ETC扣费",
                    "status": "active",
                    "created_at": "2024-01-01",
                    "updated_at": "2024-01-01",
                },
            ],
            "total": 1,
            "page": 1,
            "page_size": 20,
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
        mock_mysql.list_categories.return_value = []
        mock_mysql.get_category_tree.return_value = {"账单问题": ["ETC扣费", "发票问题"]}
        set_mysql_client(mock_mysql)

        from api.routes import get_categories

        result = get_categories()
        labels = [n["label"] for n in result["categories"]]
        assert "账单问题" in labels

    def test_get_categories_with_rows(self):
        mock_mysql = MagicMock()
        mock_mysql.list_categories.return_value = [
            {"id": 1, "label": "账单问题", "parent_id": None, "description": "desc"},
            {"id": 2, "label": "ETC扣费", "parent_id": 1, "description": None},
        ]
        set_mysql_client(mock_mysql)

        result = get_categories()
        roots = result["categories"]
        root = next(n for n in roots if n["label"] == "账单问题")
        child_labels = [c["label"] for c in root["children"]]
        assert "ETC扣费" in child_labels

    def test_get_categories_with_empty_label(self):
        mock_mysql = MagicMock()
        mock_mysql.list_categories.return_value = []
        mock_mysql.get_category_tree.return_value = {"": ["子类"], "账单问题": ["ETC"]}
        set_mysql_client(mock_mysql)

        result = get_categories()
        labels = [n["label"] for n in result["categories"]]
        assert "账单问题" in labels
        assert "" not in labels

    def test_get_categories_no_mysql(self):
        set_mysql_client(None)
        with pytest.raises(HTTPException) as exc:
            get_categories()
        assert exc.value.status_code == 500


class TestWorkOrderListAPI:
    def test_list_work_orders(self):
        mock_mysql = MagicMock()
        mock_mysql.get_work_order_list.return_value = {
            "items": [
                {
                    "id": 1,
                    "external_id": "WO1",
                    "raw_data": "test",
                    "status": "submitted",
                    "created_at": "2024-01-01",
                    "updated_at": "2024-01-01",
                },
            ],
            "total": 1,
            "page": 1,
            "page_size": 20,
        }
        set_mysql_client(mock_mysql)

        from api.routes import list_work_orders

        result = list_work_orders(page=1, page_size=20)
        assert result.total == 1


class TestSerializeRow:
    def test_serialize_datetime(self):
        row = {"id": 1, "created_at": datetime(2024, 1, 1, 12, 0, 0)}
        result = _serialize_row(row)
        assert result["created_at"] == "2024-01-01 12:00:00"
        assert result["id"] == 1

    def test_serialize_non_datetime(self):
        row = {"id": 1, "name": "测试"}
        result = _serialize_row(row)
        assert result["name"] == "测试"
        assert result["id"] == 1


class TestCurrentOperator:
    def test_with_valid_bearer_token(self):
        with patch("utils.jwt_utils.verify_token", return_value={"sub": "user1"}):
            req = MagicMock()
            req.headers.get.return_value = "Bearer abc"
            assert _current_operator(req) == "user1"

    def test_with_invalid_bearer_token(self):
        with patch("utils.jwt_utils.verify_token", side_effect=Exception("bad token")):
            req = MagicMock()
            req.headers.get.return_value = "Bearer bad"
            assert _current_operator(req) == "admin"

    def test_without_auth(self):
        req = MagicMock()
        req.headers.get.return_value = ""
        assert _current_operator(req) == "admin"

    def test_with_non_bearer_auth(self):
        req = MagicMock()
        req.headers.get.return_value = "Basic xyz"
        assert _current_operator(req) == "admin"


class TestParseRawData:
    def test_parse_valid_dict(self):
        assert _parse_raw_data('{"a": 1}') == {"a": 1}

    def test_parse_none(self):
        assert _parse_raw_data(None) == {}

    def test_parse_empty(self):
        assert _parse_raw_data("") == {}

    def test_parse_invalid_json(self):
        assert _parse_raw_data("not json") == {}

    def test_parse_non_dict(self):
        assert _parse_raw_data("[1, 2]") == {}


class TestFmtDt:
    def test_fmt_datetime(self):
        assert _fmt_dt(datetime(2024, 1, 1, 12, 0, 0)) == "2024-01-01 12:00:00"

    def test_fmt_none(self):
        assert _fmt_dt(None) is None

    def test_fmt_string(self):
        assert _fmt_dt("2024-01-01") == "2024-01-01"


class TestUpdateQAStatusAPI:
    @patch("api.routes.get_business_config")
    def test_update_status_deprecated(self, mock_cfg):
        mock_cfg.return_value = ["active", "deprecated", "archived"]
        mock_mysql = MagicMock()
        set_mysql_client(mock_mysql)
        mock_service = MagicMock()
        set_service(mock_service)
        req = UpdateStatusRequest(qa_id=1, status="deprecated")
        request = MagicMock()
        request.headers.get.return_value = ""
        result = update_qa_status(req, request)
        assert result.status == "deprecated"
        mock_mysql.update_qa_status.assert_called_once_with(1, "deprecated")
        mock_service.deactivate_qa.assert_called_once_with(1)
        mock_mysql.insert_audit_log.assert_not_called()

    @patch("api.routes.get_business_config")
    def test_update_status_active_with_audit(self, mock_cfg):
        mock_cfg.return_value = ["active", "deprecated", "archived"]
        mock_mysql = MagicMock()
        mock_mysql.get_qa_detail.return_value = {"question": "q", "answer": "a"}
        set_mysql_client(mock_mysql)
        set_service(MagicMock())
        req = UpdateStatusRequest(qa_id=1, status="active")
        request = MagicMock()
        request.headers.get.return_value = ""
        result = update_qa_status(req, request)
        assert result.status == "active"
        mock_mysql.insert_audit_log.assert_called_once()
        call_kwargs = mock_mysql.insert_audit_log.call_args.kwargs
        assert call_kwargs["result"] == "pass"
        assert call_kwargs["qa_id"] == 1

    @patch("api.routes.get_business_config")
    def test_update_status_archived_with_audit(self, mock_cfg):
        mock_cfg.return_value = ["active", "deprecated", "archived"]
        mock_mysql = MagicMock()
        mock_mysql.get_qa_detail.return_value = {"question": "q", "answer": "a"}
        set_mysql_client(mock_mysql)
        set_service(MagicMock())
        req = UpdateStatusRequest(qa_id=1, status="archived")
        request = MagicMock()
        request.headers.get.return_value = ""
        result = update_qa_status(req, request)
        assert result.status == "archived"
        call_kwargs = mock_mysql.insert_audit_log.call_args.kwargs
        assert call_kwargs["result"] == "reject"

    @patch("api.routes.get_business_config")
    def test_update_status_invalid(self, mock_cfg):
        mock_cfg.return_value = ["active", "deprecated", "archived"]
        set_mysql_client(MagicMock())
        req = UpdateStatusRequest(qa_id=1, status="invalid")
        with pytest.raises(HTTPException) as exc:
            update_qa_status(req, MagicMock())
        assert exc.value.status_code == 400

    def test_update_status_no_mysql(self):
        set_mysql_client(None)
        req = UpdateStatusRequest(qa_id=1, status="active")
        with pytest.raises(HTTPException) as exc:
            update_qa_status(req, MagicMock())
        assert exc.value.status_code == 500

    @patch("api.routes.get_business_config")
    def test_update_status_no_service(self, mock_cfg):
        mock_cfg.return_value = ["active", "deprecated", "archived"]
        set_mysql_client(MagicMock())
        set_service(None)
        req = UpdateStatusRequest(qa_id=1, status="deprecated")
        result = update_qa_status(req, MagicMock())
        assert result.status == "deprecated"


class TestCreateCategoryAPI:
    def test_create_category_success(self):
        mock_mysql = MagicMock()
        mock_mysql.create_category.return_value = 5
        set_mysql_client(mock_mysql)
        req = CategoryCreateRequest(label="新分类")
        result = create_category(req)
        assert result["id"] == 5
        assert result["message"] == "分类已创建"

    def test_create_category_no_mysql(self):
        set_mysql_client(None)
        req = CategoryCreateRequest(label="x")
        with pytest.raises(HTTPException) as exc:
            create_category(req)
        assert exc.value.status_code == 500


class TestUpdateCategoryAPI:
    def test_update_category_success(self):
        mock_mysql = MagicMock()
        mock_mysql.update_category.return_value = True
        mock_mysql.get_category_by_id.return_value = {"id": 1, "label": "改后", "parent_id": None, "description": ""}
        set_mysql_client(mock_mysql)
        req = CategoryUpdateRequest(label="改后")
        result = update_category(1, req)
        assert result["id"] == 1
        assert result["message"] == "分类已更新"

    def test_update_category_not_found(self):
        mock_mysql = MagicMock()
        mock_mysql.update_category.return_value = False
        mock_mysql.get_category_by_id.return_value = None
        set_mysql_client(mock_mysql)
        req = CategoryUpdateRequest(label="x")
        with pytest.raises(HTTPException) as exc:
            update_category(999, req)
        assert exc.value.status_code == 404

    def test_update_category_no_mysql(self):
        set_mysql_client(None)
        req = CategoryUpdateRequest(label="x")
        with pytest.raises(HTTPException) as exc:
            update_category(1, req)
        assert exc.value.status_code == 500


class TestDeleteCategoryAPI:
    def test_delete_category_success(self):
        mock_mysql = MagicMock()
        mock_mysql.delete_category.return_value = True
        mock_mysql.get_category_by_id.return_value = {"id": 1, "label": "测试", "parent_id": None, "description": ""}
        mock_mysql.count_qa_by_category.return_value = 0
        set_mysql_client(mock_mysql)
        result = delete_category(1)
        assert result["id"] == 1
        assert result["message"] == "分类已删除"

    def test_delete_category_not_found(self):
        mock_mysql = MagicMock()
        mock_mysql.delete_category.return_value = False
        mock_mysql.get_category_by_id.return_value = None
        set_mysql_client(mock_mysql)
        with pytest.raises(HTTPException) as exc:
            delete_category(999)
        assert exc.value.status_code == 404

    def test_delete_category_no_mysql(self):
        set_mysql_client(None)
        with pytest.raises(HTTPException) as exc:
            delete_category(1)
        assert exc.value.status_code == 500


class TestAuditHistoryAPI:
    def test_audit_history_success(self):
        mock_mysql = MagicMock()
        mock_mysql.get_audit_history.return_value = {
            "items": [
                {
                    "id": 1,
                    "qa_id": 10,
                    "question": "q",
                    "answer": "a",
                    "result": "pass",
                    "operator": "admin",
                    "created_at": "2024-01-01",
                }
            ],
            "total": 1,
            "page": 1,
            "page_size": 20,
        }
        set_mysql_client(mock_mysql)
        result = audit_history(page=1, page_size=20)
        assert result.total == 1
        assert len(result.items) == 1
        assert result.items[0].operator == "admin"

    def test_audit_history_no_mysql(self):
        set_mysql_client(None)
        with pytest.raises(HTTPException) as exc:
            audit_history()
        assert exc.value.status_code == 500


class TestStatsTrendAPI:
    def test_stats_trend_success(self):
        today = datetime.now().strftime("%Y-%m-%d")
        mock_mysql = MagicMock()
        mock_mysql.get_trend.return_value = {"items": [{"d": today, "cnt": 3}]}
        mock_mysql.get_qa_trend.return_value = {"items": [{"d": today, "cnt": 1}]}
        set_mysql_client(mock_mysql)
        result = stats_trend(days=7)
        assert len(result.dates) == 7
        assert len(result.work_order_counts) == 7
        assert len(result.qa_new_counts) == 7
        assert result.work_order_counts[-1] == 3
        assert result.qa_new_counts[-1] == 1

    def test_stats_trend_no_mysql(self):
        set_mysql_client(None)
        with pytest.raises(HTTPException) as exc:
            stats_trend()
        assert exc.value.status_code == 500


class TestCreateWorkOrderAPI:
    def test_create_work_order_success(self):
        mock_mysql = MagicMock()
        mock_mysql.insert_work_order_full.return_value = 42
        set_mysql_client(mock_mysql)
        req = WorkOrderCreateRequest(next_dept="账单组", customer_name="张三", detail_desc="扣费异常")
        result = create_work_order(req)
        assert result.id == 42
        assert result.status == "submitted"
        assert result.dept == "账单组"
        assert result.customer_name == "张三"
        assert result.detail_desc == "扣费异常"
        mock_mysql.insert_work_order_full.assert_called_once()

    def test_create_work_order_no_mysql(self):
        set_mysql_client(None)
        req = WorkOrderCreateRequest()
        with pytest.raises(HTTPException) as exc:
            create_work_order(req)
        assert exc.value.status_code == 500


class TestGetWorkOrderAPI:
    def test_get_work_order_success(self):
        mock_mysql = MagicMock()
        mock_mysql.get_work_order_detail.return_value = {
            "id": 1,
            "external_id": "WO1",
            "raw_data": '{"service_id":"s1","customer_name":"张三"}',
            "status": "submitted",
            "dept": "账单组",
        }
        set_mysql_client(mock_mysql)
        result = get_work_order(1)
        assert result.id == 1
        assert result.customer_name == "张三"

    def test_get_work_order_not_found(self):
        mock_mysql = MagicMock()
        mock_mysql.get_work_order_detail.return_value = None
        set_mysql_client(mock_mysql)
        with pytest.raises(HTTPException) as exc:
            get_work_order(999)
        assert exc.value.status_code == 404

    def test_get_work_order_no_mysql(self):
        set_mysql_client(None)
        with pytest.raises(HTTPException) as exc:
            get_work_order(1)
        assert exc.value.status_code == 500


class TestReplyWorkOrderAPI:
    def test_reply_work_order_success_with_back_dept(self):
        mock_mysql = MagicMock()
        mock_mysql.get_work_order_detail.side_effect = [
            {"id": 1, "external_id": "WO1", "raw_data": "{}", "status": "submitted", "dept": "账单组"},
            {
                "id": 1,
                "external_id": "WO1",
                "raw_data": '{"handle_remark":"已处理","back_dept":"客服组"}',
                "status": "answered",
                "dept": "账单组",
            },
        ]
        set_mysql_client(mock_mysql)
        req = WorkOrderReplyRequest(handle_remark="已处理", back_dept="客服组")
        result = reply_work_order(1, req)
        assert result.id == 1
        assert result.status == "answered"
        mock_mysql.update_work_order_reply.assert_called_once()
        call_args = mock_mysql.update_work_order_reply.call_args
        assert call_args.args[0] == 1
        assert call_args.args[2] == "answered"

    def test_reply_work_order_success_no_back_dept(self):
        mock_mysql = MagicMock()
        mock_mysql.get_work_order_detail.side_effect = [
            {"id": 1, "raw_data": "{}", "status": "submitted", "dept": "账单组"},
            {"id": 1, "raw_data": '{"handle_remark":"ok"}', "status": "answered", "dept": "账单组"},
        ]
        set_mysql_client(mock_mysql)
        req = WorkOrderReplyRequest(handle_remark="ok")
        result = reply_work_order(1, req)
        assert result.id == 1
        mock_mysql.update_work_order_reply.assert_called_once()

    def test_reply_work_order_not_found(self):
        mock_mysql = MagicMock()
        mock_mysql.get_work_order_detail.return_value = None
        set_mysql_client(mock_mysql)
        req = WorkOrderReplyRequest(handle_remark="x")
        with pytest.raises(HTTPException) as exc:
            reply_work_order(999, req)
        assert exc.value.status_code == 404

    def test_reply_work_order_no_mysql(self):
        set_mysql_client(None)
        req = WorkOrderReplyRequest(handle_remark="x")
        with pytest.raises(HTTPException) as exc:
            reply_work_order(1, req)
        assert exc.value.status_code == 500


class TestASRQueryAPI:
    def _make_file(self, filename="test.wav", content=b"audio"):
        f = MagicMock()
        f.filename = filename
        f.read = AsyncMock(return_value=content)
        return f

    @patch("api.routes.get_asr_service")
    def test_asr_query_success(self, mock_get):
        mock_asr = MagicMock()
        mock_asr._enabled = True
        mock_asr.transcribe.return_value = ASRResponse(text="ETC扣费", confidence=0.9)
        mock_get.return_value = mock_asr
        mock_service = MagicMock()
        mock_service.query.return_value = MagicMock(
            query="ETC扣费",
            standardized_query="ETC",
            confidence="high",
            candidates=[],
            total_candidates=0,
        )
        set_service(mock_service)
        result = asyncio.run(asr_query(self._make_file(), "账单问题", user={"sub": "test"}))
        assert result.asr_text == "ETC扣费"
        assert result.query == "ETC扣费"
        assert result.confidence == "high"
        mock_service.query.assert_called_once_with("ETC扣费", "账单问题")

    @patch("api.routes.get_asr_service")
    def test_asr_query_empty_text(self, mock_get):
        mock_asr = MagicMock()
        mock_asr._enabled = True
        mock_asr.transcribe.return_value = ASRResponse(text="   ", confidence=0.5)
        mock_get.return_value = mock_asr
        set_service(MagicMock())
        result = asyncio.run(asr_query(self._make_file(), user={"sub": "test"}))
        assert result.asr_text == ""
        assert result.query == ""

    @patch("api.routes.get_asr_service")
    def test_asr_query_disabled(self, mock_get):
        mock_asr = MagicMock()
        mock_asr._enabled = False
        mock_get.return_value = mock_asr
        with pytest.raises(HTTPException) as exc:
            asyncio.run(asr_query(self._make_file(), user={"sub": "test"}))
        assert exc.value.status_code == 503

    @patch("api.routes.get_asr_service")
    def test_asr_query_no_service(self, mock_get):
        mock_asr = MagicMock()
        mock_asr._enabled = True
        mock_get.return_value = mock_asr
        set_service(None)
        with pytest.raises(HTTPException) as exc:
            asyncio.run(asr_query(self._make_file(), user={"sub": "test"}))
        assert exc.value.status_code == 500

    @patch("api.routes.get_asr_service")
    def test_asr_query_file_not_found(self, mock_get):
        mock_asr = MagicMock()
        mock_asr._enabled = True
        mock_asr.transcribe.side_effect = FileNotFoundError("missing file")
        mock_get.return_value = mock_asr
        set_service(MagicMock())
        with pytest.raises(HTTPException) as exc:
            asyncio.run(asr_query(self._make_file(), user={"sub": "test"}))
        assert exc.value.status_code == 404

    @patch("api.routes.get_asr_service")
    def test_asr_query_runtime_error(self, mock_get):
        mock_asr = MagicMock()
        mock_asr._enabled = True
        mock_asr.transcribe.side_effect = RuntimeError("model err")
        mock_get.return_value = mock_asr
        set_service(MagicMock())
        with pytest.raises(HTTPException) as exc:
            asyncio.run(asr_query(self._make_file(), user={"sub": "test"}))
        assert exc.value.status_code == 503

    @patch("api.routes.get_asr_service")
    def test_asr_query_generic_error(self, mock_get):
        mock_asr = MagicMock()
        mock_asr._enabled = True
        mock_asr.transcribe.side_effect = ValueError("boom")
        mock_get.return_value = mock_asr
        set_service(MagicMock())
        with pytest.raises(HTTPException) as exc:
            asyncio.run(asr_query(self._make_file(), user={"sub": "test"}))
        assert exc.value.status_code == 500


class TestUserAPI:
    MOCK_SUPER = {"sub": "superadmin", "role": "superadmin"}

    def test_list_users(self):
        mock_mysql = MagicMock()
        mock_mysql.list_users.return_value = {
            "items": [
                {
                    "id": 1,
                    "username": "admin",
                    "role": "admin",
                    "dept": "",
                    "status": "active",
                    "created_at": "2024-01-01",
                    "updated_at": "2024-01-01",
                }
            ],
            "total": 1,
            "page": 1,
            "page_size": 20,
        }
        set_mysql_client(mock_mysql)
        result = list_users(page=1, page_size=20)
        assert result.total == 1
        assert result.items[0].username == "admin"

    def test_list_users_no_service(self):
        set_mysql_client(None)
        with pytest.raises(HTTPException) as exc:
            list_users()
        assert exc.value.status_code == 500

    def test_create_user_success(self):
        mock_mysql = MagicMock()
        mock_mysql.get_user_by_username.return_value = None
        mock_mysql.list_roles.return_value = [{"role_key": "admin"}, {"role_key": "service"}]
        mock_mysql.create_user.return_value = 10
        set_mysql_client(mock_mysql)
        with patch("api.routes.hash_password", return_value="hashed"):
            req = UserCreateRequest(username="newuser", password="pw123456", role="admin")
            result = create_user(req, self.MOCK_SUPER)
        assert result["user_id"] == 10

    def test_create_user_duplicate(self):
        mock_mysql = MagicMock()
        mock_mysql.get_user_by_username.return_value = {"id": 1}
        set_mysql_client(mock_mysql)
        req = UserCreateRequest(username="admin", password="pw123456", role="admin")
        with pytest.raises(HTTPException) as exc:
            create_user(req, self.MOCK_SUPER)
        assert exc.value.status_code == 409

    def test_create_user_invalid_role(self):
        mock_mysql = MagicMock()
        mock_mysql.get_user_by_username.return_value = None
        mock_mysql.list_roles.return_value = [{"role_key": "admin"}]
        set_mysql_client(mock_mysql)
        req = UserCreateRequest(username="x", password="pw123456", role="superadmin")
        with pytest.raises(HTTPException) as exc:
            create_user(req, self.MOCK_SUPER)
        assert exc.value.status_code == 400

    def test_update_user_success(self):
        mock_mysql = MagicMock()
        mock_mysql.update_user.return_value = True
        set_mysql_client(mock_mysql)
        req = UserUpdateRequest(role="service", status="disabled")
        result = update_user(1, req, self.MOCK_SUPER)
        assert result["user_id"] == 1

    def test_update_user_not_found(self):
        mock_mysql = MagicMock()
        mock_mysql.update_user.return_value = False
        set_mysql_client(mock_mysql)
        req = UserUpdateRequest(role="service")
        with pytest.raises(HTTPException) as exc:
            update_user(99, req, self.MOCK_SUPER)
        assert exc.value.status_code == 404

    def test_reset_password_success(self):
        mock_mysql = MagicMock()
        mock_mysql.reset_password.return_value = True
        set_mysql_client(mock_mysql)
        with patch("api.routes.hash_password", return_value="hashed"):
            req = ResetPasswordRequest(user_id=1, new_password="newpw123")
            result = reset_password(1, req, self.MOCK_SUPER)
        assert result["user_id"] == 1

    def test_reset_password_id_mismatch(self):
        mock_mysql = MagicMock()
        set_mysql_client(mock_mysql)
        req = ResetPasswordRequest(user_id=2, new_password="newpw123")
        with pytest.raises(HTTPException) as exc:
            reset_password(1, req, self.MOCK_SUPER)
        assert exc.value.status_code == 400

    def test_delete_user_success(self):
        mock_mysql = MagicMock()
        mock_mysql.delete_user.return_value = True
        set_mysql_client(mock_mysql)
        result = delete_user(1, self.MOCK_SUPER)
        assert result["user_id"] == 1

    def test_delete_user_not_found(self):
        mock_mysql = MagicMock()
        mock_mysql.delete_user.return_value = False
        set_mysql_client(mock_mysql)
        with pytest.raises(HTTPException) as exc:
            delete_user(99, self.MOCK_SUPER)
        assert exc.value.status_code == 404


class TestRoleAPI:
    MOCK_SUPER = {"sub": "superadmin", "role": "superadmin"}

    def test_list_roles(self):
        mock_mysql = MagicMock()
        mock_mysql.list_roles.return_value = [
            {"id": 1, "role_key": "admin", "role_name": "管理员", "description": "全权限", "created_at": "2024-01-01"},
        ]
        set_mysql_client(mock_mysql)
        result = list_roles()
        assert len(result) == 1
        assert result[0].role_key == "admin"

    def test_list_roles_no_service(self):
        set_mysql_client(None)
        with pytest.raises(HTTPException) as exc:
            list_roles()
        assert exc.value.status_code == 500

    def test_create_role_success(self):
        mock_mysql = MagicMock()
        mock_mysql.create_role.return_value = 5
        set_mysql_client(mock_mysql)
        req = RoleCreateRequest(role_key="viewer", role_name="只读用户")
        result = create_role(req, self.MOCK_SUPER)
        assert result["role_id"] == 5

    def test_create_role_duplicate(self):
        mock_mysql = MagicMock()
        mock_mysql.create_role.side_effect = Exception("Duplicate entry")
        set_mysql_client(mock_mysql)
        req = RoleCreateRequest(role_key="admin", role_name="管理员")
        with pytest.raises(HTTPException) as exc:
            create_role(req, self.MOCK_SUPER)
        assert exc.value.status_code == 409

    def test_update_role_success(self):
        mock_mysql = MagicMock()
        mock_mysql.update_role.return_value = True
        set_mysql_client(mock_mysql)
        req = RoleUpdateRequest(role_name="超级管理员")
        result = update_role(1, req, self.MOCK_SUPER)
        assert result["role_id"] == 1

    def test_update_role_not_found(self):
        mock_mysql = MagicMock()
        mock_mysql.update_role.return_value = False
        set_mysql_client(mock_mysql)
        req = RoleUpdateRequest(role_name="x")
        with pytest.raises(HTTPException) as exc:
            update_role(99, req, self.MOCK_SUPER)
        assert exc.value.status_code == 404

    def test_delete_role_success(self):
        mock_mysql = MagicMock()
        mock_mysql.delete_role.return_value = True
        set_mysql_client(mock_mysql)
        result = delete_role(1, self.MOCK_SUPER)
        assert result["role_id"] == 1

    def test_delete_role_not_found(self):
        mock_mysql = MagicMock()
        mock_mysql.delete_role.return_value = False
        set_mysql_client(mock_mysql)
        with pytest.raises(HTTPException) as exc:
            delete_role(99, self.MOCK_SUPER)
        assert exc.value.status_code == 404
