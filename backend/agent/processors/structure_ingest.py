import json
import random
import threading
from collections import defaultdict

from langchain_core.messages import HumanMessage

from agent.llm import get_llm, get_structured_llm
from agent.output_schemas import StructureIngestOutput
from agent.prompt_engine import get_prompt_engine
from agent.state import AgentState
from db.mysql_client import MySQLClient
from utils.config import get_config
from utils.config_center import get_business_config
from utils.logger import get_logger

logger = get_logger("agent.processors.structure_ingest")

_category_cache = {"tree": None, "tree_str": None, "default_l1": None, "default_l2": None}
_example_cache = {"examples": None}
_shared_mysql = None
_cache_lock = threading.Lock()


def _get_mysql() -> MySQLClient:
    global _shared_mysql
    with _cache_lock:
        if _shared_mysql is None:
            _shared_mysql = MySQLClient()
        return _shared_mysql


def get_category_tree() -> dict:
    with _cache_lock:
        if _category_cache["tree"] is not None:
            return _category_cache["tree"]
    try:
        mysql = _get_mysql()
        all_qa = mysql.get_all_questions()
        tree = defaultdict(set)
        for qa in all_qa:
            l1 = qa.get("category_l1", "").strip()
            l2 = qa.get("category_l2", "").strip()
            if l1 and l2:
                tree[l1].add(l2)
            elif l1:
                tree[l1].add(l1)
        result = {l1: sorted(l2_set) for l1, l2_set in sorted(tree.items())}
        with _cache_lock:
            if result:
                _category_cache["tree"] = result
                _category_cache["default_l1"] = next(iter(result))
                _category_cache["default_l2"] = (
                    result[_category_cache["default_l1"]][0] if result[_category_cache["default_l1"]] else ""
                )
            else:
                _category_cache["tree"] = {}
                _category_cache["default_l1"] = ""
                _category_cache["default_l2"] = ""
            return _category_cache["tree"]
    except Exception:
        with _cache_lock:
            _category_cache["tree"] = {}
            _category_cache["default_l1"] = ""
            _category_cache["default_l2"] = ""
            return {}


def get_category_tree_str() -> str:
    if _category_cache["tree_str"] is not None:
        return _category_cache["tree_str"]
    tree = get_category_tree()
    if not tree:
        _category_cache["tree_str"] = ""
        return ""
    lines = []
    for l1, l2_list in tree.items():
        lines.append(f"- {l1}: {', '.join(l2_list)}")
    _category_cache["tree_str"] = "\n".join(lines)
    return _category_cache["tree_str"]


def invalidate_category_cache():
    with _cache_lock:
        _category_cache["tree"] = None
        _category_cache["tree_str"] = None
        _category_cache["default_l1"] = None
        _category_cache["default_l2"] = None


def invalidate_example_cache():
    with _cache_lock:
        _example_cache["examples"] = None


def get_reference_examples(count: int = 10) -> list[str]:
    with _cache_lock:
        if _example_cache["examples"] is not None:
            return _example_cache["examples"][:count]
    try:
        cfg = get_config().get("prompts", {}).get("standardize", {})
        min_len = cfg.get("min_length", 5)
        max_len = cfg.get("max_length", 30)
        mysql = _get_mysql()
        all_qa = mysql.get_all_questions()
        questions = [
            qa["question"] for qa in all_qa if qa.get("question") and min_len <= len(qa["question"]) <= max_len
        ]
        if len(questions) > count * 3:
            sampled = random.sample(questions, count * 3)
        else:
            sampled = questions
        with _cache_lock:
            _example_cache["examples"] = sampled
        return sampled[:count]
    except Exception:
        with _cache_lock:
            _example_cache["examples"] = []
        return []


def _get_kw_lists() -> tuple:
    forbidden = get_business_config("forbidden_new_kws", [])
    must_preserve = get_business_config("must_preserve_kws", [])
    return forbidden, must_preserve


STRUCTURE_INGEST_PROMPT = """你是{{enterprise_name}}客服知识库管理员。请将以下工单数据处理为知识库标准格式，输出JSON。

## 输出字段说明
- question：知识库标准问题（改写后直接向量化存入Milvus，必须与现有问题风格一致）
- answer：对客话术（面向客户的回答，简洁清晰，包含关键处理结果）
- category_l1：一级分类（从分类体系中选择）
- category_l2：二级分类（从分类体系中选择）
- internal_process：内部处理办法及流程（给客服看的操作步骤）
- feedback_dept：涉及反馈部门/微信群/工单模板
- category_confidence：分类置信度（0-1，分类越确定越高，0.5以下表示不确定）

## 分类体系
{{category_tree}}

## 分类选择规则
根据问题核心诉求选择最匹配的分类，不要默认选第一个：
- 先判断问题属于哪个业务板块（售后/售前/账户/财务...），再选二级分类
{{classify_examples}}

## 问题改写规则
1. 长度5-30字，简短直接，提问式
2. 格式：主语+诉求/疑问，如"XX怎么办理？"、"XX是什么原因？"
3. 去掉叙述性描述（"我上个月..."、"同一个路段..."等背景），保留核心诉求
4. 【必须保留】原问题中的核心业务关键词：{{must_preserve_kws_str}}等，一个都不能丢
5. 【禁止引入】不得凭空引入原问题未提及的全新业务概念
6. 保持原问题的核心意图不变，不要偏移到其他诉求

## 答案结构化规则
1. answer是面向客户的最终话术，简洁清晰，包含关键处理结果
2. internal_process是客服内部操作步骤，客户看不到
3. feedback_dept从工单上下文中的"流转至"字段提取，没有则留空
4. "待XX岗..."是内部流程放internal_process，不是answer

## 参考示例（来自真实知识库）
{{reference_examples}}

## 工单数据
问题描述：{{question}}
处理结果：{{answer}}
{{context}}

## 输出JSON"""


_CLASSIFY_EXAMPLES_FALLBACK = "- 示例：扣费/退款/账单相关→账单类；设备/OBU/蓝牙相关→设备异常；黑名单/风控相关→黑名单类；注销/激活/挂失相关→业务变更类；冻结/解冻/账户相关→账户类"


def _validate_rewrite(original: str, rewrite: str) -> tuple:
    forbidden_new_kws, must_preserve_kws = _get_kw_lists()
    hallucination_kws = [kw for kw in forbidden_new_kws if kw in rewrite and kw not in original]
    lost_kws = [kw for kw in must_preserve_kws if kw in original and kw not in rewrite]
    return hallucination_kws, lost_kws


def _apply_confidence_action(
    cat_conf: float, cat_l1: str, cat_l2: str, default_l1: str, default_l2: str, review_highlights: list
) -> tuple:
    cfg = get_config().get("ingest_confidence", {})
    auto_th = cfg.get("auto", 0.8)
    review_th = cfg.get("review", 0.5)
    highlight_th = cfg.get("highlight", 0.3)

    needs_review = False
    if cat_conf >= auto_th:
        pass
    elif cat_conf >= review_th:
        needs_review = True
    elif cat_conf >= highlight_th:
        needs_review = True
        review_highlights.append(f"分类置信度低({cat_conf:.2f})，建议人工确认")
    else:
        needs_review = True
        cat_l1 = default_l1
        cat_l2 = default_l2
        review_highlights.append(f"分类置信度极低({cat_conf:.2f})，使用默认分类，建议人工确认")

    return cat_l1, cat_l2, needs_review


def structure_ingest(state: AgentState) -> dict:
    question = state.question or state.raw_question
    answer = state.answer or state.raw_answer

    context = ""
    if state.work_order_context:
        context = f"工单上下文：{state.work_order_context}"

    tree = get_category_tree()
    tree_str = get_category_tree_str()
    default_l1 = _category_cache["default_l1"] or ""
    default_l2 = _category_cache["default_l2"] or ""

    _, must_preserve_kws = _get_kw_lists()

    sample_count = get_business_config("reference_sample_count", 10)
    examples = get_reference_examples(sample_count)
    reference_examples = "\n".join(f'- "{ex}"' for ex in examples) if examples else "（无参考示例）"

    classify_examples = get_business_config("classify_examples", _CLASSIFY_EXAMPLES_FALLBACK)

    try:
        engine = get_prompt_engine()
        prompt = engine.render(
            "structure_ingest",
            fallback=STRUCTURE_INGEST_PROMPT,
            category_tree=tree_str,
            question=question,
            answer=answer,
            context=context,
            must_preserve_kws_str="、".join(must_preserve_kws),
            reference_examples=reference_examples,
            classify_examples=classify_examples,
        )

        structured_llm, supported = get_structured_llm(StructureIngestOutput)

        if supported:
            try:
                result = structured_llm.invoke([HumanMessage(content=prompt)])
                if isinstance(result, StructureIngestOutput):
                    return _process_structured_result(result, question, answer, tree, default_l1, default_l2, state)
            except Exception as e:
                logger.warning(f"结构化输出调用失败，降级为JSON解析: {e}")

        llm = get_llm()
        response = llm.invoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        parsed = _parse_json(content)
        if parsed:
            return _process_parsed_result(parsed, question, answer, tree, default_l1, default_l2, state)

    except Exception as e:
        logger.error(f"LLM规整失败: {e}")
        return {
            "question": question,
            "answer": answer,
            "category_l1": default_l1,
            "category_l2": default_l2,
            "category_confidence": 0.3,
            "internal_process": "",
            "feedback_dept": "",
            "error": f"LLM规整失败: {e!s}",
            "current_step": "structure_ingest",
        }

    return {
        "question": question,
        "answer": answer,
        "category_l1": default_l1,
        "category_l2": default_l2,
        "category_confidence": 0.3,
        "internal_process": "",
        "feedback_dept": "",
        "current_step": "structure_ingest",
    }


def _process_structured_result(
    result: StructureIngestOutput,
    question: str,
    answer: str,
    tree: dict,
    default_l1: str,
    default_l2: str,
    state: AgentState,
) -> dict:
    cat_l1 = result.category_l1
    cat_l2 = result.category_l2
    if cat_l1 not in tree:
        cat_l1 = default_l1
        cat_l2 = default_l2
    elif cat_l2 not in tree.get(cat_l1, []):
        cat_l2 = tree[cat_l1][0] if tree[cat_l1] else default_l2

    rewritten = result.question
    hallucination_kws, lost_kws = _validate_rewrite(question, rewritten)

    needs_review = False
    review_highlights = list(state.review_highlights)

    if hallucination_kws:
        rewritten = question
        needs_review = True
        review_highlights.append(f"改写引入不存在的关键词{hallucination_kws}，已回退为原始问题")

    if lost_kws and not hallucination_kws:
        needs_review = True
        review_highlights.append(f"改写丢失关键词{lost_kws}，建议人工确认")

    std_cfg = get_business_config("standardize", {})
    rewrite_min_len = std_cfg.get("rewrite_min_length", 3) if isinstance(std_cfg, dict) else 3
    if not rewritten or len(rewritten) < rewrite_min_len:
        rewritten = question
        needs_review = True
        review_highlights.append("问题改写结果过短，建议人工确认")

    cat_conf = result.category_confidence
    cat_l1, cat_l2, conf_review = _apply_confidence_action(
        cat_conf, cat_l1, cat_l2, default_l1, default_l2, review_highlights
    )
    if conf_review:
        needs_review = True

    updates = {
        "question": rewritten,
        "answer": result.answer,
        "category_l1": cat_l1,
        "category_l2": cat_l2,
        "category_confidence": cat_conf,
        "internal_process": result.internal_process,
        "feedback_dept": result.feedback_dept,
        "current_step": "structure_ingest",
    }
    if needs_review:
        updates["needs_review"] = True
        updates["review_highlights"] = review_highlights
    return updates


def _process_parsed_result(
    parsed: dict, question: str, answer: str, tree: dict, default_l1: str, default_l2: str, state: AgentState
) -> dict:
    cat_l1 = parsed.get("category_l1", default_l1)
    cat_l2 = parsed.get("category_l2", default_l2)
    if cat_l1 not in tree:
        cat_l1 = default_l1
        cat_l2 = default_l2
    elif cat_l2 not in tree.get(cat_l1, []):
        cat_l2 = tree[cat_l1][0] if tree[cat_l1] else default_l2

    rewritten = parsed.get("question", question)
    hallucination_kws, lost_kws = _validate_rewrite(question, rewritten)

    needs_review = False
    review_highlights = list(state.review_highlights)

    if hallucination_kws:
        rewritten = question
        needs_review = True
        review_highlights.append(f"改写引入不存在的关键词{hallucination_kws}，已回退为原始问题")

    if lost_kws and not hallucination_kws:
        needs_review = True
        review_highlights.append(f"改写丢失关键词{lost_kws}，建议人工确认")

    std_cfg = get_business_config("standardize", {})
    rewrite_min_len = std_cfg.get("rewrite_min_length", 3) if isinstance(std_cfg, dict) else 3
    if not rewritten or len(rewritten) < rewrite_min_len:
        rewritten = question
        needs_review = True
        review_highlights.append("问题改写结果过短，建议人工确认")

    cat_conf = parsed.get("category_confidence", 0.5)
    try:
        cat_conf = float(cat_conf)
        cat_conf = max(0.0, min(1.0, cat_conf))
    except (TypeError, ValueError):
        cat_conf = 0.3

    cat_l1, cat_l2, conf_review = _apply_confidence_action(
        cat_conf, cat_l1, cat_l2, default_l1, default_l2, review_highlights
    )
    if conf_review:
        needs_review = True

    updates = {
        "question": rewritten,
        "answer": parsed.get("answer", answer),
        "category_l1": cat_l1,
        "category_l2": cat_l2,
        "category_confidence": cat_conf,
        "internal_process": parsed.get("internal_process", ""),
        "feedback_dept": parsed.get("feedback_dept", ""),
        "current_step": "structure_ingest",
    }
    if needs_review:
        updates["needs_review"] = True
        updates["review_highlights"] = review_highlights
    return updates


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
