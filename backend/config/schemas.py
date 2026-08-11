from pydantic import BaseModel, Field, field_validator


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = Field(ge=1, le=65535)
    title: str
    version: str
    workers: int = Field(ge=1)


class CacheConfig(BaseModel):
    active_ids_ttl: int = Field(ge=1)
    config_ttl: int = Field(ge=1)


class MysqlPoolConfig(BaseModel):
    max_usage: int = Field(ge=0)
    ping: int = Field(ge=0)


class MysqlEnvConfig(BaseModel):
    host: str
    port: int = Field(ge=1, le=65535)
    user: str
    password: str
    database: str
    pool: MysqlPoolConfig


class MilvusEnvConfig(BaseModel):
    db_path: str
    collection_name: str


class MilvusIndexConfig(BaseModel):
    type: str
    M: int = Field(ge=4)
    ef_construction: int = Field(ge=1)


class MilvusSearchConfig(BaseModel):
    ef: int = Field(ge=1)
    overfetch_ratio: int = Field(ge=1)


class EmbedModelConfig(BaseModel):
    name: str
    path: str
    dim: int = Field(ge=1)


class RerankModelConfig(BaseModel):
    name: str
    path: str


class ModelsConfig(BaseModel):
    embed: EmbedModelConfig
    rerank: RerankModelConfig
    query_prefix: str = ""


class LlmConfig(BaseModel):
    enabled: bool
    provider: str
    api_key: str
    base_url: str
    model: str
    temperature: float = Field(ge=0, le=2)
    max_tokens: int = Field(ge=1)

    @field_validator("api_key")
    @classmethod
    def api_key_not_empty(cls, v):
        if not v or v.startswith("${"):
            raise ValueError("api_key未配置，请设置环境变量或在.env中配置")
        return v


class ThresholdConfig(BaseModel):
    mode: str
    gap_high: float = Field(ge=0, le=1)
    gap_mid: float = Field(ge=0, le=1)
    gap_low: float = Field(ge=0, le=1)
    floor_high: float = Field(ge=0, le=1)
    floor_mid: float = Field(ge=0, le=1)
    floor_low: float = Field(ge=0, le=1)
    high: float = Field(ge=0, le=1)
    low: float = Field(ge=0, le=1)
    min: float = Field(ge=0, le=1)

    @field_validator("mode")
    @classmethod
    def mode_must_be_valid(cls, v):
        if v not in ("gap", "absolute"):
            raise ValueError(f"mode必须是gap或absolute，got: {v}")
        return v


class IngestConfidenceConfig(BaseModel):
    auto: float = Field(ge=0, le=1)
    review: float = Field(ge=0, le=1)
    highlight: float = Field(ge=0, le=1)

    @field_validator("review", "highlight")
    @classmethod
    def thresholds_ordered(cls, v, info):
        return v


class AsrConfig(BaseModel):
    enabled: bool
    model: str
    finetuned_path: str = ""
    max_duration_ms: int = Field(ge=1)
    sample_rate: int = Field(ge=1)
    language: str = "zh"
    device: str = "cuda"
    use_vllm: bool = False
    tensor_parallel_size: int = Field(ge=1)


class HydeConfig(BaseModel):
    enabled: bool
    conditional: bool = True
    num_questions: int = Field(ge=1)
    max_questions_per_qa: int = Field(ge=1)
    max_rewrite_per_batch: int = Field(ge=1)
    answer_summary_max_len: int = Field(ge=1)


class DedupConfig(BaseModel):
    question_threshold: float = Field(ge=0, le=1)
    answer_threshold: float = Field(ge=0, le=1)


class DataConfig(BaseModel):
    qa_csv: str
    test_csv: str = ""
    test_rewrite_csv: str = ""
    work_order_csv: str = ""
    raw_qa_csv: str = ""


VALIDATORS = {
    "server": ServerConfig,
    "cache": CacheConfig,
    "mysql": MysqlEnvConfig,
    "milvus": MilvusEnvConfig,
    "models": ModelsConfig,
    "llm": LlmConfig,
    "threshold": ThresholdConfig,
    "ingest_confidence": IngestConfidenceConfig,
    "asr": AsrConfig,
    "hyde": HydeConfig,
    "dedup": DedupConfig,
    "data": DataConfig,
}


def validate_config(cfg: dict) -> list[str]:
    errors = []
    for key, schema_cls in VALIDATORS.items():
        if key not in cfg:
            errors.append(f"[{key}] 配置段缺失")
            continue
        try:
            schema_cls(**cfg[key])
        except Exception as e:
            for line in str(e).split("\n"):
                if line.strip():
                    errors.append(f"[{key}] {line.strip()}")
    return errors
