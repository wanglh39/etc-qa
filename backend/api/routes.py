import json
import os
import random
import tempfile
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile

from agent.graph import ingest_agent
from agent.state import AgentState
from api.work_order.client import WorkOrderClient
from asr.models import ASRHealthResponse, ASRResponse
from asr.service import get_asr_service
from db.mysql_client import MySQLClient
from models.schemas import (
    AddQARequest,
    AddQAResponse,
    AgentProcessRequest,
    AgentProcessResponse,
    ASRQueryResponse,
    AuditLogItem,
    AuditLogListResponse,
    CategoryCreateRequest,
    CategoryUpdateRequest,
    OperationLogItem,
    OperationLogListResponse,
    QADetailResponse,
    QAListItem,
    QAListResponse,
    QASearchRequest,
    QASearchResponse,
    QueryRequest,
    QueryResponse,
    ResetPasswordRequest,
    RoleCreateRequest,
    RoleItem,
    RoleUpdateRequest,
    StatsResponse,
    TrendResponse,
    UpdateQARequest,
    UpdateQAResponse,
    UpdateStatusRequest,
    UpdateStatusResponse,
    UserCreateRequest,
    UserListItem,
    UserListResponse,
    UserUpdateRequest,
    WorkOrderCreateRequest,
    WorkOrderDetailResponse,
    WorkOrderListItem,
    WorkOrderListResponse,
    WorkOrderReplyRequest,
)
from rag.service import QAService
from utils.auth_middleware import get_current_user, require_role
from utils.config_center import get_business_config, invalidate_cache
from utils.logger import get_logger
from utils.password import hash_password
from utils.rate_limit import limiter

logger = get_logger("api.routes")

router = APIRouter(dependencies=[Depends(get_current_user)])
service: QAService = None
work_order_client: WorkOrderClient = None
mysql_client: MySQLClient = None
scheduler_manager = None


@router.get("/health")
def health_check():
    return {"status": "ok"}


def _serialize_row(row: dict) -> dict:
    result = {}
    for k, v in row.items():
        if isinstance(v, datetime):
            result[k] = v.strftime("%Y-%m-%d %H:%M:%S")
        else:
            result[k] = v
    return result


def set_service(s: QAService):
    global service
    service = s


def set_work_order_client(client: WorkOrderClient):
    global work_order_client
    work_order_client = client


def set_mysql_client(client: MySQLClient):
    global mysql_client
    mysql_client = client


def set_scheduler_manager(mgr):
    global scheduler_manager
    scheduler_manager = mgr


def _current_operator(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            from utils.jwt_utils import verify_token

            payload = verify_token(auth[7:])
            return payload.get("sub", "admin")
        except Exception:
            pass
    return "admin"


def _parse_raw_data(raw_data: str | None) -> dict:
    if not raw_data:
        return {}
    try:
        parsed = json.loads(raw_data)
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


_SECRET_KEY_FRAGMENTS = ("api_key", "password", "secret", "token", "access_key")


def _redact_secrets(obj):
    if isinstance(obj, dict):
        return {
            k: ("***" if any(f in str(k).lower() for f in _SECRET_KEY_FRAGMENTS) else _redact_secrets(v))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_redact_secrets(v) for v in obj]
    return obj


def _fmt_dt(v) -> str | None:
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    return str(v) if v else None


def _work_order_to_detail(row: dict) -> WorkOrderDetailResponse:
    data = _parse_raw_data(row.get("raw_data"))
    return WorkOrderDetailResponse(
        id=row["id"],
        external_id=row.get("external_id", ""),
        status=row.get("status", ""),
        dept=row.get("dept", ""),
        service_id=data.get("service_id", ""),
        customer_name=data.get("customer_name", ""),
        phone=data.get("phone", ""),
        problem_type=data.get("problem_type", ""),
        next_dept=data.get("next_dept", ""),
        return_dept=data.get("return_dept", ""),
        receive_user=data.get("receive_user", ""),
        priority=data.get("priority", ""),
        detail_desc=data.get("detail_desc", ""),
        handle_remark=data.get("handle_remark", ""),
        created_at=_fmt_dt(row.get("created_at")),
        updated_at=_fmt_dt(row.get("updated_at")),
    )


def _build_category_tree() -> list[dict]:
    nodes: list[dict] = []
    rows = mysql_client.list_categories()
    existing_labels: set[str] = set()
    for r in rows:
        nodes.append(
            {
                "id": r["id"],
                "label": r["label"],
                "parentId": r.get("parent_id"),
                "description": r.get("description") or "",
            }
        )
        existing_labels.add(r["label"])

    derived = mysql_client.get_category_tree()
    next_id = 100000
    label_to_id: dict[str, int] = {n["label"]: n["id"] for n in nodes}
    for l1, l2_list in derived.items():
        if not l1:
            continue
        if l1 not in label_to_id:
            parent_id = next_id
            next_id += 1
            nodes.append({"id": parent_id, "label": l1, "parentId": None, "description": ""})
            label_to_id[l1] = parent_id
        else:
            parent_id = label_to_id[l1]
        existing_children = {n["label"] for n in nodes if n.get("parentId") == parent_id}
        for l2 in l2_list:
            if l2 and l2 not in existing_children:
                nodes.append({"id": next_id, "label": l2, "parentId": parent_id, "description": ""})
                next_id += 1
                existing_children.add(l2)

    children_map: dict = {}
    for n in nodes:
        n["children"] = []
        children_map.setdefault(n["parentId"], []).append(n)
    for n in nodes:
        n["children"] = children_map.get(n["id"], [])
    return [n for n in nodes if n["parentId"] is None]


@router.post("/query", response_model=QueryResponse)
def query_qa(req: QueryRequest, user: dict = Depends(get_current_user)):
    if not limiter.check(f"query:{user.get('sub')}", 30, 60):
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")
    if service is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    result = service.query(req.question, req.category_l1)
    return result


@router.post("/add", response_model=AddQAResponse, dependencies=[Depends(require_role("admin", "superadmin", page="/workbench/admin/knowledge"))])
def add_qa(req: AddQARequest):
    if service is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    qa_id = service.add_knowledge(req)
    return AddQAResponse(qa_id=qa_id, message="添加成功，索引已更新")


@router.post("/agent/process", response_model=AgentProcessResponse)
def agent_process(req: AgentProcessRequest, user: dict = Depends(get_current_user)):
    if not limiter.check(f"agent:{user.get('sub')}", 20, 60):
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")
    initial_state = AgentState(
        raw_question=req.question,
        raw_answer=req.answer or "",
        raw_context=req.context or "",
        user_id=req.user_id,
    )
    result = ingest_agent.invoke(initial_state.model_dump())
    return AgentProcessResponse(
        question=result.get("question", ""),
        answer=result.get("answer", ""),
        internal_process=result.get("internal_process", ""),
        feedback_dept=result.get("feedback_dept", ""),
        is_duplicate=result.get("is_duplicate", False),
        duplicate_of=result.get("duplicate_of"),
        similarity_score=result.get("similarity_score", 0.0),
        category_l1=result.get("category_l1", ""),
        category_l2=result.get("category_l2", ""),
        category_confidence=result.get("category_confidence", 0.0),
        needs_review=result.get("needs_review", False),
        review_highlights=result.get("review_highlights", []),
        current_step=result.get("current_step", ""),
        error=result.get("error"),
    )


@router.put(
    "/qa/status", response_model=UpdateStatusResponse, dependencies=[Depends(require_role("admin", "superadmin", page="/workbench/admin/knowledge"))]
)
def update_qa_status(req: UpdateStatusRequest, request: Request):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    valid_statuses = get_business_config("qa_statuses", ["active", "deprecated", "archived"])
    if req.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"status必须是{valid_statuses}之一")
    if req.status == "active" and service is not None:
        service.activate_qa(req.qa_id)
        mysql_client.update_qa_status(req.qa_id, req.status)
    elif service is not None:
        service.deactivate_qa(req.qa_id)
        mysql_client.update_qa_status(req.qa_id, req.status)
    else:
        mysql_client.update_qa_status(req.qa_id, req.status)
    if req.status in ("active", "archived"):
        detail = mysql_client.get_qa_detail(req.qa_id) or {}
        mysql_client.insert_audit_log(
            qa_id=req.qa_id,
            question=detail.get("question", ""),
            answer=detail.get("answer", ""),
            result="pass" if req.status == "active" else "reject",
            operator=_current_operator(request),
        )
    return UpdateStatusResponse(qa_id=req.qa_id, status=req.status, message=f"状态已更新为{req.status}")


@router.put("/config/{key}", dependencies=[Depends(require_role("admin", "superadmin", page="/workbench/admin/config"))])
def update_config(key: str, value: dict):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    mysql_client.set_config(key, value.get("value"), value.get("description", ""))
    invalidate_cache(key)
    return {"key": key, "message": "配置已更新，缓存已刷新"}


@router.get("/config/{key}", dependencies=[Depends(require_role("admin", "superadmin", page="/workbench/admin/config"))])
def get_config_value(key: str):
    result = get_business_config(key)
    return {"key": key, "value": _redact_secrets(result)}


@router.post("/config/reload", dependencies=[Depends(require_role("admin", "superadmin", page="/workbench/admin/config"))])
def reload_config():
    invalidate_cache()
    return {"message": "所有配置缓存已刷新，将从DB重新加载"}


@router.get("/qa/list", response_model=QAListResponse)
def list_qa(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category_l1: str | None = None,
    status: str | None = None,
):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    result = mysql_client.get_qa_list(page=page, page_size=page_size, category_l1=category_l1, status=status)
    items = [QAListItem(**_serialize_row(row)) for row in result["items"]]
    return QAListResponse(items=items, total=result["total"], page=result["page"], page_size=result["page_size"])


@router.get("/qa/{qa_id}", response_model=QADetailResponse)
def get_qa_detail(qa_id: int):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    row = mysql_client.get_qa_detail(qa_id)
    if row is None:
        raise HTTPException(status_code=404, detail="QA不存在")
    return QADetailResponse(**_serialize_row(row))


@router.delete("/qa/{qa_id}", dependencies=[Depends(require_role("admin", "superadmin", page="/workbench/admin/knowledge"))])
def delete_qa(qa_id: int):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    if service is not None:
        service.deactivate_qa(qa_id)
    deleted = mysql_client.delete_qa(qa_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="QA不存在")
    return {"qa_id": qa_id, "message": "已删除"}


@router.put("/qa/{qa_id}", response_model=UpdateQAResponse, dependencies=[Depends(require_role("admin", "superadmin", page="/workbench/admin/knowledge"))])
def update_qa(qa_id: int, req: UpdateQARequest):
    if service is None or mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    try:
        service.update_qa(qa_id, req)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return UpdateQAResponse(qa_id=qa_id, message="编辑成功")


@router.post("/qa/search", response_model=QASearchResponse)
def search_qa(req: QASearchRequest):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    result = mysql_client.search_qa(
        keyword=req.keyword, page=req.page, page_size=req.page_size, category_l1=req.category_l1, status=req.status
    )
    items = [QAListItem(**_serialize_row(row)) for row in result["items"]]
    return QASearchResponse(items=items, total=result["total"], page=result["page"], page_size=result["page_size"])


@router.get("/stats", response_model=StatsResponse, dependencies=[Depends(require_role("admin", "superadmin", "ops", page="/workbench/admin/dashboard"))])
def get_stats():
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    qa_counts = mysql_client.count_qa()
    wo_counts = mysql_client.count_work_orders()
    category_stats = mysql_client.get_category_stats()
    return StatsResponse(
        qa_total=qa_counts.get("total", 0),
        qa_active=qa_counts.get("active", 0),
        qa_deprecated=qa_counts.get("deprecated", 0),
        qa_archived=qa_counts.get("archived", 0),
        work_order_total=wo_counts.get("total", 0),
        work_order_submitted=wo_counts.get("submitted", 0),
        work_order_processed=wo_counts.get("processed", 0),
        category_stats=category_stats if isinstance(category_stats, dict) else {},
    )


@router.get("/categories")
def get_categories():
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    return {"categories": _build_category_tree()}


@router.post("/categories", dependencies=[Depends(require_role("admin", "superadmin", page="/workbench/admin/category"))])
def create_category(req: CategoryCreateRequest):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    cat_id = mysql_client.create_category(req.label, req.parent_id, req.description)
    return {"id": cat_id, "message": "分类已创建"}


@router.put("/categories/{cat_id}", dependencies=[Depends(require_role("admin", "superadmin", page="/workbench/admin/category"))])
def update_category(cat_id: int, req: CategoryUpdateRequest):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    updated = mysql_client.update_category(cat_id, req.label, req.parent_id, req.description)
    if not updated:
        raise HTTPException(status_code=404, detail="分类不存在")
    return {"id": cat_id, "message": "分类已更新"}


@router.delete("/categories/{cat_id}", dependencies=[Depends(require_role("admin", "superadmin", page="/workbench/admin/category"))])
def delete_category(cat_id: int):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    deleted = mysql_client.delete_category(cat_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="分类不存在")
    return {"id": cat_id, "message": "分类已删除"}


@router.get(
    "/audit/history", response_model=AuditLogListResponse, dependencies=[Depends(require_role("admin", "superadmin", page="/workbench/admin/auditHistory"))]
)
def audit_history(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    result = mysql_client.get_audit_history(page=page, page_size=page_size)
    items = [AuditLogItem(**_serialize_row(row)) for row in result["items"]]
    return AuditLogListResponse(items=items, total=result["total"], page=result["page"], page_size=result["page_size"])


@router.get(
    "/stats/trend", response_model=TrendResponse, dependencies=[Depends(require_role("admin", "superadmin", "ops", page="/workbench/admin/dashboard"))]
)
def stats_trend(days: int = Query(7, ge=1, le=90)):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    dates = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days - 1, -1, -1)]

    wo_rows = mysql_client.get_trend(days)
    wo_by_date = {str(r["d"]): r["cnt"] for r in wo_rows["items"]}
    work_order_counts = [wo_by_date.get(d, 0) for d in dates]

    qa_rows = mysql_client.get_qa_trend(days)
    qa_by_date = {str(r["d"]): r["cnt"] for r in qa_rows["items"]}
    qa_new_counts = [qa_by_date.get(d, 0) for d in dates]

    return TrendResponse(dates=dates, work_order_counts=work_order_counts, qa_new_counts=qa_new_counts)


@router.get("/depts")
def list_depts():
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    rows = mysql_client.get_all_depts()
    return [{"dept_key": r["dept_key"], "dept_name": r["dept_name"]} for r in rows]


@router.get("/work_orders", response_model=WorkOrderListResponse)
def list_work_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    dept: str | None = None,
):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    result = mysql_client.get_work_order_list(page=page, page_size=page_size, status=status, dept=dept)
    items = [WorkOrderListItem(**_serialize_row(row)) for row in result["items"]]
    return WorkOrderListResponse(items=items, total=result["total"], page=result["page"], page_size=result["page_size"])


@router.get("/work_orders/stats")
def get_work_order_stats(dept: str | None = None):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    if dept:
        return mysql_client.count_work_orders_by_dept(dept)
    return mysql_client.count_work_orders()


@router.post("/work_orders", response_model=WorkOrderDetailResponse)
def create_work_order(req: WorkOrderCreateRequest):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    external_id = f"WO-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
    raw_data = json.dumps(req.model_dump(), ensure_ascii=False)
    wo_id = mysql_client.insert_work_order_full(external_id, req.next_dept, raw_data)
    return _work_order_to_detail(
        {
            "id": wo_id,
            "external_id": external_id,
            "raw_data": raw_data,
            "status": "submitted",
            "dept": req.next_dept,
        }
    )


@router.get("/work_orders/{wo_id}", response_model=WorkOrderDetailResponse)
def get_work_order(wo_id: int):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    row = mysql_client.get_work_order_detail(wo_id)
    if row is None:
        raise HTTPException(status_code=404, detail="工单不存在")
    return _work_order_to_detail(row)


@router.put("/work_orders/{wo_id}/reply", response_model=WorkOrderDetailResponse)
def reply_work_order(wo_id: int, req: WorkOrderReplyRequest):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    row = mysql_client.get_work_order_detail(wo_id)
    if row is None:
        raise HTTPException(status_code=404, detail="工单不存在")
    data = _parse_raw_data(row.get("raw_data"))
    data["handle_remark"] = req.handle_remark
    if req.back_dept:
        data["back_dept"] = req.back_dept
    mysql_client.update_work_order_reply(wo_id, json.dumps(data, ensure_ascii=False), "answered")
    updated = mysql_client.get_work_order_detail(wo_id)
    return _work_order_to_detail(updated)


@router.post("/asr", response_model=ASRResponse)
async def asr_transcribe(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    if not limiter.check(f"asr:{user.get('sub')}", 10, 60):
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")
    asr_service = get_asr_service()
    if not asr_service._enabled:
        raise HTTPException(status_code=503, detail="ASR未启用")

    suffix = os.path.splitext(file.filename)[1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = asr_service.transcribe(tmp_path)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"ASR识别失败: {e}")
        raise HTTPException(status_code=500, detail=f"ASR识别失败: {e!s}")
    finally:
        os.unlink(tmp_path)


@router.get("/asr/health", response_model=ASRHealthResponse)
def asr_health():
    asr_service = get_asr_service()
    return asr_service.health()


@router.post("/asr/query", response_model=ASRQueryResponse)
async def asr_query(
    file: UploadFile = File(...), category_l1: str | None = None, user: dict = Depends(get_current_user)
):
    if not limiter.check(f"asr_query:{user.get('sub')}", 10, 60):
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")
    asr_service = get_asr_service()
    if not asr_service._enabled:
        raise HTTPException(status_code=503, detail="ASR未启用")
    if service is None:
        raise HTTPException(status_code=500, detail="RAG服务未初始化")

    suffix = os.path.splitext(file.filename)[1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        asr_result = asr_service.transcribe(tmp_path)

        if not asr_result.text.strip():
            return ASRQueryResponse(
                asr_text="",
                asr_confidence=asr_result.confidence,
                asr_duration_ms=asr_result.duration_ms,
                asr_model=asr_result.model,
                asr_language=asr_result.language,
                asr_segments=[s.model_dump() for s in asr_result.segments],
            )

        rag_result = service.query(asr_result.text, category_l1)

        return ASRQueryResponse(
            asr_text=asr_result.text,
            asr_confidence=asr_result.confidence,
            asr_duration_ms=asr_result.duration_ms,
            asr_model=asr_result.model,
            asr_language=asr_result.language,
            asr_segments=[s.model_dump() for s in asr_result.segments],
            query=rag_result.query,
            standardized_query=rag_result.standardized_query,
            confidence=rag_result.confidence,
            candidates=rag_result.candidates,
            total_candidates=rag_result.total_candidates,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"ASR+检索失败: {e}")
        raise HTTPException(status_code=500, detail=f"ASR+检索失败: {e!s}")
    finally:
        os.unlink(tmp_path)


@router.get("/users", response_model=UserListResponse, dependencies=[Depends(require_role("superadmin", page="/workbench/admin/account"))])
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=999),
    role: str | None = None,
    status: str | None = None,
):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    result = mysql_client.list_users(page=page, page_size=page_size, role=role, status=status)
    items = [UserListItem(**_serialize_row(row)) for row in result["items"]]
    return UserListResponse(items=items, total=result["total"], page=result["page"], page_size=result["page_size"])


@router.post("/users")
def create_user(req: UserCreateRequest, user: dict = Depends(require_role("superadmin", page="/workbench/admin/account"))):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    existing = mysql_client.get_user_by_username(req.username)
    if existing:
        raise HTTPException(status_code=409, detail="用户名已存在")
    valid_roles = [r["role_key"] for r in mysql_client.list_roles()]
    if req.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"角色不存在，可选: {valid_roles}")
    user_id = mysql_client.create_user(req.username, hash_password(req.password), req.role, req.dept, req.status)
    mysql_client.insert_operation_log(
        user["sub"], "create", "user", user_id, f"创建账号 {req.username} 角色={req.role}"
    )
    return {"user_id": user_id, "message": "账号创建成功"}


@router.put("/users/{user_id}")
def update_user(user_id: int, req: UserUpdateRequest, user: dict = Depends(require_role("superadmin", page="/workbench/admin/account"))):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    ok = mysql_client.update_user(user_id, role=req.role, dept=req.dept, status=req.status)
    if not ok:
        raise HTTPException(status_code=404, detail="用户不存在或无更新字段")
    mysql_client.insert_operation_log(
        user["sub"], "update", "user", user_id, f"修改账号 role={req.role} status={req.status}"
    )
    return {"user_id": user_id, "message": "账号已更新"}


@router.put("/users/{user_id}/password")
def reset_password(user_id: int, req: ResetPasswordRequest, user: dict = Depends(require_role("superadmin", page="/workbench/admin/account"))):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    if user_id != req.user_id:
        raise HTTPException(status_code=400, detail="user_id不一致")
    ok = mysql_client.reset_password(user_id, hash_password(req.new_password))
    if not ok:
        raise HTTPException(status_code=404, detail="用户不存在")
    mysql_client.insert_operation_log(user["sub"], "reset_password", "user", user_id, "重置密码")
    return {"user_id": user_id, "message": "密码已重置"}


@router.delete("/users/{user_id}")
def delete_user(user_id: int, user: dict = Depends(require_role("superadmin", page="/workbench/admin/account"))):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    ok = mysql_client.delete_user(user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="用户不存在")
    mysql_client.insert_operation_log(user["sub"], "delete", "user", user_id, "删除账号")
    return {"user_id": user_id, "message": "账号已删除"}


@router.get("/roles/permissions")
def get_my_permissions(user: dict = Depends(get_current_user)):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    rows = mysql_client.list_roles()
    for row in rows:
        if row["role_key"] == user["role"]:
            perms = row.get("permissions") or []
            if isinstance(perms, str):
                import json as _json

                perms = _json.loads(perms)
            return {"permissions": perms}
    return {"permissions": []}


@router.get("/roles", response_model=list[RoleItem], dependencies=[Depends(require_role("superadmin", page="/workbench/admin/role"))])
def list_roles():
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    rows = mysql_client.list_roles()
    return [RoleItem(**_serialize_row(row)) for row in rows]


@router.post("/roles")
def create_role(req: RoleCreateRequest, user: dict = Depends(require_role("superadmin", page="/workbench/admin/role"))):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    try:
        role_id = mysql_client.create_role(req.role_key, req.role_name, req.description, req.permissions)
    except Exception as e:
        raise HTTPException(status_code=409, detail=f"角色key已存在: {e}")
    mysql_client.insert_operation_log(user["sub"], "create", "role", role_id, f"创建角色 {req.role_key}")
    return {"role_id": role_id, "message": "角色创建成功"}


@router.put("/roles/{role_id}")
def update_role(role_id: int, req: RoleUpdateRequest, user: dict = Depends(require_role("superadmin", page="/workbench/admin/role"))):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    ok = mysql_client.update_role(
        role_id, role_name=req.role_name, description=req.description, permissions=req.permissions
    )
    if not ok:
        raise HTTPException(status_code=404, detail="角色不存在或无更新字段")
    mysql_client.insert_operation_log(user["sub"], "update", "role", role_id, "修改角色")
    return {"role_id": role_id, "message": "角色已更新"}


@router.delete("/roles/{role_id}")
def delete_role(role_id: int, user: dict = Depends(require_role("superadmin", page="/workbench/admin/role"))):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    ok = mysql_client.delete_role(role_id)
    if not ok:
        raise HTTPException(status_code=404, detail="角色不存在")
    mysql_client.insert_operation_log(user["sub"], "delete", "role", role_id, "删除角色")
    return {"role_id": role_id, "message": "角色已删除"}


@router.get("/operations", response_model=OperationLogListResponse, dependencies=[Depends(require_role("superadmin", page="/workbench/admin/operationLog"))])
def list_operations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    operator: str | None = None,
    action: str | None = None,
):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    result = mysql_client.list_operation_logs(page=page, page_size=page_size, operator=operator, action=action)
    items = [OperationLogItem(**_serialize_row(row)) for row in result["items"]]
    return OperationLogListResponse(
        items=items, total=result["total"], page=result["page"], page_size=result["page_size"]
    )


@router.get("/scheduler/status", dependencies=[Depends(require_role("admin", "superadmin", "ops", page="/workbench/admin/scheduler"))])
def get_scheduler_status():
    if scheduler_manager is None:
        raise HTTPException(status_code=500, detail="调度器未初始化")
    return scheduler_manager.get_status()


@router.post("/scheduler/trigger/{job_id}", dependencies=[Depends(require_role("admin", "superadmin", "ops", page="/workbench/admin/scheduler"))])
def trigger_scheduler_job(job_id: str):
    if scheduler_manager is None:
        raise HTTPException(status_code=500, detail="调度器未初始化")
    result = scheduler_manager.trigger_job(job_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.put("/scheduler/config", dependencies=[Depends(require_role("superadmin", "ops", page="/workbench/admin/scheduler"))])
def update_scheduler_config(job_id: str = Query(...), hours: int = Query(None, ge=1), minutes: int = Query(None, ge=1)):
    if scheduler_manager is None:
        raise HTTPException(status_code=500, detail="调度器未初始化")
    result = scheduler_manager.update_job_schedule(job_id, hours=hours, minutes=minutes)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/scheduler/logs", dependencies=[Depends(require_role("admin", "superadmin", "ops", page="/workbench/admin/scheduler"))])
def get_scheduler_logs(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    result = mysql_client.get_scheduler_logs(page=page, page_size=page_size)
    return {
        "items": [_serialize_row(row) for row in result["items"]],
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
    }


@router.get("/alerts", dependencies=[Depends(require_role("admin", "superadmin", "ops", page="/workbench/admin/alert"))])
def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    severity: str | None = None,
):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    result = mysql_client.get_alert_events(page=page, page_size=page_size, status=status, severity=severity)
    return {
        "items": [_serialize_row(row) for row in result["items"]],
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
    }


@router.put("/alerts/{alert_id}/ack", dependencies=[Depends(require_role("admin", "superadmin", "ops", page="/workbench/admin/alert"))])
def ack_alert(alert_id: int, request: Request):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    auth = request.headers.get("Authorization", "")
    acked_by = "unknown"
    if auth.startswith("Bearer "):
        try:
            from utils.jwt_utils import verify_token

            payload = verify_token(auth[7:])
            acked_by = payload.get("sub", "unknown")
        except Exception:
            pass
    ok = mysql_client.ack_alert_event(alert_id, acked_by)
    if not ok:
        raise HTTPException(status_code=404, detail="告警不存在或已确认")
    return {"message": "告警已确认", "alert_id": alert_id}


@router.get("/alerts/metrics", dependencies=[Depends(require_role("admin", "superadmin", "ops", page="/workbench/admin/monitor"))])
def get_alert_metrics():
    from alert.monitor import get_all_metrics

    return get_all_metrics()


@router.get("/system/status", dependencies=[Depends(require_role("superadmin", "ops", page="/workbench/admin/status"))])
def get_system_status():
    import time

    components = []

    components.append({"name": "API服务", "status": "healthy", "latency_ms": 0, "detail": "FastAPI运行中"})

    try:
        start = time.time()
        conn = mysql_client._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        conn.close()
        latency = round((time.time() - start) * 1000, 1)
        components.append({"name": "MySQL", "status": "healthy", "latency_ms": latency, "detail": "连接正常"})
    except Exception as e:
        components.append({"name": "MySQL", "status": "unhealthy", "latency_ms": 0, "detail": str(e)[:100]})

    try:
        if service is not None and hasattr(service, "recall") and hasattr(service.recall, "milvus"):
            milvus = service.recall.milvus
            if milvus and milvus.client:
                start = time.time()
                milvus.client.list_collections()
                latency = round((time.time() - start) * 1000, 1)
                components.append({"name": "Milvus", "status": "healthy", "latency_ms": latency, "detail": "连接正常"})
            else:
                components.append({"name": "Milvus", "status": "unknown", "latency_ms": 0, "detail": "未初始化"})
        else:
            components.append({"name": "Milvus", "status": "unknown", "latency_ms": 0, "detail": "服务未加载"})
    except Exception as e:
        components.append({"name": "Milvus", "status": "unhealthy", "latency_ms": 0, "detail": str(e)[:100]})

    if service is not None:
        components.append({"name": "RAG服务", "status": "healthy", "latency_ms": 0, "detail": "QAService已加载"})
    else:
        components.append({"name": "RAG服务", "status": "unhealthy", "latency_ms": 0, "detail": "未初始化"})

    try:
        from asr.service import get_asr_service

        asr = get_asr_service()
        asr_h = asr.health()
        if asr_h.loaded:
            components.append(
                {"name": "ASR模型", "status": "healthy", "latency_ms": 0, "detail": f"已加载({asr_h.model})"}
            )
        else:
            components.append({"name": "ASR模型", "status": "standby", "latency_ms": 0, "detail": "未加载(按需启动)"})
    except Exception:
        components.append({"name": "ASR模型", "status": "standby", "latency_ms": 0, "detail": "未启用"})

    if scheduler_manager is not None:
        sched_status = scheduler_manager.get_status()
        components.append(
            {
                "name": "定时调度器",
                "status": "healthy" if sched_status.get("running") else "stopped",
                "latency_ms": 0,
                "detail": f"运行中{len(sched_status.get('jobs', []))}个任务"
                if sched_status.get("running")
                else "已停止",
            }
        )
    else:
        components.append({"name": "定时调度器", "status": "unhealthy", "latency_ms": 0, "detail": "未初始化"})

    try:
        from alert.monitor import get_all_metrics

        metrics = get_all_metrics()
        active_alerts = 0
        components.append(
            {"name": "告警监控", "status": "healthy", "latency_ms": 0, "detail": f"监控{len(metrics)}项指标"}
        )
    except Exception:
        components.append({"name": "告警监控", "status": "unhealthy", "latency_ms": 0, "detail": "异常"})

    healthy_count = sum(1 for c in components if c["status"] == "healthy")
    overall = "healthy" if healthy_count == len(components) else ("degraded" if healthy_count > 0 else "unhealthy")

    return {"overall": overall, "components": components, "timestamp": datetime.now().isoformat()}


@router.get("/system/logs", dependencies=[Depends(require_role("superadmin", "ops", page="/workbench/admin/status"))])
def get_system_logs(lines: int = Query(100, ge=1, le=500), level: str = Query(None)):
    log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs", "etc_qa.log")
    if not os.path.exists(log_path):
        return {"logs": [], "total": 0}

    try:
        with open(log_path, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
    except Exception as e:
        return {"logs": [], "total": 0, "error": str(e)}

    if level and level.upper() in ("ERROR", "WARNING", "INFO"):
        filtered = [l for l in all_lines if f"[{level.upper()}]" in l]
    else:
        filtered = all_lines

    recent = filtered[-lines:] if len(filtered) > lines else filtered
    result = []
    for line in recent:
        line = line.strip()
        if not line:
            continue
        log_level = "INFO"
        if "[ERROR]" in line:
            log_level = "ERROR"
        elif "[WARNING]" in line:
            log_level = "WARNING"
        elif "[INFO]" in line:
            log_level = "INFO"
        result.append({"line": line, "level": log_level})

    return {"logs": result, "total": len(result)}
