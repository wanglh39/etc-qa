
from pydantic import BaseModel, Field


class ASRResponse(BaseModel):
    text: str = Field(description="识别文本")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="识别置信度")
    duration_ms: int = Field(default=0, ge=0, description="音频时长（毫秒）")
    model: str = Field(default="", description="使用的模型名")
    language: str | None = Field(default=None, description="检测到的语言")


class ASRHealthResponse(BaseModel):
    loaded: bool = Field(description="模型是否已加载")
    model: str = Field(default="", description="模型名")
    device: str = Field(default="", description="推理设备（cuda/cpu）")
    finetuned: bool = Field(default=False, description="是否使用微调模型")
