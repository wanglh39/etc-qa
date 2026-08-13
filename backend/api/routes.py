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
    AuditLogItem,
    AuditLogListResponse,
    CategoryCreateRequest,
    CategoryUpdateRequest,
    PromptKeySummary,
    PromptPublishRequest,
    PromptRollbackRequest,
    PromptShadowRequest,
    PromptVersionInfo,
    QADetailResponse,
    QAListItem,
    QAListResponse,
    QASearchRequest,
    QASearchResponse,
    QueryRequest,
    QueryResponse,
    StatsResponse,
    TrendResponse,
    UpdateStatusRequest,
    UpdateStatusResponse,
    WorkOrderCreateRequest,
    WorkOrderDetailResponse,
    WorkOrderListItem,
    WorkOrderListResponse,
    WorkOrderReplyRequest,
)
from prompt.shadow_recorder import get_shadow_records, get_shadow_stats
from prompt.version_manager import get_version_manager
from rag.service import QAService
from utils.auth_middleware import get_current_user, require_role
from utils.config_center import get_business_config, invalidate_cache
from utils.logger import get_logger

logger = get_logger("api.routes")

router = APIRouter(dependencies=[Depends(get_current_user)])
service: QAService = None
work_order_client: WorkOrderClient = None
mysql_client: MySQLClient = None


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
    if rows:
        for r in rows:
            nodes.append({
                "id": r["id"],
                "label": r["label"],
                "parentId": r.get("parent_id"),
                "description": r.get("description") or "",
            })
    else:
        derived = mysql_client.get_category_tree()
        next_id = 1
        for l1, l2_list in derived.items():
            if not l1:
                continue
            parent_id = next_id
            next_id += 1
            nodes.append({"id": parent_id, "label": l1, "parentId": None, "description": ""})
            for l2 in l2_list:
                nodes.append({"id": next_id, "label": l2, "parentId": parent_id, "description": ""})
                next_id += 1

    children_map: dict = {}
    for n in nodes:
        n["children"] = []
        children_map.setdefault(n["parentId"], []).append(n)
    for n in nodes:
        n["children"] = children_map.get(n["id"], [])
    return [n for n in nodes if n["parentId"] is None]


@router.post("/query", response_model=QueryResponse)
def query_qa(req: QueryRequest):
    if service is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    result = service.query(req.question, req.category_l1)
    return result


@router.post("/add", response_model=AddQAResponse, dependencies=[Depends(require_role("admin"))])
def add_qa(req: AddQARequest):
    if service is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    qa_id = service.add_knowledge(req)
    return AddQAResponse(qa_id=qa_id, message="添加成功，索引已更新")


@router.post("/agent/process", response_model=AgentProcessResponse)
def agent_process(req: AgentProcessRequest):
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


@router.put("/qa/status", response_model=UpdateStatusResponse, dependencies=[Depends(require_role("admin"))])
def update_qa_status(req: UpdateStatusRequest, request: Request):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    valid_statuses = get_business_config("qa_statuses", ["active", "deprecated", "archived"])
    if req.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"status必须是{valid_statuses}之一")
    mysql_client.update_qa_status(req.qa_id, req.status)
    if service is not None:
        service.invalidate_active_ids_cache()
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


@router.put("/config/{key}", dependencies=[Depends(require_role("admin"))])
def update_config(key: str, value: dict):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    mysql_client.set_config(key, value.get("value"), value.get("description", ""))
    invalidate_cache(key)
    return {"key": key, "message": "配置已更新，缓存已刷新"}


@router.get("/config/{key}")
def get_config_value(key: str):
    result = get_business_config(key)
    return {"key": key, "value": result}


@router.post("/config/reload", dependencies=[Depends(require_role("admin"))])
def reload_config():
    invalidate_cache()
    return {"message": "所有配置缓存已刷新，将从DB重新加载"}


@router.get("/qa/list", response_model=QAListResponse)
def list_qa(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
            category_l1: str | None = None, status: str | None = None):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    result = mysql_client.get_qa_list(page=page, page_size=page_size,
                                      category_l1=category_l1, status=status)
    items = [QAListItem(**_serialize_row(row)) for row in result["items"]]
    return QAListResponse(items=items, total=result["total"],
                          page=result["page"], page_size=result["page_size"])


@router.get("/qa/{qa_id}", response_model=QADetailResponse)
def get_qa_detail(qa_id: int):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    row = mysql_client.get_qa_detail(qa_id)
    if row is None:
        raise HTTPException(status_code=404, detail="QA不存在")
    return QADetailResponse(**_serialize_row(row))


@router.delete("/qa/{qa_id}", dependencies=[Depends(require_role("admin"))])
def delete_qa(qa_id: int):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    deleted = mysql_client.delete_qa(qa_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="QA不存在")
    if service is not None:
        service.invalidate_active_ids_cache()
    return {"qa_id": qa_id, "message": "已删除"}


@router.post("/qa/search", response_model=QASearchResponse)
def search_qa(req: QASearchRequest):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    result = mysql_client.search_qa(keyword=req.keyword, page=req.page,
                                    page_size=req.page_size,
                                    category_l1=req.category_l1, status=req.status)
    items = [QAListItem(**_serialize_row(row)) for row in result["items"]]
    return QASearchResponse(items=items, total=result["total"],
                            page=result["page"], page_size=result["page_size"])


@router.get("/stats", response_model=StatsResponse, dependencies=[Depends(require_role("admin"))])
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
        category_stats=category_stats,
    )


@router.get("/categories")
def get_categories():
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    return {"categories": _build_category_tree()}


@router.post("/categories", dependencies=[Depends(require_role("admin"))])
def create_category(req: CategoryCreateRequest):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    cat_id = mysql_client.create_category(req.label, req.parent_id, req.description)
    return {"id": cat_id, "message": "分类已创建"}


@router.put("/categories/{cat_id}", dependencies=[Depends(require_role("admin"))])
def update_category(cat_id: int, req: CategoryUpdateRequest):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    updated = mysql_client.update_category(cat_id, req.label, req.parent_id, req.description)
    if not updated:
        raise HTTPException(status_code=404, detail="分类不存在")
    return {"id": cat_id, "message": "分类已更新"}


@router.delete("/categories/{cat_id}", dependencies=[Depends(require_role("admin"))])
def delete_category(cat_id: int):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    deleted = mysql_client.delete_category(cat_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="分类不存在")
    return {"id": cat_id, "message": "分类已删除"}


@router.get("/audit/history", response_model=AuditLogListResponse, dependencies=[Depends(require_role("admin"))])
def audit_history(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    result = mysql_client.get_audit_history(page=page, page_size=page_size)
    items = [AuditLogItem(**_serialize_row(row)) for row in result["items"]]
    return AuditLogListResponse(items=items, total=result["total"],
                                page=result["page"], page_size=result["page_size"])


@router.get("/stats/trend", response_model=TrendResponse, dependencies=[Depends(require_role("admin"))])
def stats_trend(days: int = Query(7, ge=1, le=90)):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    dates = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
             for i in range(days - 1, -1, -1)]

    wo_rows = mysql_client.get_trend(days)
    wo_by_date = {str(r["d"]): r["cnt"] for r in wo_rows["items"]}
    work_order_counts = [wo_by_date.get(d, 0) for d in dates]

    qa_rows = mysql_client.get_qa_trend(days)
    qa_by_date = {str(r["d"]): r["cnt"] for r in qa_rows["items"]}
    qa_new_counts = [qa_by_date.get(d, 0) for d in dates]

    return TrendResponse(dates=dates, work_order_counts=work_order_counts, qa_new_counts=qa_new_counts)


@router.get("/work_orders", response_model=WorkOrderListResponse)
def list_work_orders(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                     status: str | None = None, dept: str | None = None):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    result = mysql_client.get_work_order_list(page=page, page_size=page_size,
                                              status=status, dept=dept)
    items = [WorkOrderListItem(**_serialize_row(row)) for row in result["items"]]
    return WorkOrderListResponse(items=items, total=result["total"],
                                 page=result["page"], page_size=result["page_size"])


@router.post("/work_orders", response_model=WorkOrderDetailResponse)
def create_work_order(req: WorkOrderCreateRequest):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    external_id = f"WO-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
    raw_data = json.dumps(req.model_dump(), ensure_ascii=False)
    wo_id = mysql_client.insert_work_order_full(external_id, req.next_dept, raw_data)
    return _work_order_to_detail({
        "id": wo_id, "external_id": external_id, "raw_data": raw_data,
        "status": "submitted", "dept": req.next_dept,
    })


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
    mysql_client.update_work_order_reply(wo_id, json.dumps(data, ensure_ascii=False), "processed")
    updated = mysql_client.get_work_order_detail(wo_id)
    return _work_order_to_detail(updated)


@router.post("/asr", response_model=ASRResponse)
async def asr_transcribe(file: UploadFile = File(...)):
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


@router.get("/prompts", response_model=list[PromptKeySummary], dependencies=[Depends(require_role("admin"))])
def list_prompt_keys():
    vm = get_version_manager()
    keys = vm.list_all_keys()
    return [PromptKeySummary(
        prompt_key=k["prompt_key"],
        latest_version=k["latest_version"] or 0,
        active_count=k["active_count"] or 0,
        shadow_count=k["shadow_count"] or 0,
    ) for k in keys]


@router.get("/prompts/{prompt_key}/versions", response_model=list[PromptVersionInfo], dependencies=[Depends(require_role("admin"))])
def list_prompt_versions(prompt_key: str):
    vm = get_version_manager()
    versions = vm.list_versions(prompt_key)
    return [PromptVersionInfo(
        id=v.get("id"),
        prompt_key=v["prompt_key"],
        version=v["version"],
        is_active=v["is_active"],
        status=v.get("status", "active"),
        description=v.get("description", ""),
        created_at=str(v.get("created_at", "")) if v.get("created_at") else None,
        template_text_preview=v["template_text"][:100] + "..." if len(v["template_text"]) > 100 else v["template_text"],
    ) for v in versions]


@router.get("/prompts/{prompt_key}/versions/{version}", dependencies=[Depends(require_role("admin"))])
def get_prompt_version(prompt_key: str, version: int):
    vm = get_version_manager()
    v = vm.get_version(prompt_key, version)
    if v is None:
        raise HTTPException(status_code=404, detail="版本不存在")
    return v


@router.post("/prompts/publish", dependencies=[Depends(require_role("admin"))])
def publish_prompt(req: PromptPublishRequest):
    vm = get_version_manager()
    result = vm.publish(req.prompt_key, req.template_text, req.description)
    return result


@router.post("/prompts/rollback", dependencies=[Depends(require_role("admin"))])
def rollback_prompt(req: PromptRollbackRequest):
    vm = get_version_manager()
    result = vm.rollback(req.prompt_key, req.target_version)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/prompts/shadow/start", dependencies=[Depends(require_role("admin"))])
def start_shadow(req: PromptShadowRequest):
    vm = get_version_manager()
    result = vm.start_shadow(req.prompt_key, req.shadow_version)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/prompts/shadow/stop", dependencies=[Depends(require_role("admin"))])
def stop_shadow(req: PromptShadowRequest):
    vm = get_version_manager()
    return vm.stop_shadow(req.prompt_key, req.shadow_version)


@router.get("/prompts/shadow/stats", dependencies=[Depends(require_role("admin"))])
def shadow_stats():
    return get_shadow_stats()


@router.get("/prompts/shadow/records", dependencies=[Depends(require_role("admin"))])
def shadow_records(prompt_key: str | None = None, diff_only: bool = False, limit: int = 50):
    return get_shadow_records(prompt_key=prompt_key, diff_only=diff_only, limit=limit)
