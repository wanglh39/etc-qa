
from pydantic import BaseModel, Field


class StandardizeOutput(BaseModel):
    need_rewrite: bool = Field(description="是否需要改写")
    reason: str = Field(default="", description="判断理由")
    rewritten: str = Field(default="", description="改写后问题，不需要改写时留空")
    rewrite_confidence: float = Field(ge=0.0, le=1.0, default=1.0, description="改写质量置信度，1.0=高置信，低值表示改写可能有问题")


class StructureIngestOutput(BaseModel):
    question: str = Field(min_length=1, description="标准问题")
    answer: str = Field(min_length=1, description="对客话术")
    category_l1: str = Field(min_length=1, description="一级分类")
    category_l2: str = Field(default="", description="二级分类")
    internal_process: str = Field(default="", description="内部处理流程")
    feedback_dept: str = Field(default="", description="反馈部门")
    category_confidence: float = Field(ge=0.0, le=1.0, default=0.5, description="分类置信度")


class HydeJudgeOutput(BaseModel):
    need_rewrite: bool = Field(description="是否需要HyDE改写")
    reason: str = Field(default="", description="判断理由")


class HydeRewriteOutput(BaseModel):
    questions: list[str] = Field(default_factory=list, description="假设性问题列表")
