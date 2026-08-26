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

from agent.processors.clean_text import clean_text
from agent.processors.structure_ingest import get_category_tree, structure_ingest
from agent.state import AgentState
from db.milvus_client import MilvusQA
from db.mysql_client import MySQLClient
from rag.bm25_index import BM25Index
from rag.recall import RecallEngine
from rag.siliconflow import get_embedding_client
from utils.config import load_config
from utils.config_center import get_business_config

cfg = load_config()
embed_model = get_embedding_client()

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

CORE_KEYWORDS = get_business_config("must_preserve_kws", ["ETC", "etc", "扣费", "退款", "注销", "激活"])
INTERNAL_PROCESS_KEYWORDS = get_business_config("internal_process_keywords", ["核实", "待", "安排", "引导", "手动"])

WO_TYPE_TO_L1 = get_business_config("wo_type_to_l1", {
    "收款对账-划扣": "售后业务",
    "退款申请": "售后业务",
    "通行异常/多扣费": "售后业务",
    "通行异常/少扣费": "售后业务",
    "通行异常/未扣费": "售后业务",
    "设备邮寄/更换": "售后业务",
    "设备激活/异常": "售前业务",
    "ETC注销": "售后业务",
    "ETC变更": "售后业务",
    "车队权限/其他": "售后业务",
    "账单查询": "售后业务",
    "投诉/其他": "其它",
    "发票申请": "售后业务",
    "黑名单查询": "售后业务",
    "通行异常/其他": "售后业务",
})


def load_work_orders(csv_path, limit=None):
    rows = []
    with open(csv_path, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if limit and i >= limit:
                break
            desc = row.get("问题描述", "").strip()
            result = row.get("处理结果/备注", "").strip()
            wo_type = row.get("工单类型", "").strip()
            dept = row.get("流转至", "").strip()
            if not desc:
                continue
            question = re.sub(r"客户.{0,10}?[（(].{2,30}?[）)]反馈[：:]", "", desc).strip()
            if not question:
                question = desc
            rows.append({
                "id": i,
                "raw_question": desc,
                "question": question,
                "answer": result,
                "work_order_type": wo_type,
                "work_order_context": f"工单类型={wo_type}，流转至={dept}",
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
        has_question_mark = "？" in q or "?" in q
        no_narrative = not bool(re.search(r"我[上这那本]?[个月星期年周]", q))
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
    print("structure_ingest 质量评估")
    print("=" * 60)

    work_orders = load_work_orders(WORK_ORDER_CSV, limit=limit)
    if sample and sample < len(work_orders):
        indices = np.random.choice(len(work_orders), sample, replace=False)
        indices.sort()
        work_orders = [work_orders[i] for i in indices]
    print(f"工单数量: {len(work_orders)}")

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
                "category_l1": "咨询类",
                "category_l2": "业务咨询",
                "needs_review": True,
            })

        if (i + 1) % 10 == 0:
            print(f"  已处理 {i + 1}/{len(work_orders)}")
        time.sleep(0.5)

    print(f"\nJSON解析成功率: {parse_success}/{len(work_orders)} = {parse_success/len(work_orders)*100:.1f}%")
    if parse_fail > 0:
        print(f"  解析失败: {parse_fail}条")
        for e in errors[:5]:
            print(f"    - {e['raw'][:30]}: {e['error'][:50]}")

    rewrites = [o["rewritten_question"] for o in outputs]

    print("\n--- 检索增益（原始问题 vs 改写后问题，Top3 L1命中工单期望分类） ---")
    raw_hit, rw_hit, raw_better, rw_better, same, total, gain_details = eval_retrieval_gain(
        outputs, work_orders, recall_eng, embed_model, qa_pairs_dict
    )
    print(f"  可评估工单数: {total}（有工单类型→L1映射的）")
    print(f"  原始问题Top3命中: {raw_hit}/{total} ({raw_hit/total*100:.1f}%)")
    print(f"  改写后Top3命中:  {rw_hit}/{total} ({rw_hit/total*100:.1f}%)")
    print(f"  改写更好: {rw_better}条 | 原始更好: {raw_better}条 | 相同: {same}条")
    if rw_better > 0 or raw_better > 0:
        print(f"  净增益: {rw_better - raw_better}条 ({(rw_better - raw_better)/total*100:.1f}%)")
    gain_examples = [d for d in gain_details if d["rewrite_hit"] and not d["raw_hit"]][:3]
    if gain_examples:
        print("  改写增益示例:")
        for g in gain_examples:
            print(f"    原始: {g['raw_question']} → Top3L1={g['raw_top3_l1']}")
            print(f"    改写: {g['rewritten']} → Top3L1={g['rewrite_top3_l1']} (期望={g['expected_l1']})")

    print("\n--- 分类一致性（LLM输出L1 vs 工单类型映射L1） ---")
    cat_match, cat_total, mismatch_examples = eval_category_consistency(outputs, work_orders)
    print(f"  一致率: {cat_match}/{cat_total} ({cat_match/cat_total*100:.1f}%)")
    if mismatch_examples:
        print("  不一致示例:")
        for m in mismatch_examples[:5]:
            print(f"    工单类型={m['wo_type']}→期望L1={m['expected_l1']}, 实际L1={m['actual_l1']}, 问题={m['question']}")

    format_results = eval_format_quality(rewrites)
    format_scores = [r["format_score"] for r in format_results]
    print("\n--- 格式规范度 ---")
    print(f"  平均: {np.mean(format_scores):.4f}")
    length_ok_count = sum(r["length_ok"] for r in format_results)
    qmark_count = sum(r["has_question_mark"] for r in format_results)
    no_narr_count = sum(r["no_narrative"] for r in format_results)
    core_kw_count = sum(r["has_core_keyword"] for r in format_results)
    print(f"  长度5-30字: {length_ok_count}/{len(format_results)} ({length_ok_count/len(format_results)*100:.1f}%)")
    print(f"  含疑问词/？: {qmark_count}/{len(format_results)} ({qmark_count/len(format_results)*100:.1f}%)")
    print(f"  无叙述性描述: {no_narr_count}/{len(format_results)} ({no_narr_count/len(format_results)*100:.1f}%)")
    print(f"  含核心业务词: {core_kw_count}/{len(format_results)} ({core_kw_count/len(format_results)*100:.1f}%)")

    categories_l1 = [o["category_l1"] for o in outputs]
    categories_l2 = [o["category_l2"] for o in outputs]
    cat_results = eval_category(categories_l1, categories_l2)
    l1_valid = sum(r["l1_valid"] for r in cat_results)
    l2_valid = sum(r["l2_valid"] for r in cat_results)
    print("\n--- 分类合理性（L1/L2是否在分类体系中） ---")
    print(f"  category_l1有效: {l1_valid}/{len(cat_results)} ({l1_valid/len(cat_results)*100:.1f}%)")
    print(f"  category_l2有效: {l2_valid}/{len(cat_results)} ({l2_valid/len(cat_results)*100:.1f}%)")
    l1_dist = Counter(categories_l1)
    print(f"  category_l1分布: {dict(l1_dist)}")

    raw_answers = [o["raw_answer"] for o in outputs]
    answers = [o["answer"] for o in outputs]
    internal_processes = [o["internal_process"] for o in outputs]
    feedback_depts = [o["feedback_dept"] for o in outputs]
    ans_results = eval_answer_structure(answers, internal_processes, feedback_depts, raw_answers)
    ans_nonempty = sum(r["answer_nonempty"] for r in ans_results)
    ip_separated = sum(r["internal_process_separated"] for r in ans_results)
    fd_extracted = sum(r["feedback_dept_extracted"] for r in ans_results)
    has_internal_kw = sum(r["has_internal_action_kw"] for r in ans_results)
    print("\n--- 答案结构化质量 ---")
    print(f"  answer非空: {ans_nonempty}/{len(ans_results)} ({ans_nonempty/len(ans_results)*100:.1f}%)")
    print(f"  internal_process已分离: {ip_separated}/{len(ans_results)} ({ip_separated/len(ans_results)*100:.1f}%)")
    print(f"  feedback_dept已提取: {fd_extracted}/{len(ans_results)} ({fd_extracted/len(ans_results)*100:.1f}%)")
    print(f"  含内部操作关键词: {has_internal_kw}/{len(ans_results)} ({has_internal_kw/len(ans_results)*100:.1f}%)")

    review_count = sum(1 for o in outputs if o.get("needs_review"))
    print("\n--- 需人工审核 ---")
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

    print(f"\n报告已保存: {report_path}")
    print(f"详情已保存: {details_path}")

    print("\n" + "=" * 60)
    print("评估总结")
    print("=" * 60)
    print(f"  JSON解析成功率:    {report['parse_success_rate']*100:.1f}%")
    print(f"  检索增益(改写-原始): {report['retrieval_gain']['net_gain_rate']*100:.1f}% ({report['retrieval_gain']['net_gain']}条)")
    print(f"  分类一致性:        {report['category_consistency']['rate']*100:.1f}%")
    print(f"  格式规范度:        {report['format']['mean']*100:.1f}%")
    print(f"  分类L1有效:        {report['category_validity']['l1_valid_rate']*100:.1f}%")
    print(f"  分类L2有效:        {report['category_validity']['l2_valid_rate']*100:.1f}%")
    print(f"  答案非空:          {report['answer_structure']['answer_nonempty_rate']*100:.1f}%")
    print(f"  内部流程已分离:     {report['answer_structure']['internal_process_separated_rate']*100:.1f}%")


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    sample = int(sys.argv[2]) if len(sys.argv) > 2 else None
    run_eval(limit=limit, sample=sample)
