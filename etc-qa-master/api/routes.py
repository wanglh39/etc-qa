import os
import tempfile
from datetime import datetime

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

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
    UpdateStatusRequest,
    UpdateStatusResponse,
    WorkOrderListItem,
    WorkOrderListResponse,
)
from prompt.shadow_recorder import get_shadow_records, get_shadow_stats
from prompt.version_manager import get_version_manager
from rag.service import QAService
from utils.config_center import get_business_config, invalidate_cache
from utils.logger import get_logger

logger = get_logger("api.routes")

router = APIRouter()
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


@router.post("/query", response_model=QueryResponse)
def query_qa(req: QueryRequest):
    if service is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    result = service.query(req.question, req.category_l1)
    return result


@router.post("/add", response_model=AddQAResponse)
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


@router.get("/health")
def health():
    return {"status": "ok"}


@router.put("/qa/status", response_model=UpdateStatusResponse)
def update_qa_status(req: UpdateStatusRequest):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    valid_statuses = get_business_config("qa_statuses", ["active", "deprecated", "archived"])
    if req.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"status必须是{valid_statuses}之一")
    mysql_client.update_qa_status(req.qa_id, req.status)
    if service is not None:
        service.invalidate_active_ids_cache()
    return UpdateStatusResponse(qa_id=req.qa_id, status=req.status, message=f"状态已更新为{req.status}")


@router.put("/config/{key}")
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


@router.post("/config/reload")
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


@router.delete("/qa/{qa_id}")
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


@router.get("/stats", response_model=StatsResponse)
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
    tree = mysql_client.get_category_tree()
    return {"categories": tree}


@router.get("/work_orders", response_model=WorkOrderListResponse)
def list_work_orders(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                     status: str | None = None):
    if mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    result = mysql_client.get_work_order_list(page=page, page_size=page_size, status=status)
    items = [WorkOrderListItem(**_serialize_row(row)) for row in result["items"]]
    return WorkOrderListResponse(items=items, total=result["total"],
                                 page=result["page"], page_size=result["page_size"])


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


@router.get("/prompts", response_model=list[PromptKeySummary])
def list_prompt_keys():
    vm = get_version_manager()
    keys = vm.list_all_keys()
    return [PromptKeySummary(
        prompt_key=k["prompt_key"],
        latest_version=k["latest_version"] or 0,
        active_count=k["active_count"] or 0,
        shadow_count=k["shadow_count"] or 0,
    ) for k in keys]


@router.get("/prompts/{prompt_key}/versions", response_model=list[PromptVersionInfo])
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


@router.get("/prompts/{prompt_key}/versions/{version}")
def get_prompt_version(prompt_key: str, version: int):
    vm = get_version_manager()
    v = vm.get_version(prompt_key, version)
    if v is None:
        raise HTTPException(status_code=404, detail="版本不存在")
    return v


@router.post("/prompts/publish")
def publish_prompt(req: PromptPublishRequest):
    vm = get_version_manager()
    result = vm.publish(req.prompt_key, req.template_text, req.description)
    return result


@router.post("/prompts/rollback")
def rollback_prompt(req: PromptRollbackRequest):
    vm = get_version_manager()
    result = vm.rollback(req.prompt_key, req.target_version)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/prompts/shadow/start")
def start_shadow(req: PromptShadowRequest):
    vm = get_version_manager()
    result = vm.start_shadow(req.prompt_key, req.shadow_version)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/prompts/shadow/stop")
def stop_shadow(req: PromptShadowRequest):
    vm = get_version_manager()
    return vm.stop_shadow(req.prompt_key, req.shadow_version)


@router.get("/prompts/shadow/stats")
def shadow_stats():
    return get_shadow_stats()


@router.get("/prompts/shadow/records")
def shadow_records(prompt_key: str | None = None, diff_only: bool = False, limit: int = 50):
    return get_shadow_records(prompt_key=prompt_key, diff_only=diff_only, limit=limit)
