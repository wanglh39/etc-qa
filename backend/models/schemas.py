
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., max_length=500)
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
    question: str = Field(..., max_length=500)
    answer: str = Field(..., max_length=5000)
    category_l1: str | None = Field(None, max_length=50)
    category_l2: str | None = Field(None, max_length=50)
    internal_process: str | None = Field(None, max_length=2000)
    feedback_dept: str | None = Field(None, max_length=50)


class AddQAResponse(BaseModel):
    qa_id: int
    message: str


class AgentProcessRequest(BaseModel):
    question: str = Field(..., max_length=500)
    answer: str | None = Field("", max_length=5000)
    context: str | None = Field("", max_length=5000)
    user_id: str | None = Field(None, max_length=64)


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
    keyword: str = Field(..., max_length=200)
    category_l1: str | None = Field(None, max_length=50)
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
    service_id: str = Field("", max_length=64)
    customer_name: str = Field("", max_length=64)
    phone: str = Field("", max_length=32)
    problem_type: str = Field("", max_length=32)
    next_dept: str = Field("", max_length=32)
    return_dept: str = Field("", max_length=32)
    receive_user: str = Field("", max_length=64)
    priority: str = Field("mid", max_length=16)
    detail_desc: str = Field("", max_length=5000)


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
    handle_remark: str = Field("", max_length=5000)
    back_dept: str = Field("", max_length=32)


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


class OperationLogItem(BaseModel):
    id: int
    operator: str = ""
    action: str = ""
    target_type: str = ""
    target_id: int | None = None
    detail: str = ""
    ip: str = ""
    created_at: str | None = None


class OperationLogListResponse(BaseModel):
    items: list[OperationLogItem]
    total: int
    page: int
    page_size: int


class CategoryCreateRequest(BaseModel):
    label: str = Field(..., max_length=50)
    parent_id: int | None = None
    description: str = Field("", max_length=500)


class CategoryUpdateRequest(BaseModel):
    label: str = Field(..., max_length=50)
    parent_id: int | None = None
    description: str = Field("", max_length=500)


class TrendResponse(BaseModel):
    dates: list[str]
    work_order_counts: list[int]
    qa_new_counts: list[int]


class ASRQueryResponse(BaseModel):
    asr_text: str
    asr_confidence: float = 1.0
    asr_duration_ms: int = 0
    asr_model: str = ""
    asr_language: str | None = None
    asr_segments: list[dict] = []
    query: str = ""
    standardized_query: str = ""
    confidence: str = ""
    candidates: list[CandidateResult] = []
    total_candidates: int = 0


class UserListItem(BaseModel):
    id: int
    username: str
    role: str
    dept: str = ""
    status: str = "active"
    created_at: str | None = None
    updated_at: str | None = None


class UserListResponse(BaseModel):
    items: list[UserListItem]
    total: int
    page: int
    page_size: int


class UserCreateRequest(BaseModel):
    username: str = Field(..., max_length=50)
    password: str = Field(..., min_length=6, max_length=128)
    role: str = Field(..., max_length=50)
    dept: str = Field("", max_length=50)
    status: str = Field("active", max_length=20)


class UserUpdateRequest(BaseModel):
    role: str | None = Field(None, max_length=50)
    dept: str | None = Field(None, max_length=50)
    status: str | None = Field(None, max_length=20)


class ResetPasswordRequest(BaseModel):
    user_id: int
    new_password: str = Field(..., min_length=6, max_length=128)


class RoleItem(BaseModel):
    id: int
    role_key: str
    role_name: str
    description: str = ""
    created_at: str | None = None


class RoleCreateRequest(BaseModel):
    role_key: str = Field(..., max_length=50)
    role_name: str = Field(..., max_length=100)
    description: str = Field("", max_length=500)


class RoleUpdateRequest(BaseModel):
    role_name: str | None = Field(None, max_length=100)
    description: str | None = Field(None, max_length=500)
