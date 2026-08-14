import os

os.environ['ETC_QA_ENV'] = os.environ.get('ETC_QA_ENV', 'test')
import sys

sys.path.insert(0, '.')
import csv
import json
import re
import time
from collections import Counter

import numpy as np
from sentence_transformers import SentenceTransformer

from agent.processors.clean_text import clean_text
from agent.processors.structure_ingest import get_category_tree, structure_ingest
from agent.state import AgentState
from db.milvus_client import MilvusQA
from db.mysql_client import MySQLClient
from rag.bm25_index import BM25Index
from rag.recall import RecallEngine
from utils.config import load_config
from utils.config_center import get_business_config

cfg = load_config()
embed_model = SentenceTransformer(cfg["models"]["embed"]["path"])

mysql = MySQLClient()
milvus = MilvusQA()
all_qa = mysql.get_all_questions()
bm25 = BM25Index()
bm25.build(all_qa)
qa_pairs_dict = {qa["id"]: qa for qa in all_qa}
recall_eng = RecallEngine(embed_model, milvus, bm25)

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
WORK_ORDER_CSV = os.path.join(PROJECT_ROOT, cfg.get("data", {}).get("work_order_csv", "data/eval/work_orders_200.csv"))
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)

CORE_KEYWORDS = get_business_config("must_preserve_kws", ["ETC", "etc", "鎵ｈ垂", "閫€娆?, "娉ㄩ攢", "婵€娲?])
INTERNAL_PROCESS_KEYWORDS = get_business_config("internal_process_keywords", ["鏍稿疄", "寰?, "瀹夋帓", "寮曞", "鎵嬪姩"])

WO_TYPE_TO_L1 = get_business_config("wo_type_to_l1", {
    "鏀舵瀵硅处-鍒掓墸": "鍞悗涓氬姟",
    "閫€娆剧敵璇?: "鍞悗涓氬姟",
    "閫氳寮傚父/澶氭墸璐?: "鍞悗涓氬姟",
    "閫氳寮傚父/灏戞墸璐?: "鍞悗涓氬姟",
    "閫氳寮傚父/鏈墸璐?: "鍞悗涓氬姟",
    "璁惧閭瘎/鏇存崲": "鍞悗涓氬姟",
    "璁惧婵€娲?寮傚父": "鍞墠涓氬姟",
    "ETC娉ㄩ攢": "鍞悗涓氬姟",
    "ETC鍙樻洿": "鍞悗涓氬姟",
    "杞﹂槦鏉冮檺/鍏朵粬": "鍞悗涓氬姟",
    "璐﹀崟鏌ヨ": "鍞悗涓氬姟",
    "鎶曡瘔/鍏朵粬": "鍏跺畠",
    "鍙戠エ鐢宠": "鍞悗涓氬姟",
    "榛戝悕鍗曟煡璇?: "鍞悗涓氬姟",
    "閫氳寮傚父/鍏朵粬": "鍞悗涓氬姟",
})


def load_work_orders(csv_path, limit=None):
    rows = []
    with open(csv_path, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if limit and i >= limit:
                break
            desc = row.get("闂鎻忚堪", "").strip()
            result = row.get("澶勭悊缁撴灉/澶囨敞", "").strip()
            wo_type = row.get("宸ュ崟绫诲瀷", "").strip()
            dept = row.get("娴佽浆鑷?, "").strip()
            if not desc:
                continue
            question = re.sub(r"瀹㈡埛.{0,10}?[锛?].{2,30}?[锛?]鍙嶉[锛?]", "", desc).strip()
            if not question:
                question = desc
            rows.append({
                "id": i,
                "raw_question": desc,
                "question": question,
                "answer": result,
                "work_order_type": wo_type,
                "work_order_context": f"宸ュ崟绫诲瀷={wo_type}锛屾祦杞嚦={dept}",
            })
    return rows


def _recall_and_get_l1(query_text, query_vec, recall_eng, qa_pairs_dict, top_k=3):
    results = recall_eng.recall(query_text, query_vec, use_hyde=False)
    if not results:
        return [], ""
    top_l1s = []
    for qid, _ in results[:top_k]:
        qa = qa_pairs_dict.get(qid, {})
        top_l1s.append(qa.get("category_l1", ""))
    return top_l1s, top_l1s[0] if top_l1s else ""


def eval_retrieval_gain(outputs, work_orders, recall_eng, embed_model, qa_pairs_dict):
    raw_l1_match = 0
    rewrite_l1_match = 0
    raw_better = 0
    rewrite_better = 0
    same = 0
    total = 0
    details = []

    for i, o in enumerate(outputs):
        rw = o["rewritten_question"]
        raw_q = o["raw_question"]
        if not rw or len(rw) < 3 or not raw_q:
            continue

        wo = work_orders[i]
        expected_l1 = WO_TYPE_TO_L1.get(wo.get("work_order_type", ""), None)
        if not expected_l1:
            continue

        total += 1

        raw_vec = embed_model.encode(
            [cfg["models"]["query_prefix"] + raw_q], normalize_embeddings=True
        ).tolist()[0]
        raw_top_l1s, raw_top1_l1 = _recall_and_get_l1(raw_q, raw_vec, recall_eng, qa_pairs_dict)

        rw_vec = embed_model.encode(
            [cfg["models"]["query_prefix"] + rw], normalize_embeddings=True
        ).tolist()[0]
        rw_top_l1s, rw_top1_l1 = _recall_and_get_l1(rw, rw_vec, recall_eng, qa_pairs_dict)

        raw_hit = expected_l1 in raw_top_l1s
        rw_hit = expected_l1 in rw_top_l1s

        if raw_hit:
            raw_l1_match += 1
        if rw_hit:
            rewrite_l1_match += 1

        if rw_hit and not raw_hit:
            rewrite_better += 1
        elif raw_hit and not rw_hit:
            raw_better += 1
        else:
            same += 1

        details.append({
            "raw_question": raw_q[:40],
            "rewritten": rw[:30],
            "expected_l1": expected_l1,
            "raw_top3_l1": raw_top_l1s,
            "rewrite_top3_l1": rw_top_l1s,
            "raw_hit": raw_hit,
            "rewrite_hit": rw_hit,
        })

    return raw_l1_match, rewrite_l1_match, raw_better, rewrite_better, same, total, details


def eval_category_consistency(outputs, work_orders):
    match = 0
    mismatch_examples = []
    total = 0

    for i, o in enumerate(outputs):
        wo = work_orders[i]
        wo_type = wo.get("work_order_type", "")
        expected_l1 = WO_TYPE_TO_L1.get(wo_type, None)
        if not expected_l1:
            continue
        total += 1
        if o["category_l1"] == expected_l1:
            match += 1
        else:
            if len(mismatch_examples) < 10:
                mismatch_examples.append({
                    "wo_type": wo_type,
                    "expected_l1": expected_l1,
                    "actual_l1": o["category_l1"],
                    "question": o["rewritten_question"][:30],
                })

    return match, total, mismatch_examples


def eval_format_quality(questions):
    results = []
    for q in questions:
        length = len(q)
        has_question_mark = "锛? in q or "?" in q
        no_narrative = not bool(re.search(r"鎴慬涓婅繖閭ｆ湰]?[涓湀鏄熸湡骞村懆]", q))
        has_core_kw = any(kw in q for kw in CORE_KEYWORDS)
        length_ok = 5 <= length <= 30
        results.append({
            "length": length,
            "length_ok": length_ok,
            "has_question_mark": has_question_mark,
            "no_narrative": no_narrative,
            "has_core_keyword": has_core_kw,
            "format_score": sum([length_ok, has_question_mark, no_narrative, has_core_kw]) / 4,
        })
    return results


def eval_category(categories_l1, categories_l2):
    tree = get_category_tree()
    results = []
    for l1, l2 in zip(categories_l1, categories_l2):
        l1_valid = l1 in tree
        l2_valid = l1_valid and l2 in tree.get(l1, [])
        results.append({"l1_valid": l1_valid, "l2_valid": l2_valid})
    return results


def eval_answer_structure(answers, internal_processes, feedback_depts, raw_answers):
    results = []
    for ans, ip, fd, raw in zip(answers, internal_processes, feedback_depts, raw_answers):
        ans_nonempty = len(ans.strip()) > 0
        ip_separated = bool(ip.strip()) and ip.strip() != ans.strip()
        fd_extracted = bool(fd.strip())
        has_internal_kw = any(kw in (ip or "") for kw in INTERNAL_PROCESS_KEYWORDS)
        results.append({
            "answer_nonempty": ans_nonempty,
            "internal_process_separated": ip_separated,
            "feedback_dept_extracted": fd_extracted,
            "has_internal_action_kw": has_internal_kw,
        })
    return results


def run_eval(limit=None, sample=None):
    print("=" * 60)
    print("structure_ingest 璐ㄩ噺璇勪及")
    print("=" * 60)

    work_orders = load_work_orders(WORK_ORDER_CSV, limit=limit)
    if sample and sample < len(work_orders):
        indices = np.random.choice(len(work_orders), sample, replace=False)
        indices.sort()
        work_orders = [work_orders[i] for i in indices]
    print(f"宸ュ崟鏁伴噺: {len(work_orders)}")

    outputs = []
    parse_success = 0
    parse_fail = 0
    errors = []

    for i, wo in enumerate(work_orders):
        state = AgentState(
            raw_question=wo["raw_question"],
            raw_answer=wo["answer"],
            raw_context=wo.get("work_order_context", ""),
        )
        state = AgentState(**{**state.model_dump(), "work_order_context": wo.get("work_order_context", "")})
        cleaned = clean_text(state)
        state.question = cleaned["question"]
        state.answer = cleaned.get("answer", state.raw_answer)

        try:
            result = structure_ingest(state)
            if result.get("error"):
                parse_fail += 1
                errors.append({"id": wo["id"], "error": result["error"], "raw": wo["raw_question"]})
            else:
                parse_success += 1
            outputs.append({
                "id": wo["id"],
                "raw_question": wo["raw_question"],
                "cleaned_question": state.question,
                "rewritten_question": result.get("question", ""),
                "raw_answer": wo["answer"],
                "answer": result.get("answer", ""),
                "internal_process": result.get("internal_process", ""),
                "feedback_dept": result.get("feedback_dept", ""),
                "category_l1": result.get("category_l1", ""),
                "category_l2": result.get("category_l2", ""),
                "needs_review": result.get("needs_review", False),
            })
        except Exception as e:
            parse_fail += 1
            errors.append({"id": wo["id"], "error": str(e), "raw": wo["raw_question"]})
            outputs.append({
                "id": wo["id"],
                "raw_question": wo["raw_question"],
                "cleaned_question": state.question,
                "rewritten_question": state.question,
                "raw_answer": wo["answer"],
                "answer": wo["answer"],
                "internal_process": "",
                "feedback_dept": "",
                "category_l1": "鍜ㄨ绫?,
                "category_l2": "涓氬姟鍜ㄨ",
                "needs_review": True,
            })

        if (i + 1) % 10 == 0:
            print(f"  宸插鐞?{i + 1}/{len(work_orders)}")
        time.sleep(0.5)

    print(f"\nJSON瑙ｆ瀽鎴愬姛鐜? {parse_success}/{len(work_orders)} = {parse_success/len(work_orders)*100:.1f}%")
    if parse_fail > 0:
        print(f"  瑙ｆ瀽澶辫触: {parse_fail}鏉?)
        for e in errors[:5]:
            print(f"    - {e['raw'][:30]}: {e['error'][:50]}")

    rewrites = [o["rewritten_question"] for o in outputs]

    print("\n--- 妫€绱㈠鐩婏紙鍘熷闂 vs 鏀瑰啓鍚庨棶棰橈紝Top3 L1鍛戒腑宸ュ崟鏈熸湜鍒嗙被锛?---")
    raw_hit, rw_hit, raw_better, rw_better, same, total, gain_details = eval_retrieval_gain(
        outputs, work_orders, recall_eng, embed_model, qa_pairs_dict
    )
    print(f"  鍙瘎浼板伐鍗曟暟: {total}锛堟湁宸ュ崟绫诲瀷鈫扡1鏄犲皠鐨勶級")
    print(f"  鍘熷闂Top3鍛戒腑: {raw_hit}/{total} ({raw_hit/total*100:.1f}%)")
    print(f"  鏀瑰啓鍚嶵op3鍛戒腑:  {rw_hit}/{total} ({rw_hit/total*100:.1f}%)")
    print(f"  鏀瑰啓鏇村ソ: {rw_better}鏉?| 鍘熷鏇村ソ: {raw_better}鏉?| 鐩稿悓: {same}鏉?)
    if rw_better > 0 or raw_better > 0:
        print(f"  鍑€澧炵泭: {rw_better - raw_better}鏉?({(rw_better - raw_better)/total*100:.1f}%)")
    gain_examples = [d for d in gain_details if d["rewrite_hit"] and not d["raw_hit"]][:3]
    if gain_examples:
        print("  鏀瑰啓澧炵泭绀轰緥:")
        for g in gain_examples:
            print(f"    鍘熷: {g['raw_question']} 鈫?Top3L1={g['raw_top3_l1']}")
            print(f"    鏀瑰啓: {g['rewritten']} 鈫?Top3L1={g['rewrite_top3_l1']} (鏈熸湜={g['expected_l1']})")

    print("\n--- 鍒嗙被涓€鑷存€э紙LLM杈撳嚭L1 vs 宸ュ崟绫诲瀷鏄犲皠L1锛?---")
    cat_match, cat_total, mismatch_examples = eval_category_consistency(outputs, work_orders)
    print(f"  涓€鑷寸巼: {cat_match}/{cat_total} ({cat_match/cat_total*100:.1f}%)")
    if mismatch_examples:
        print("  涓嶄竴鑷寸ず渚?")
        for m in mismatch_examples[:5]:
            print(f"    宸ュ崟绫诲瀷={m['wo_type']}鈫掓湡鏈汱1={m['expected_l1']}, 瀹為檯L1={m['actual_l1']}, 闂={m['question']}")

    format_results = eval_format_quality(rewrites)
    format_scores = [r["format_score"] for r in format_results]
    print("\n--- 鏍煎紡瑙勮寖搴?---")
    print(f"  骞冲潎: {np.mean(format_scores):.4f}")
    length_ok_count = sum(r["length_ok"] for r in format_results)
    qmark_count = sum(r["has_question_mark"] for r in format_results)
    no_narr_count = sum(r["no_narrative"] for r in format_results)
    core_kw_count = sum(r["has_core_keyword"] for r in format_results)
    print(f"  闀垮害5-30瀛? {length_ok_count}/{len(format_results)} ({length_ok_count/len(format_results)*100:.1f}%)")
    print(f"  鍚枒闂瘝/锛? {qmark_count}/{len(format_results)} ({qmark_count/len(format_results)*100:.1f}%)")
    print(f"  鏃犲彊杩版€ф弿杩? {no_narr_count}/{len(format_results)} ({no_narr_count/len(format_results)*100:.1f}%)")
    print(f"  鍚牳蹇冧笟鍔¤瘝: {core_kw_count}/{len(format_results)} ({core_kw_count/len(format_results)*100:.1f}%)")

    categories_l1 = [o["category_l1"] for o in outputs]
    categories_l2 = [o["category_l2"] for o in outputs]
    cat_results = eval_category(categories_l1, categories_l2)
    l1_valid = sum(r["l1_valid"] for r in cat_results)
    l2_valid = sum(r["l2_valid"] for r in cat_results)
    print("\n--- 鍒嗙被鍚堢悊鎬э紙L1/L2鏄惁鍦ㄥ垎绫讳綋绯讳腑锛?---")
    print(f"  category_l1鏈夋晥: {l1_valid}/{len(cat_results)} ({l1_valid/len(cat_results)*100:.1f}%)")
    print(f"  category_l2鏈夋晥: {l2_valid}/{len(cat_results)} ({l2_valid/len(cat_results)*100:.1f}%)")
    l1_dist = Counter(categories_l1)
    print(f"  category_l1鍒嗗竷: {dict(l1_dist)}")

    raw_answers = [o["raw_answer"] for o in outputs]
    answers = [o["answer"] for o in outputs]
    internal_processes = [o["internal_process"] for o in outputs]
    feedback_depts = [o["feedback_dept"] for o in outputs]
    ans_results = eval_answer_structure(answers, internal_processes, feedback_depts, raw_answers)
    ans_nonempty = sum(r["answer_nonempty"] for r in ans_results)
    ip_separated = sum(r["internal_process_separated"] for r in ans_results)
    fd_extracted = sum(r["feedback_dept_extracted"] for r in ans_results)
    has_internal_kw = sum(r["has_internal_action_kw"] for r in ans_results)
    print("\n--- 绛旀缁撴瀯鍖栬川閲?---")
    print(f"  answer闈炵┖: {ans_nonempty}/{len(ans_results)} ({ans_nonempty/len(ans_results)*100:.1f}%)")
    print(f"  internal_process宸插垎绂? {ip_separated}/{len(ans_results)} ({ip_separated/len(ans_results)*100:.1f}%)")
    print(f"  feedback_dept宸叉彁鍙? {fd_extracted}/{len(ans_results)} ({fd_extracted/len(ans_results)*100:.1f}%)")
    print(f"  鍚唴閮ㄦ搷浣滃叧閿瘝: {has_internal_kw}/{len(ans_results)} ({has_internal_kw/len(ans_results)*100:.1f}%)")

    review_count = sum(1 for o in outputs if o.get("needs_review"))
    print("\n--- 闇€浜哄伐瀹℃牳 ---")
    print(f"  {review_count}/{len(outputs)} ({review_count/len(outputs)*100:.1f}%)")

    report = {
        "total": len(work_orders),
        "parse_success_rate": parse_success / len(work_orders),
        "retrieval_gain": {
            "raw_top3_hit": raw_hit / total if total else 0,
            "rewrite_top3_hit": rw_hit / total if total else 0,
            "rewrite_better": rw_better,
            "raw_better": raw_better,
            "net_gain": rw_better - raw_better,
            "net_gain_rate": (rw_better - raw_better) / total if total else 0,
        },
        "category_consistency": {
            "rate": cat_match / cat_total if cat_total else 0,
        },
        "format": {
            "mean": float(np.mean(format_scores)),
            "length_ok_rate": length_ok_count / len(format_results),
            "question_mark_rate": qmark_count / len(format_results),
            "no_narrative_rate": no_narr_count / len(format_results),
            "core_keyword_rate": core_kw_count / len(format_results),
        },
        "category_validity": {
            "l1_valid_rate": l1_valid / len(cat_results),
            "l2_valid_rate": l2_valid / len(cat_results),
            "l1_distribution": dict(l1_dist),
        },
        "answer_structure": {
            "answer_nonempty_rate": ans_nonempty / len(ans_results),
            "internal_process_separated_rate": ip_separated / len(ans_results),
            "feedback_dept_extracted_rate": fd_extracted / len(ans_results),
            "has_internal_kw_rate": has_internal_kw / len(ans_results),
        },
        "review_rate": review_count / len(outputs),
    }
    report_path = os.path.join(OUTPUT_DIR, "eval_structure_ingest_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    details_path = os.path.join(OUTPUT_DIR, "eval_structure_ingest_details.json")
    with open(details_path, "w", encoding="utf-8") as f:
        json.dump(outputs, f, ensure_ascii=False, indent=2)

    print(f"\n鎶ュ憡宸蹭繚瀛? {report_path}")
    print(f"璇︽儏宸蹭繚瀛? {details_path}")

    print("\n" + "=" * 60)
    print("璇勪及鎬荤粨")
    print("=" * 60)
    print(f"  JSON瑙ｆ瀽鎴愬姛鐜?    {report['parse_success_rate']*100:.1f}%")
    print(f"  妫€绱㈠鐩?鏀瑰啓-鍘熷): {report['retrieval_gain']['net_gain_rate']*100:.1f}% ({report['retrieval_gain']['net_gain']}鏉?")
    print(f"  鍒嗙被涓€鑷存€?        {report['category_consistency']['rate']*100:.1f}%")
    print(f"  鏍煎紡瑙勮寖搴?        {report['format']['mean']*100:.1f}%")
    print(f"  鍒嗙被L1鏈夋晥:        {report['category_validity']['l1_valid_rate']*100:.1f}%")
    print(f"  鍒嗙被L2鏈夋晥:        {report['category_validity']['l2_valid_rate']*100:.1f}%")
    print(f"  绛旀闈炵┖:          {report['answer_structure']['answer_nonempty_rate']*100:.1f}%")
    print(f"  鍐呴儴娴佺▼宸插垎绂?     {report['answer_structure']['internal_process_separated_rate']*100:.1f}%")


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    sample = int(sys.argv[2]) if len(sys.argv) > 2 else None
    run_eval(limit=limit, sample=sample)