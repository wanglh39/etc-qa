from typing import Annotated

from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class AgentState(BaseModel):
    raw_question: str = Field(description="原始问题文本")
    raw_answer: str = Field(default="", description="原始答案文本")
    raw_context: str = Field(default="", description="会话上下文")
    work_order_context: str = Field(default="", description="工单额外上下文（工单类型/流转至/车牌号等）")
    user_id: str | None = Field(default=None, description="用户ID")

    question: str = Field(default="", description="处理后的问题")
    rewrite_confidence: float = Field(default=1.0, description="问题改写置信度（1.0=未改写或高置信，低值表示改写质量不确定）")
    answer: str = Field(default="", description="处理后的答案")
    internal_process: str = Field(default="", description="内部处理办法及流程")
    feedback_dept: str = Field(default="", description="涉及反馈部门/微信群/工单模板")
    hyde_questions: list[str] = Field(default_factory=list, description="HyDE生成的假设性问题")

    is_duplicate: bool = Field(default=False, description="是否重复")
    duplicate_of: int | None = Field(default=None, description="重复的原始qa_id")
    similarity_score: float = Field(default=0.0, description="与已有问题的相似度")

    category_l1: str = Field(default="", description="一级分类")
    category_l2: str = Field(default="", description="二级分类")
    category_confidence: float = Field(default=0.0, description="分类置信度")

    confidence: float = Field(default=1.0, description="整体处理置信度")
    needs_review: bool = Field(default=False, description="是否需要人工重点审核")
    review_highlights: list[str] = Field(default_factory=list, description="审核高亮项")

    current_step: str = Field(default="start", description="当前流水线步骤")
    error: str | None = Field(default=None, description="错误信息")
    messages: Annotated[list, add_messages] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True
