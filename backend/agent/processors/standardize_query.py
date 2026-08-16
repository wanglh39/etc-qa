import json
import re

from langchain_core.messages import HumanMessage

from agent.llm import get_llm, get_structured_llm
from agent.output_schemas import StandardizeOutput
from agent.prompt_engine import get_prompt_engine
from agent.state import AgentState
from utils.config import get_config
from utils.config_center import get_business_config
from utils.logger import get_logger

logger = get_logger("agent.processors.standardize_query")


def _get_filler_patterns() -> list:
    return get_business_config("filler_patterns", [])


def _get_core_patterns() -> list:
    raw = get_business_config("core_patterns", [])
    return [(item["pattern"], item["replacement"]) for item in raw]


def _get_brand_keywords() -> list:
    return get_business_config("brand_keywords", [])


def _get_subject_keywords() -> list:
    return get_business_config("subject_keywords", [])


def _get_question_words() -> list:
    return get_business_config("question_words", [])


def _get_preserve_question_words() -> list:
    return get_business_config("preserve_question_words", [])


def _get_standardize_limits() -> tuple:
    cfg = get_config().get("prompts", {}).get("standardize", {})
    return cfg.get("min_length", 5), cfg.get("max_length", 30), cfg.get("rewrite_min_length", 3)


JUDGE_PROMPT = """你是{{enterprise_name}}客服问题标准化助手。判断用户问题是否需要改写为标准检索格式。

## 核心原则：最小改动
- 问题已经简洁规范 → 不改写，直接返回
- 只有问题确实口语化严重、冗长模糊时才改写
- 禁止同义替换（"怎么"不换"如何"，"能不能"不换"是否可以"）
- 改写只做减法（去掉填充词/背景描述），不做加法（不添加新词）

## 不需要改写的例子
{{judge_no_rewrite_examples}}

## 需要改写的例子
{{judge_rewrite_examples}}

## 改写规则（必须严格遵守）
1. 必须保留品牌名：{{brand_keywords_str}}等
2. 必须保留疑问词：能不能、怎么、如何、为什么、多少等，不能把疑问句改成陈述句
3. 必须保留具体业务信息：报错提示词、金额、渠道名等
4. 只去掉口语填充词和冗余背景描述，核心内容一个字都不能少
5. 长度目标：{{min_length}}-{{max_length}}字

输出JSON：
{"need_rewrite": true/false, "reason": "判断理由", "rewritten": "改写后的问题（不需要改写时留空）", "rewrite_confidence": 0.0-1.0}

rewrite_confidence说明（改写质量自评）：
- 1.0：改写质量高，核心信息完整保留
- 0.5~1.0：改写合理，但可能有细微偏差
- 0~0.5：改写不确定，可能丢失或改变了核心含义
- 不需要改写时填1.0

问题：{{question}}"""


_JUDGE_NO_REWRITE_FALLBACK = """- "{{enterprise_name}}扣费异常怎么处理" → 不改写（已简洁，有业务关键词+疑问词）
- "黑名单怎么解除" → 不改写
- "发票怎么申请" → 不改写
- "解悠客服热线是多少" → 不改写"""

_JUDGE_REWRITE_FALLBACK = """- "我想问一下{{enterprise_name}}注销的流程是什么呢" → "{{enterprise_name}}注销流程是什么"（去掉填充词，保留核心）
- "客户张三反馈说他的{{enterprise_name}}重复扣费了上个月在同一高速口扣了两次" → "{{enterprise_name}}同一高速口重复扣费"（去掉人名和冗余背景）"""


def standardize_query(state: AgentState) -> dict:
    question = state.question or state.raw_question

    standardized = _rule_based_standardize(question)

    if _is_already_standard(standardized):
        return {"question": standardized, "rewrite_confidence": 1.0, "current_step": "standardize_query"}

    try:
        min_len, max_len, _ = _get_standardize_limits()
        enterprise_name = get_business_config("enterprise_name", "ETC")

        no_rewrite_examples = get_business_config("judge_no_rewrite_examples", "")
        if not no_rewrite_examples:
            no_rewrite_examples = _JUDGE_NO_REWRITE_FALLBACK.replace("{{enterprise_name}}", enterprise_name)

        rewrite_examples = get_business_config("judge_rewrite_examples", "")
        if not rewrite_examples:
            rewrite_examples = _JUDGE_REWRITE_FALLBACK.replace("{{enterprise_name}}", enterprise_name)

        engine = get_prompt_engine()
        prompt = engine.render(
            "judge",
            fallback=JUDGE_PROMPT,
            question=standardized,
            min_length=min_len,
            max_length=max_len,
            judge_no_rewrite_examples=no_rewrite_examples,
            judge_rewrite_examples=rewrite_examples,
        )

        structured_llm, supported = get_structured_llm(StandardizeOutput)

        if supported:
            try:
                result = structured_llm.invoke([HumanMessage(content=prompt)])
                if isinstance(result, StandardizeOutput):
                    if not result.need_rewrite:
                        return {"question": standardized, "rewrite_confidence": 1.0, "current_step": "standardize_query"}
                    rewritten = result.rewritten.strip().strip("。？！")
                    _, _, rewrite_min_len = _get_standardize_limits()
                    rw_conf = result.rewrite_confidence
                    if rewritten and len(rewritten) >= rewrite_min_len and _preserves_keywords(standardized, rewritten):
                        rw_accept = get_config().get("rewrite_confidence", {}).get("accept", 0.5)
                        if rw_conf >= rw_accept:
                            standardized = rewritten
                        else:
                            logger.warning(f"改写置信度低({rw_conf:.2f})，拒绝LLM改写，使用规则结果")
                    return {"question": standardized, "rewrite_confidence": rw_conf, "current_step": "standardize_query"}
            except Exception as e:

                logger.warning(f"结构化输出调用失败，降级为JSON解析: {e}")

        llm = get_llm()
        response = llm.invoke([HumanMessage(content=prompt)])
        parsed = _parse_json(response.content.strip())
        if parsed:
            if not parsed.get("need_rewrite", False):
                return {"question": standardized, "rewrite_confidence": 1.0, "current_step": "standardize_query"}
            rewritten = parsed.get("rewritten", "").strip().strip("。？！")
            _, _, rewrite_min_len = _get_standardize_limits()
            rw_conf = parsed.get("rewrite_confidence", 1.0)
            try:
                rw_conf = float(rw_conf)
                rw_conf = max(0.0, min(1.0, rw_conf))
            except (TypeError, ValueError):
                rw_conf = get_config().get("rewrite_confidence", {}).get("fallback", 0.5)
            if rewritten and len(rewritten) >= rewrite_min_len and _preserves_keywords(standardized, rewritten):
                rw_accept = get_config().get("rewrite_confidence", {}).get("accept", 0.5)
                if rw_conf >= rw_accept:
                    standardized = rewritten
                else:
                    logger.warning(f"改写置信度低({rw_conf:.2f})，拒绝LLM改写，使用规则结果")
            return {"question": standardized, "rewrite_confidence": rw_conf, "current_step": "standardize_query"}
    except Exception as e:
        logger.warning(f"标准化失败，使用规则结果: {e}")

    return {"question": standardized, "rewrite_confidence": 0.5, "current_step": "standardize_query"}


def _rule_based_standardize(text: str) -> str:
    filler_patterns = _get_filler_patterns()
    core_patterns = _get_core_patterns()
    text = text.strip()
    prev = ""
    while prev != text:
        prev = text
        for pattern in filler_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)
        text = text.strip()
    for pattern, replacement in core_patterns:
        if re.search(pattern, text):
            text = re.sub(pattern, replacement, text, count=1)
    text = re.sub(r"\s+", "", text)
    return text.strip(" ，。！？、")


def _is_already_standard(text: str) -> bool:
    brand_keywords = _get_brand_keywords()
    subject_keywords = _get_subject_keywords()
    question_words = _get_question_words()
    min_len, max_len, _ = _get_standardize_limits()
    if len(text) < min_len or len(text) > max_len:
        return False
    if re.search(r'[。.；;]', text):
        return False
    has_subject = any(kw in text for kw in brand_keywords + subject_keywords)
    has_question_word = any(kw in text for kw in question_words)
    return has_subject and has_question_word


def _preserves_keywords(original: str, rewritten: str) -> bool:
    brand_keywords = _get_brand_keywords()
    preserve_qw = _get_preserve_question_words()
    for kw in brand_keywords:
        if kw in original and kw not in rewritten:
            return False
    for qw in preserve_qw:
        if qw in original and qw not in rewritten:
            return False
    return True


def _parse_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                return None
        return None
