from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from utils.config import get_config
from utils.logger import get_logger

logger = get_logger("agent.llm")

_llm_cache = {}
_structured_cache = {}


def _get_structured_method(model: str) -> str | None:
    cfg = get_config()
    explicit = cfg.get("llm", {}).get("structured_method")
    if explicit:
        return explicit if explicit != "none" else None

    registry = cfg.get("llm_registry", {})
    model_info = registry.get(model, {})
    method = model_info.get("structured_method")
    if method and method != "none":
        return method

    return None


def get_llm() -> ChatOpenAI:
    cfg = get_config()["llm"]
    if not cfg.get("enabled"):
        raise RuntimeError("LLM未启用，请在config.yaml中配置llm.enabled=true")

    key = (cfg["provider"], cfg["model"], cfg["base_url"])
    if key not in _llm_cache:
        _llm_cache[key] = ChatOpenAI(
            model=cfg["model"],
            api_key=cfg["api_key"],
            base_url=cfg["base_url"],
            temperature=cfg.get("temperature", 0.1),
            max_tokens=cfg.get("max_tokens", 1024),
            timeout=cfg.get("timeout", 10),
            max_retries=cfg.get("max_retries", 1),
        )
    return _llm_cache[key]


def get_structured_llm(output_schema: type[BaseModel]) -> tuple:
    llm = get_llm()
    schema_name = output_schema.__name__
    cache_key = (llm.model, schema_name)

    if cache_key in _structured_cache:
        return _structured_cache[cache_key]

    method = _get_structured_method(llm.model)

    if method is None:
        logger.info(f"模型 {llm.model} 不支持结构化输出，使用JSON解析: {schema_name}")
        _structured_cache[cache_key] = (llm, False)
        return llm, False

    try:
        structured = llm.with_structured_output(output_schema, method=method)
        _structured_cache[cache_key] = (structured, True)
        logger.info(f"结构化输出模式: {schema_name} ({method})")
        return structured, True
    except Exception as e:
        logger.warning(f"结构化输出初始化失败({method})，降级为JSON解析: {e}")
        _structured_cache[cache_key] = (llm, False)
        return llm, False
