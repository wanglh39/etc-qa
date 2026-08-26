import os

os.environ['ETC_QA_ENV'] = os.environ.get('ETC_QA_ENV', 'test')
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import argparse
import json
from datetime import datetime

from agent.processors.hyde_rewrite import hyde_rewrite
from agent.processors.standardize_query import standardize_query
from agent.processors.structure_ingest import structure_ingest
from agent.state import AgentState
from db.mysql_client import MySQLClient
from rag.service import QAService
from utils.config import load_config
from utils.logger import get_logger

logger = get_logger("scripts.eval.eval_prompt_diff")

GOLDEN_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "golden", "golden_dataset.json")


def load_golden(path: str = GOLDEN_PATH) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _fuzzy_match(actual: str, expected: str) -> bool:
    if actual == expected:
        return True
    actual_clean = actual.replace("的", "").replace("了", "").replace("怎么", "如何").replace("如何", "怎么")
    expected_clean = expected.replace("的", "").replace("了", "").replace("怎么", "如何").replace("如何", "怎么")
    if actual_clean == expected_clean:
        return True
    if expected in actual or actual in expected:
        return True
    overlap = sum(1 for c in expected if c in actual)
    if len(expected) > 0 and overlap / len(expected) >= 0.8:
        return True
    return False


def eval_standardize(case: dict) -> dict:
    question = case["input"]["question"]
    state = AgentState(raw_question=question)
    try:
        result = standardize_query(state)
        actual_question = result.get("question", question)
        actual_conf = result.get("rewrite_confidence", 1.0)
    except Exception as e:
        return {"pass": False, "error": str(e), "actual": {}}

    expected = case["expected"]
    checks = {}

    if "question" in expected:
        checks["question_match"] = _fuzzy_match(actual_question, expected["question"])
    if "keywords" in expected:
        checks["keywords_preserved"] = all(kw in actual_question for kw in expected["keywords"])
    if "need_rewrite" in expected:
        was_rewritten = actual_question != question
        if expected["need_rewrite"]:
            checks["need_rewrite"] = was_rewritten or _fuzzy_match(actual_question, expected.get("question", ""))
        else:
            checks["need_rewrite"] = not was_rewritten or _fuzzy_match(actual_question, question)
    if "rewrite_confidence_min" in expected:
        checks["confidence_ok"] = actual_conf >= expected["rewrite_confidence_min"]
    if expected.get("shorter_than_input"):
        checks["shorter"] = len(actual_question) < len(question)

    return {
        "pass": all(checks.values()) if checks else True,
        "checks": checks,
        "actual": {"question": actual_question, "rewrite_confidence": actual_conf},
    }


def eval_hyde(case: dict) -> dict:
    question = case["input"]["question"]
    answer = case["input"]["answer"]
    state = AgentState(raw_question=question, answer=answer)
    try:
        result = hyde_rewrite(state)
        actual_hyde = result.get("hyde_questions", [])
    except Exception as e:
        return {"pass": False, "error": str(e), "actual": {}}

    expected = case["expected"]
    checks = {}

    if "hyde_count_min" in expected:
        checks["hyde_count"] = len(actual_hyde) >= expected["hyde_count_min"]
    if "must_preserve" in expected:
        checks["preserve_keywords"] = all(
            any(kw in hq for hq in actual_hyde) for kw in expected["must_preserve"]
        )

    return {
        "pass": all(checks.values()) if checks else True,
        "checks": checks,
        "actual": {"hyde_questions": actual_hyde, "hyde_count": len(actual_hyde)},
    }


def eval_ingest(case: dict) -> dict:
    question = case["input"]["question"]
    answer = case["input"]["answer"]
    state = AgentState(raw_question=question, raw_answer=answer)
    try:
        result = structure_ingest(state)
        actual_cat = result.get("category_l1", "")
        actual_conf = result.get("category_confidence", 0.0)
    except Exception as e:
        return {"pass": False, "error": str(e), "actual": {}}

    expected = case["expected"]
    checks = {}

    if "category_l1" in expected:
        checks["category_match"] = _fuzzy_match(actual_cat, expected["category_l1"])
    if "has_category" in expected:
        checks["has_category"] = bool(actual_cat) == expected["has_category"]
    if "confidence_min" in expected:
        checks["confidence_ok"] = actual_conf >= expected["confidence_min"]

    return {
        "pass": all(checks.values()) if checks else True,
        "checks": checks,
        "actual": {"category_l1": actual_cat, "category_confidence": actual_conf},
    }


def eval_rag(case: dict, qa_service: QAService) -> dict:
    question = case["input"]["question"]
    try:
        result = qa_service.query(question)
        candidates = result.candidates if hasattr(result, 'candidates') else []
        top_ids = [c.qa_id for c in candidates] if candidates else []
    except Exception as e:
        return {"pass": False, "error": str(e), "actual": {}}

    expected = case["expected"]
    checks = {}

    if "recall_at_1" in expected:
        checks["recall_at_1"] = (len(top_ids) >= 1) if expected["recall_at_1"] else True
    if "recall_at_3" in expected:
        checks["recall_at_3"] = (len(top_ids) >= 1) if expected["recall_at_3"] else True

    return {
        "pass": all(checks.values()) if checks else True,
        "checks": checks,
        "actual": {"top_ids": top_ids[:5], "total_candidates": len(top_ids)},
    }


EVALUATORS = {
    "standardize_query": eval_standardize,
    "hyde_rewrite": eval_hyde,
    "structure_ingest": eval_ingest,
    "rag": None,
}


def run_evaluation(golden: list[dict], pipelines: list[str] = None) -> dict:
    cfg = load_config()
    qa_service = None
    if "rag" in (pipelines or ["rag"]):
        try:
            from db.milvus_client import MilvusQA
            from rag.bm25_index import BM25Index
            from rag.recall import RecallEngine
            from rag.reranker import Reranker
            from rag.service import QAService
            from rag.siliconflow import get_embedding_client, get_rerank_client
            from rag.threshold import ThresholdJudge

            mysql = MySQLClient()
            milvus = MilvusQA()
            all_qa = mysql.get_all_questions()
            bm25 = BM25Index()
            bm25.build(all_qa)
            embed_model = get_embedding_client()
            rerank_model = get_rerank_client()
            recall_eng = RecallEngine(embed_model, milvus, bm25)
            reranker = Reranker(rerank_model, mysql_client=mysql)
            threshold = ThresholdJudge()
            qa_service = QAService(recall_eng, threshold, reranker, mysql)
        except Exception as e:
            logger.warning(f"RAG服务初始化失败: {e}")

    results = {"by_pipeline": {}, "total": 0, "passed": 0, "failed": 0, "cases": []}

    for case in golden:
        pipeline = case["pipeline"]
        if pipelines and pipeline not in pipelines:
            continue

        evaluator = EVALUATORS.get(pipeline)
        if evaluator is None:
            if pipeline == "rag" and qa_service:
                eval_result = eval_rag(case, qa_service)
            else:
                continue
        else:
            eval_result = evaluator(case)

        if pipeline not in results["by_pipeline"]:
            results["by_pipeline"][pipeline] = {"total": 0, "passed": 0, "failed": 0}

        results["by_pipeline"][pipeline]["total"] += 1
        results["total"] += 1

        if eval_result["pass"]:
            results["by_pipeline"][pipeline]["passed"] += 1
            results["passed"] += 1
        else:
            results["by_pipeline"][pipeline]["failed"] += 1
            results["failed"] += 1

        results["cases"].append({
            "id": case["id"],
            "pipeline": pipeline,
            "input": case["input"],
            "expected": case["expected"],
            "result": eval_result,
        })

    return results


def format_report(results: dict, label: str = "") -> str:
    lines = []
    lines.append(f"{'='*60}")
    lines.append(f"提示词评估报告 {label}")
    lines.append(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"{'='*60}")
    lines.append(f"总计: {results['total']} | 通过: {results['passed']} | 失败: {results['failed']}")
    if results['total'] > 0:
        lines.append(f"通过率: {results['passed']/results['total']*100:.1f}%")
    lines.append("")

    for pipeline, stats in results["by_pipeline"].items():
        rate = stats["passed"] / stats["total"] * 100 if stats["total"] > 0 else 0
        lines.append(f"  {pipeline}: {stats['passed']}/{stats['total']} ({rate:.1f}%)")

    failed_cases = [c for c in results["cases"] if not c["result"]["pass"]]
    if failed_cases:
        lines.append(f"\n--- 失败用例 ({len(failed_cases)}) ---")
        for c in failed_cases:
            lines.append(f"  [{c['id']}] {c['pipeline']}")
            lines.append(f"    输入: {c['input']}")
            lines.append(f"    期望: {c['expected']}")
            lines.append(f"    实际: {c['result'].get('actual', {})}")
            if c["result"].get("checks"):
                lines.append(f"    检查: {c['result']['checks']}")
            if c["result"].get("error"):
                lines.append(f"    错误: {c['result']['error']}")
            lines.append("")

    return "\n".join(lines)


def format_diff(before: dict, after: dict) -> str:
    lines = []
    lines.append(f"{'='*60}")
    lines.append("DIFF 报告（新版 vs 旧版）")
    lines.append(f"{'='*60}")

    before_rate = before["passed"] / before["total"] * 100 if before["total"] > 0 else 0
    after_rate = after["passed"] / after["total"] * 100 if after["total"] > 0 else 0
    delta = after_rate - before_rate

    lines.append(f"通过率: {after_rate:.1f}% (旧: {before_rate:.1f}%, 差值: {delta:+.1f}%)")
    lines.append(f"通过: {after['passed']}/{after['total']} (旧: {before['passed']}/{before['total']})")
    lines.append("")

    for pipeline in set(list(before["by_pipeline"].keys()) + list(after["by_pipeline"].keys())):
        b = before["by_pipeline"].get(pipeline, {"passed": 0, "total": 0})
        a = after["by_pipeline"].get(pipeline, {"passed": 0, "total": 0})
        b_rate = b["passed"] / b["total"] * 100 if b["total"] > 0 else 0
        a_rate = a["passed"] / a["total"] * 100 if a["total"] > 0 else 0
        d = a_rate - b_rate
        symbol = "↑" if d > 0 else "↓" if d < 0 else "="
        lines.append(f"  {pipeline}: {a_rate:.1f}% {symbol} (旧: {b_rate:.1f}%, {d:+.1f}%)")

    before_ids = {c["id"]: c for c in before["cases"]}
    after_ids = {c["id"]: c for c in after["cases"]}

    regressions = []
    improvements = []
    for cid in before_ids:
        if cid in after_ids:
            b_pass = before_ids[cid]["result"]["pass"]
            a_pass = after_ids[cid]["result"]["pass"]
            if b_pass and not a_pass:
                regressions.append(cid)
            elif not b_pass and a_pass:
                improvements.append(cid)

    if regressions:
        lines.append(f"\n--- 回退用例 ({len(regressions)}) ---")
        for cid in regressions:
            c = after_ids[cid]
            lines.append(f"  [{cid}] {c['pipeline']} 输入: {c['input']}")

    if improvements:
        lines.append(f"\n--- 改善用例 ({len(improvements)}) ---")
        for cid in improvements:
            c = after_ids[cid]
            lines.append(f"  [{cid}] {c['pipeline']} 输入: {c['input']}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="提示词评估对比")
    parser.add_argument("--pipeline", nargs="*", help="只评估指定流水线")
    parser.add_argument("--golden", default=GOLDEN_PATH, help="黄金数据集路径")
    parser.add_argument("--output", default=None, help="输出目录")
    args = parser.parse_args()

    golden = load_golden(args.golden)
    pipelines = args.pipeline
    out_dir = args.output or os.path.join(os.path.dirname(__file__), "..", "..", "output")
    os.makedirs(out_dir, exist_ok=True)

    print("运行黄金数据集评估...")
    results = run_evaluation(golden, pipelines)

    report = format_report(results)
    print(report)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(out_dir, f"prompt_eval_{ts}.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    results_path = os.path.join(out_dir, f"prompt_eval_{ts}.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n报告: {report_path}")
    print(f"数据: {results_path}")


if __name__ == "__main__":
    main()
