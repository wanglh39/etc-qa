import json

from langchain_core.messages import HumanMessage

from agent.llm import get_llm, get_structured_llm
from agent.output_schemas import HydeJudgeOutput, HydeRewriteOutput
from agent.prompt_engine import get_prompt_engine
from agent.state import AgentState
from utils.config import get_config
from utils.config_center import get_business_config
from utils.logger import get_logger

logger = get_logger("agent.processors.hyde_rewrite")

HYDE_JUDGE_PROMPT = """你是{{enterprise_name}}知识库管理员。判断以下问题是否需要生成假设性改写来提升检索召回率。

## 不需要改写的情况
- 问题简洁标准，包含业务关键词+疑问词，5-15字
- 问题表述与知识库常见问法高度一致
{{hyde_judge_no_rewrite_examples}}

## 需要改写的情况
- 问题冗长、口语化、包含背景描述
- 问题表述与知识库标准问法差异大
- 答案包含具体细节（金额/渠道/报错词），改写时需保留
{{hyde_judge_rewrite_examples}}

输出JSON：
{"need_rewrite": true/false, "reason": "判断理由"}

问题：{{question}}
答案摘要：{{answer_summary}}"""

_HYDE_JUDGE_NO_REWRITE_FALLBACK = """示例：
- "{{enterprise_name}}怎么注销" → 不需要
- "黑名单如何解除" → 不需要
- "发票怎么申请" → 不需要"""

_HYDE_JUDGE_REWRITE_FALLBACK = """示例：
- "我上个月在同一个高速口被扣了两次费怎么办" → 需要
- "客户说他的{{enterprise_name}}设备不亮了但是蓝牙能连上" → 需要"""

HYDE_PROMPT = """你是{{enterprise_name}}用户，正在咨询客服。请根据以下问答，生成{{num_questions}}种你会怎么问这个问题。

要求：
1. 站在用户角度，口语化，像打电话问客服
2. 必须保留品牌名（{{brand_keywords_str}}等）
3. 必须保留疑问词（能不能、怎么、为什么、多少等）
4. 如果答案里有具体数字/渠道/报错词，改写时必须带上（如158元、农商行、实名认证异常）
5. 每种10-30字，不要重复，语义必须与标准问题一致
6. 不要引入标准问题和答案中未提及的业务概念

示例：
{{hyde_examples}}

标准问题：{{question}}
答案摘要：{{answer_summary}}

{{num_questions}}种问法（每行一个，不要编号）："""

_HYDE_EXAMPLES_FALLBACK = """标准问题：{{enterprise_name}}重复扣费怎么退款
→ {{enterprise_name}}同一高速扣了两次费怎么办
→ 重复扣费了钱什么时候退回来
→ {{enterprise_name}}多扣了一次怎么申请退款"""


def _judge_need_rewrite(question: str, answer_summary: str) -> tuple:
    cfg = get_config()
    hyde_cfg = cfg.get("hyde", {})
    conditional = hyde_cfg.get("conditional", True)

    if not conditional:
        return True, "conditional=false，全部改写"

    std_cfg = get_business_config("standardize", {})
    min_len = std_cfg.get("min_length", 5) if isinstance(std_cfg, dict) else 5
    max_len = std_cfg.get("max_length", 30) if isinstance(std_cfg, dict) else 30
    brand_keywords = get_business_config("brand_keywords", [])
    subject_keywords = get_business_config("subject_keywords", [])
    question_words = get_business_config("question_words", [])

    if min_len <= len(question) <= max_len:
        has_brand = any(kw in question for kw in brand_keywords + subject_keywords)
        has_qw = any(kw in question for kw in question_words)
        if has_brand and has_qw:
            return False, "问题简洁标准，跳过HyDE"

    try:
        engine = get_prompt_engine()
        enterprise_name = get_business_config("enterprise_name", "ETC")

        no_rewrite_examples = get_business_config("hyde_judge_no_rewrite_examples", "")
        if not no_rewrite_examples:
            no_rewrite_examples = _HYDE_JUDGE_NO_REWRITE_FALLBACK.replace("{{enterprise_name}}", enterprise_name)

        rewrite_examples = get_business_config("hyde_judge_rewrite_examples", "")
        if not rewrite_examples:
            rewrite_examples = _HYDE_JUDGE_REWRITE_FALLBACK.replace("{{enterprise_name}}", enterprise_name)

        prompt = engine.render(
            "hyde_judge",
            fallback=HYDE_JUDGE_PROMPT,
            question=question,
            answer_summary=answer_summary,
            hyde_judge_no_rewrite_examples=no_rewrite_examples,
            hyde_judge_rewrite_examples=rewrite_examples,
        )

        structured_llm, supported = get_structured_llm(HydeJudgeOutput)

        if supported:
            try:
                result = structured_llm.invoke([HumanMessage(content=prompt)])
                if isinstance(result, HydeJudgeOutput):
                    return result.need_rewrite, result.reason
            except Exception as e:

                logger.warning(f"HyDE判断结构化输出失败，降级为JSON解析: {e}")

        llm = get_llm()
        response = llm.invoke([HumanMessage(content=prompt)])
        parsed = _parse_json(response.content.strip())
        if parsed:
            return parsed.get("need_rewrite", True), parsed.get("reason", "")
    except Exception as e:
        logger.warning(f"HyDE判断失败，默认改写: {e}")

    return True, "判断失败，默认改写"


def hyde_rewrite(state: AgentState) -> dict:
    question = state.question or state.raw_question
    answer = state.answer or state.raw_answer

    if not question or not answer:
        return {"hyde_questions": [], "current_step": "hyde_rewrite"}

    cfg = get_config()
    hyde_cfg = cfg.get("hyde", {})
    num_questions = hyde_cfg.get("num_questions", 3)
    max_questions = hyde_cfg.get("max_questions_per_qa", 3)
    max_len = hyde_cfg.get("answer_summary_max_len", 150)

    num_questions = min(num_questions, max_questions)

    answer_summary = answer[:max_len] + ("..." if len(answer) > max_len else "")

    need_rewrite, reason = _judge_need_rewrite(question, answer_summary)
    if not need_rewrite:
        logger.info(f"跳过HyDE: {reason}, question={question[:30]}")
        return {"hyde_questions": [], "current_step": "hyde_rewrite"}

    hyde_examples = get_business_config("hyde_examples", "")
    if not hyde_examples:
        enterprise_name = get_business_config("enterprise_name", "ETC")
        hyde_examples = _HYDE_EXAMPLES_FALLBACK.replace("{{enterprise_name}}", enterprise_name)

    try:
        engine = get_prompt_engine()
        prompt = engine.render(
            "hyde",
            fallback=HYDE_PROMPT,
            question=question,
            answer_summary=answer_summary,
            num_questions=num_questions,
            hyde_examples=hyde_examples,
        )

        structured_llm, supported = get_structured_llm(HydeRewriteOutput)

        if supported:
            try:
                result = structured_llm.invoke([HumanMessage(content=prompt)])
                if isinstance(result, HydeRewriteOutput):
                    return {
                        "hyde_questions": result.questions[:num_questions],
                        "current_step": "hyde_rewrite",
                    }
            except Exception as e:

                logger.warning(f"HyDE改写结构化输出失败，降级为JSON解析: {e}")

        llm = get_llm()
        response = llm.invoke([HumanMessage(content=prompt)])
        content = response.content.strip()

        hyde_questions = [
            line.strip()
            for line in content.split("\n")
            if line.strip() and len(line.strip()) >= 3
        ][:num_questions]

        return {
            "hyde_questions": hyde_questions,
            "current_step": "hyde_rewrite",
        }
    except Exception as e:
        logger.error(f"HyDE改写失败: {e}")
        return {
            "hyde_questions": [],
            "error": f"HyDE改写失败: {e!s}",
            "current_step": "hyde_rewrite",
        }


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
