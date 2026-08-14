
from pydantic import BaseModel, Field


class SpeakerSegment(BaseModel):
    start: float = Field(description="寮€濮嬫椂闂达紙绉掞級")
    end: float = Field(description="缁撴潫鏃堕棿锛堢锛?)
    speaker: str = Field(description="璇磋瘽浜烘爣璇?)
    text: str = Field(default="", description="璇ユ璇磋瘽鍐呭")


class ASRResponse(BaseModel):
    text: str = Field(description="璇嗗埆鏂囨湰")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="璇嗗埆缃俊搴?)
    duration_ms: int = Field(default=0, ge=0, description="闊抽鏃堕暱锛堟绉掞級")
    model: str = Field(default="", description="浣跨敤鐨勬ā鍨嬪悕")
    language: str | None = Field(default=None, description="妫€娴嬪埌鐨勮瑷€")
    segments: list[SpeakerSegment] = Field(default_factory=list, description="璇磋瘽浜哄垎绂荤粨鏋?)


class ASRHealthResponse(BaseModel):
    loaded: bool = Field(description="妯″瀷鏄惁宸插姞杞?)
    model: str = Field(default="", description="妯″瀷鍚?)
    device: str = Field(default="", description="鎺ㄧ悊璁惧锛坈uda/cpu锛?)
    finetuned: bool = Field(default=False, description="鏄惁浣跨敤寰皟妯″瀷")
    diarize_enabled: bool = Field(default=False, description="璇磋瘽浜哄垎绂绘槸鍚﹀惎鐢?)