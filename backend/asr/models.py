from pydantic import BaseModel, Field


class SpeakerSegment(BaseModel):
    start: float = Field(description="开始时间（秒）")
    end: float = Field(description="结束时间（秒）")
    speaker: str = Field(description="说话人标识")
    text: str = Field(default="", description="该段说话内容")


class ASRResponse(BaseModel):
    text: str = Field(description="识别文本")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="识别置信度")
    duration_ms: int = Field(default=0, ge=0, description="音频时长（毫秒）")
    model: str = Field(default="", description="使用的模型名")
    language: str | None = Field(default=None, description="检测到的语言")
    segments: list[SpeakerSegment] = Field(default_factory=list, description="说话人分离结果")


class ASRHealthResponse(BaseModel):
    loaded: bool = Field(description="模型是否已加载")
    model: str = Field(default="", description="模型名")
    device: str = Field(default="", description="推理设备（cuda/cpu）")
    finetuned: bool = Field(default=False, description="是否使用微调模型")
    diarize_enabled: bool = Field(default=False, description="说话人分离是否启用")
