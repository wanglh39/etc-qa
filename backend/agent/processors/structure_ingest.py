import json
import random
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


def _get_mysql() -> MySQLClient:
    global _shared_mysql
    if _shared_mysql is None:
        _shared_mysql = MySQLClient()
    return _shared_mysql


def get_category_tree() -> dict:
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
        if result:
            _category_cache["tree"] = result
            _category_cache["default_l1"] = next(iter(result))
            _category_cache["default_l2"] = result[_category_cache["default_l1"]][0] if result[_category_cache["default_l1"]] else ""
        else:
            _category_cache["tree"] = {}
            _category_cache["default_l1"] = ""
            _category_cache["default_l2"] = ""
        return _category_cache["tree"]
    except Exception:
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
    _category_cache["tree"] = None
    _category_cache["tree_str"] = None
    _category_cache["default_l1"] = None
    _category_cache["default_l2"] = None


def invalidate_example_cache():
    _example_cache["examples"] = None


def get_reference_examples(count: int = 10) -> list[str]:
    if _example_cache["examples"] is not None:
        return _example_cache["examples"][:count]
    try:
        cfg = get_config().get("prompts", {}).get("standardize", {})
        min_len = cfg.get("min_length", 5)
        max_len = cfg.get("max_length", 30)
        mysql = _get_mysql()
        all_qa = mysql.get_all_questions()
        questions = [qa["question"] for qa in all_qa if qa.get("question") and min_len <= len(qa["question"]) <= max_len]
        if len(questions) > count * 3:
            sampled = random.sample(questions, count * 3)
        else:
            sampled = questions
        _example_cache["examples"] = sampled
        return sampled[:count]
    except Exception:
        _example_cache["examples"] = []
        return []


def _get_kw_lists() -> tuple:
    forbidden = get_business_config("forbidden_new_kws", [])
    must_preserve = get_business_config("must_preserve_kws", [])
    return forbidden, must_preserve


STRUCTURE_INGEST_PROMPT = """浣犳槸{{enterprise_name}}瀹㈡湇鐭ヨ瘑搴撶鐞嗗憳銆傝灏嗕互涓嬪伐鍗曟暟鎹鐞嗕负鐭ヨ瘑搴撴爣鍑嗘牸寮忥紝杈撳嚭JSON銆?
## 杈撳嚭瀛楁璇存槑
- question锛氱煡璇嗗簱鏍囧噯闂锛堟敼鍐欏悗鐩存帴鍚戦噺鍖栧瓨鍏ilvus锛屽繀椤讳笌鐜版湁闂椋庢牸涓€鑷达級
- answer锛氬瀹㈣瘽鏈紙闈㈠悜瀹㈡埛鐨勫洖绛旓紝绠€娲佹竻鏅帮紝鍖呭惈鍏抽敭澶勭悊缁撴灉锛?- category_l1锛氫竴绾у垎绫伙紙浠庡垎绫讳綋绯讳腑閫夋嫨锛?- category_l2锛氫簩绾у垎绫伙紙浠庡垎绫讳綋绯讳腑閫夋嫨锛?- internal_process锛氬唴閮ㄥ鐞嗗姙娉曞強娴佺▼锛堢粰瀹㈡湇鐪嬬殑鎿嶄綔姝ラ锛?- feedback_dept锛氭秹鍙婂弽棣堥儴闂?寰俊缇?宸ュ崟妯℃澘
- category_confidence锛氬垎绫荤疆淇″害锛?-1锛屽垎绫昏秺纭畾瓒婇珮锛?.5浠ヤ笅琛ㄧず涓嶇‘瀹氾級

## 鍒嗙被浣撶郴
{{category_tree}}

## 鍒嗙被閫夋嫨瑙勫垯
鏍规嵁闂鏍稿績璇夋眰閫夋嫨鏈€鍖归厤鐨勫垎绫伙紝涓嶈榛樿閫夌涓€涓細
- 鍏堝垽鏂棶棰樺睘浜庡摢涓笟鍔℃澘鍧楋紙鍞悗/鍞墠/璐︽埛/璐㈠姟...锛夛紝鍐嶉€変簩绾у垎绫?{{classify_examples}}

## 闂鏀瑰啓瑙勫垯
1. 闀垮害5-30瀛楋紝绠€鐭洿鎺ワ紝鎻愰棶寮?2. 鏍煎紡锛氫富璇?璇夋眰/鐤戦棶锛屽"XX鎬庝箞鍔炵悊锛?銆?XX鏄粈涔堝師鍥狅紵"
3. 鍘绘帀鍙欒堪鎬ф弿杩帮紙"鎴戜笂涓湀..."銆?鍚屼竴涓矾娈?.."绛夎儗鏅級锛屼繚鐣欐牳蹇冭瘔姹?4. 銆愬繀椤讳繚鐣欍€戝師闂涓殑鏍稿績涓氬姟鍏抽敭璇嶏細{{must_preserve_kws_str}}绛夛紝涓€涓兘涓嶈兘涓?5. 銆愮姝㈠紩鍏ャ€戜笉寰楀嚟绌哄紩鍏ュ師闂鏈彁鍙婄殑鍏ㄦ柊涓氬姟姒傚康
6. 淇濇寔鍘熼棶棰樼殑鏍稿績鎰忓浘涓嶅彉锛屼笉瑕佸亸绉诲埌鍏朵粬璇夋眰

## 绛旀缁撴瀯鍖栬鍒?1. answer鏄潰鍚戝鎴风殑鏈€缁堣瘽鏈紝绠€娲佹竻鏅帮紝鍖呭惈鍏抽敭澶勭悊缁撴灉
2. internal_process鏄鏈嶅唴閮ㄦ搷浣滄楠わ紝瀹㈡埛鐪嬩笉鍒?3. feedback_dept浠庡伐鍗曚笂涓嬫枃涓殑"娴佽浆鑷?瀛楁鎻愬彇锛屾病鏈夊垯鐣欑┖
4. "寰匵X宀?.."鏄唴閮ㄦ祦绋嬫斁internal_process锛屼笉鏄痑nswer

## 鍙傝€冪ず渚嬶紙鏉ヨ嚜鐪熷疄鐭ヨ瘑搴擄級
{{reference_examples}}

## 宸ュ崟鏁版嵁
闂鎻忚堪锛歿{question}}
澶勭悊缁撴灉锛歿{answer}}
{{context}}

## 杈撳嚭JSON"""


_CLASSIFY_EXAMPLES_FALLBACK = "- 绀轰緥锛氭墸璐?閫€娆?璐﹀崟鐩稿叧鈫掕处鍗曠被锛涜澶?OBU/钃濈墮鐩稿叧鈫掕澶囧紓甯革紱榛戝悕鍗?椋庢帶鐩稿叧鈫掗粦鍚嶅崟绫伙紱娉ㄩ攢/婵€娲?鎸傚け鐩稿叧鈫掍笟鍔″彉鏇寸被锛涘喕缁?瑙ｅ喕/璐︽埛鐩稿叧鈫掕处鎴风被"


def _validate_rewrite(original: str, rewrite: str) -> tuple:
    forbidden_new_kws, must_preserve_kws = _get_kw_lists()
    hallucination_kws = [kw for kw in forbidden_new_kws if kw in rewrite and kw not in original]
    lost_kws = [kw for kw in must_preserve_kws if kw in original and kw not in rewrite]
    return hallucination_kws, lost_kws


def _apply_confidence_action(cat_conf: float, cat_l1: str, cat_l2: str,
                              default_l1: str, default_l2: str,
                              review_highlights: list) -> tuple:
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
        review_highlights.append(f"鍒嗙被缃俊搴︿綆({cat_conf:.2f})锛屽缓璁汉宸ョ‘璁?)
    else:
        needs_review = True
        cat_l1 = default_l1
        cat_l2 = default_l2
        review_highlights.append(f"鍒嗙被缃俊搴︽瀬浣?{cat_conf:.2f})锛屼娇鐢ㄩ粯璁ゅ垎绫伙紝寤鸿浜哄伐纭")

    return cat_l1, cat_l2, needs_review


def structure_ingest(state: AgentState) -> dict:
    question = state.question or state.raw_question
    answer = state.answer or state.raw_answer

    context = ""
    if state.work_order_context:
        context = f"宸ュ崟涓婁笅鏂囷細{state.work_order_context}"

    tree = get_category_tree()
    tree_str = get_category_tree_str()
    default_l1 = _category_cache["default_l1"] or ""
    default_l2 = _category_cache["default_l2"] or ""

    _, must_preserve_kws = _get_kw_lists()

    sample_count = get_business_config("reference_sample_count", 10)
    examples = get_reference_examples(sample_count)
    reference_examples = "\n".join(f'- "{ex}"' for ex in examples) if examples else "锛堟棤鍙傝€冪ず渚嬶級"

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
            must_preserve_kws_str="銆?.join(must_preserve_kws),
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

                logger.warning(f"缁撴瀯鍖栬緭鍑鸿皟鐢ㄥけ璐ワ紝闄嶇骇涓篔SON瑙ｆ瀽: {e}")

        llm = get_llm()
        response = llm.invoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        parsed = _parse_json(content)
        if parsed:
            return _process_parsed_result(parsed, question, answer, tree, default_l1, default_l2, state)

    except Exception as e:
        logger.error(f"LLM瑙勬暣澶辫触: {e}")
        return {
            "question": question,
            "answer": answer,
            "category_l1": default_l1,
            "category_l2": default_l2,
            "category_confidence": 0.3,
            "internal_process": "",
            "feedback_dept": "",
            "error": f"LLM瑙勬暣澶辫触: {e!s}",
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


def _process_structured_result(result: StructureIngestOutput, question: str, answer: str,
                                tree: dict, default_l1: str, default_l2: str, state: AgentState) -> dict:
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
        review_highlights.append(f"鏀瑰啓寮曞叆涓嶅瓨鍦ㄧ殑鍏抽敭璇峽hallucination_kws}锛屽凡鍥為€€涓哄師濮嬮棶棰?)

    if lost_kws and not hallucination_kws:
        needs_review = True
        review_highlights.append(f"鏀瑰啓涓㈠け鍏抽敭璇峽lost_kws}锛屽缓璁汉宸ョ‘璁?)

    std_cfg = get_business_config("standardize", {})
    rewrite_min_len = std_cfg.get("rewrite_min_length", 3) if isinstance(std_cfg, dict) else 3
    if not rewritten or len(rewritten) < rewrite_min_len:
        rewritten = question
        needs_review = True
        review_highlights.append("闂鏀瑰啓缁撴灉杩囩煭锛屽缓璁汉宸ョ‘璁?)

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


def _process_parsed_result(parsed: dict, question: str, answer: str,
                            tree: dict, default_l1: str, default_l2: str, state: AgentState) -> dict:
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
        review_highlights.append(f"鏀瑰啓寮曞叆涓嶅瓨鍦ㄧ殑鍏抽敭璇峽hallucination_kws}锛屽凡鍥為€€涓哄師濮嬮棶棰?)

    if lost_kws and not hallucination_kws:
        needs_review = True
        review_highlights.append(f"鏀瑰啓涓㈠け鍏抽敭璇峽lost_kws}锛屽缓璁汉宸ョ‘璁?)

    std_cfg = get_business_config("standardize", {})
    rewrite_min_len = std_cfg.get("rewrite_min_length", 3) if isinstance(std_cfg, dict) else 3
    if not rewritten or len(rewritten) < rewrite_min_len:
        rewritten = question
        needs_review = True
        review_highlights.append("闂鏀瑰啓缁撴灉杩囩煭锛屽缓璁汉宸ョ‘璁?)

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