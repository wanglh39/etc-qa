
from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str
    category_l1: str | None = None


class CandidateResult(BaseModel):
    qa_id: int
    question: str
    answer: str
    category_l1: str | None = None
    category_l2: str | None = None
    internal_process: str | None = None
    feedback_dept: str | None = None
    score: float


class QueryResponse(BaseModel):
    query: str
    standardized_query: str = ""
    confidence: str
    candidates: list[CandidateResult]
    total_candidates: int
    work_order_id: str | None = None


class AddQARequest(BaseModel):
    question: str
    answer: str
    category_l1: str | None = None
    category_l2: str | None = None
    internal_process: str | None = None
    feedback_dept: str | None = None


class AddQAResponse(BaseModel):
    qa_id: int
    message: str


class AgentProcessRequest(BaseModel):
    question: str
    answer: str | None = ""
    context: str | None = ""
    user_id: str | None = None


class AgentProcessResponse(BaseModel):
    question: str
    answer: str
    internal_process: str = ""
    feedback_dept: str = ""
    is_duplicate: bool = False
    duplicate_of: int | None = None
    similarity_score: float = 0.0
    category_l1: str = ""
    category_l2: str = ""
    category_confidence: float = 0.0
    needs_review: bool = False
    review_highlights: list[str] = []
    current_step: str = ""
    error: str | None = None


class UpdateStatusRequest(BaseModel):
    qa_id: int
    status: str


class UpdateStatusResponse(BaseModel):
    qa_id: int
    status: str
    message: str


class QAListItem(BaseModel):
    id: int
    question: str
    answer: str
    category_l1: str = ""
    category_l2: str = ""
    status: str = "active"
    created_at: str | None = None
    updated_at: str | None = None


class QAListResponse(BaseModel):
    items: list[QAListItem]
    total: int
    page: int
    page_size: int


class QADetailResponse(BaseModel):
    id: int
    question: str
    answer: str
    category_l1: str = ""
    category_l2: str = ""
    internal_process: str = ""
    feedback_dept: str = ""
    status: str = "active"
    created_at: str | None = None
    updated_at: str | None = None


class QASearchRequest(BaseModel):
    keyword: str
    category_l1: str | None = None
    status: str | None = None
    page: int = 1
    page_size: int = 20


class QASearchResponse(BaseModel):
    items: list[QAListItem]
    total: int
    page: int
    page_size: int


class StatsResponse(BaseModel):
    qa_total: int
    qa_active: int
    qa_deprecated: int
    qa_archived: int
    work_order_total: int
    work_order_submitted: int
    work_order_processed: int
    category_stats: dict


class WorkOrderListItem(BaseModel):
    id: int
    external_id: str = ""
    raw_data: str = ""
    status: str = ""
    created_at: str | None = None
    updated_at: str | None = None


class WorkOrderListResponse(BaseModel):
    items: list[WorkOrderListItem]
    total: int
    page: int
    page_size: int


class PromptPublishRequest(BaseModel):
    prompt_key: str
    template_text: str
    description: str = ""


class PromptRollbackRequest(BaseModel):
    prompt_key: str
    target_version: int | None = None


class PromptShadowRequest(BaseModel):
    prompt_key: str
    shadow_version: int


class PromptVersionInfo(BaseModel):
    id: int | None = None
    prompt_key: str
    version: int
    is_active: int
    status: str = "active"
    description: str = ""
    created_at: str | None = None
    template_text_preview: str = ""


class PromptKeySummary(BaseModel):
    prompt_key: str
    latest_version: int
    active_count: int
    shadow_count: int


class WorkOrderCreateRequest(BaseModel):
    service_id: str = ""
    customer_name: str = ""
    phone: str = ""
    problem_type: str = ""
    next_dept: str = ""
    return_dept: str = ""
    receive_user: str = ""
    priority: str = "mid"
    detail_desc: str = ""


class WorkOrderDetailResponse(BaseModel):
    id: int
    external_id: str = ""
    status: str = ""
    dept: str = ""
    service_id: str = ""
    customer_name: str = ""
    phone: str = ""
    problem_type: str = ""
    next_dept: str = ""
    return_dept: str = ""
    receive_user: str = ""
    priority: str = ""
    detail_desc: str = ""
    handle_remark: str = ""
    created_at: str | None = None
    updated_at: str | None = None


class WorkOrderReplyRequest(BaseModel):
    handle_remark: str = ""
    back_dept: str = ""


class AuditLogItem(BaseModel):
    id: int
    qa_id: int | None = None
    question: str = ""
    answer: str = ""
    result: str = ""
    operator: str = ""
    created_at: str | None = None


class AuditLogListResponse(BaseModel):
    items: list[AuditLogItem]
    total: int
    page: int
    page_size: int


class CategoryCreateRequest(BaseModel):
    label: str
    parent_id: int | None = None
    description: str = ""


class CategoryUpdateRequest(BaseModel):
    label: str
    parent_id: int | None = None
    description: str = ""


class TrendResponse(BaseModel):
    dates: list[str]
    work_order_counts: list[int]
    qa_new_counts: list[int]
