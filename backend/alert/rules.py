from dataclasses import dataclass


@dataclass
class AlertRule:
    id: str
    name: str
    metric: str
    check_type: str
    window: int
    threshold: float
    severity: str
    description: str


ALERT_RULES: list[AlertRule] = [
    AlertRule(
        id="rag_failure_rate",
        name="RAG检索失败率",
        metric="rag_query",
        check_type="failure_rate",
        window=300,
        threshold=0.10,
        severity="P0",
        description="5分钟内RAG检索失败率超过10%",
    ),
    AlertRule(
        id="rag_p95_latency",
        name="RAG检索P95延迟",
        metric="rag_query",
        check_type="p95_latency",
        window=300,
        threshold=3.0,
        severity="P0",
        description="5分钟内RAG检索P95延迟超过3秒",
    ),
    AlertRule(
        id="llm_failure_count",
        name="LLM调用失败",
        metric="llm_call",
        check_type="failure_count",
        window=300,
        threshold=5,
        severity="P0",
        description="5分钟内LLM调用失败超过5次",
    ),
    AlertRule(
        id="milvus_failure_count",
        name="Milvus搜索失败",
        metric="milvus_search",
        check_type="failure_count",
        window=300,
        threshold=3,
        severity="P0",
        description="5分钟内Milvus搜索失败超过3次",
    ),
    AlertRule(
        id="mysql_failure_count",
        name="MySQL查询失败",
        metric="mysql_query",
        check_type="failure_count",
        window=300,
        threshold=3,
        severity="P1",
        description="5分钟内MySQL查询失败超过3次",
    ),
    AlertRule(
        id="scheduler_failure",
        name="定时任务连续失败",
        metric="scheduler_task",
        check_type="consecutive_failure",
        window=3600,
        threshold=2,
        severity="P1",
        description="定时任务连续失败2次",
    ),
]
