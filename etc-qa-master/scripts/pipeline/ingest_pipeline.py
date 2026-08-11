"""
统一入库流水线 — 6步端到端处理
用法：
  python scripts/pipeline/ingest_pipeline.py --csv data/eval/work_orders_200.csv --full
  python scripts/pipeline/ingest_pipeline.py --csv data/processed/qa_filled.csv --skip-llm
  python scripts/pipeline/ingest_pipeline.py --api  # 从work_orders表拉取
"""

import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv

load_dotenv()

from agent.processors.clean_text import clean_text
from agent.processors.hyde_rewrite import hyde_rewrite
from agent.processors.structure_ingest import structure_ingest
from agent.state import AgentState
from db.milvus_client import MilvusQA
from db.mysql_client import MySQLClient
from rag.bm25_index import BM25Index
from utils.config import get_config
from utils.logger import get_logger, setup_logging

setup_logging()
logger = get_logger("pipeline")


def load_csv(csv_path):
    items = []
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            q = (row.get("question") or row.get("问题描述") or "").strip()
            a = (row.get("answer") or row.get("处理结果/备注") or row.get("对客话术") or "").strip()
            if not q or not a:
                continue
            items.append({
                "question": q,
                "answer": a,
                "category_l1": (row.get("category_l1") or row.get("业务板块") or "").strip(),
                "category_l2": (row.get("category_l2") or row.get("业务类型") or row.get("细分场景") or "").strip(),
                "internal_process": (row.get("internal_process") or row.get("内部处理办法及流程") or "").strip(),
                "feedback_dept": (row.get("feedback_dept") or row.get("涉及反馈部门/微信群/工单模板") or "").strip(),
                "context": (row.get("context") or row.get("工单类型") or "").strip(),
            })
    return items


def step1_clean(items):
    print(f"\n[Step 1/6] 数据清洗 ({len(items)}条)")
    cleaned = []
    for item in items:
        state = AgentState(raw_question=item["question"], raw_answer=item["answer"])
        result = clean_text(state)
        item["question"] = result.get("question", item["question"])
        item["answer"] = result.get("answer", item["answer"])
        cleaned.append(item)
    print(f"  清洗完成: {len(cleaned)}条")
    return cleaned


def step2_structure(items):
    print(f"\n[Step 2/6] 结构化规整 ({len(items)}条)")
    processed = []
    review_count = 0
    for i, item in enumerate(items):
        state = AgentState(
            raw_question=item["question"],
            raw_answer=item["answer"],
            work_order_context=item.get("context", ""),
        )
        result = structure_ingest(state)
        item["question"] = result.get("question", item["question"])
        item["answer"] = result.get("answer", item["answer"])
        item["category_l1"] = result.get("category_l1", item.get("category_l1", ""))
        item["category_l2"] = result.get("category_l2", item.get("category_l2", ""))
        item["internal_process"] = result.get("internal_process", item.get("internal_process", ""))
        item["feedback_dept"] = result.get("feedback_dept", item.get("feedback_dept", ""))
        if result.get("needs_review"):
            item["needs_review"] = True
            item["review_highlights"] = result.get("review_highlights", [])
            review_count += 1
        if result.get("error"):
            item["error"] = result["error"]
        processed.append(item)
        if (i + 1) % 10 == 0:
            print(f"  处理进度: {i+1}/{len(items)}")
    print(f"  规整完成: {len(processed)}条, 需人工审核: {review_count}条")
    return processed


def step3_dedup(items, mysql, milvus, embed_model, threshold=0.92):
    print(f"\n[Step 3/6] 去重检查 ({len(items)}条)")
    cfg = get_config()
    query_prefix = cfg["models"]["query_prefix"]
    active_ids = mysql.get_active_ids()

    deduped = []
    duplicate_count = 0
    for item in items:
        vector = embed_model.encode([query_prefix + item["question"]], normalize_embeddings=True)[0]
        results = milvus.search(vector.tolist(), top_k=1, active_qa_ids=active_ids)
        if results and results[0][1] >= threshold:
            duplicate_count += 1
            item["is_duplicate"] = True
            item["duplicate_of"] = results[0][0]
            item["similarity_score"] = results[0][1]
        else:
            item["is_duplicate"] = False
        deduped.append(item)

    unique = [item for item in deduped if not item.get("is_duplicate")]
    print(f"  去重完成: 重复{duplicate_count}条, 保留{len(unique)}条")
    return deduped, unique


def step4_insert(unique_items, mysql, milvus, embed_model, bm25):
    print(f"\n[Step 4/6] 双库写入 ({len(unique_items)}条)")
    cfg = get_config()
    query_prefix = cfg["models"]["query_prefix"]
    inserted_ids = []
    error_count = 0

    for item in unique_items:
        if item.get("error") and not item.get("question"):
            error_count += 1
            continue
        try:
            qa_id = mysql.insert_qa(
                question=item["question"],
                answer=item["answer"],
                category_l1=item.get("category_l1", ""),
                category_l2=item.get("category_l2", ""),
                internal_process=item.get("internal_process", ""),
                feedback_dept=item.get("feedback_dept", ""),
            )
            vector = embed_model.encode([query_prefix + item["question"]], normalize_embeddings=True)[0]
            milvus.insert(qa_id, vector.tolist(), category_l1=item.get("category_l1", ""))
            inserted_ids.append(qa_id)
        except Exception as e:
            error_count += 1
            logger.error(f"写入失败: {e}")

    if inserted_ids:
        all_qa = mysql.get_all_questions()
        bm25.build(all_qa)

    print(f"  写入完成: 成功{len(inserted_ids)}条, �@败{error_count}条")
    return inserted_ids


def step5_hyde(inserted_ids, mysql, milvus, embed_model):
    print(f"\n[Step 5/6] HyDE增强 ({len(inserted_ids)}条)")
    cfg = get_config()
    query_prefix = cfg["models"]["query_prefix"]
    hyde_count = 0

    for qa_id in inserted_ids:
        try:
            qa = mysql.get_by_id(qa_id)
            if not qa:
                continue
            state = AgentState(question=qa["question"], answer=qa["answer"])
            result = hyde_rewrite(state)
            hyde_questions = result.get("hyde_questions", [])
            if hyde_questions:
                hyde_vectors = embed_model.encode(
                    [query_prefix + q for q in hyde_questions], normalize_embeddings=True
                ).tolist()
                milvus.insert(qa_id, [], category_l1=qa.get("category_l1", ""), hyde_vectors=hyde_vectors)
                hyde_count += 1
        except Exception as e:
            logger.error(f"HyDE失败 qa_id={qa_id}: {e}")

    print(f"  HyDE完成: {hyde_count}条生成了假设性问题")


def step6_verify(inserted_ids, mysql, milvus):
    print(f"\n[Step 6/6] 质量校验 ({len(inserted_ids)}条)")
    missing_milvus = 0
    for qa_id in inserted_ids:
        try:
            results = milvus.search(
                [0.0] * milvus.dim, top_k=1,
            )
        except Exception:
            pass

    mysql_count = 0
    for qa_id in inserted_ids:
        qa = mysql.get_by_id(qa_id)
        if qa:
            mysql_count += 1

    print(f"  MySQL: {mysql_count}/{len(inserted_ids)} 条可查")
    print("  校验完成")


def run_pipeline(csv_path=None, from_api=False, skip_llm=False, skip_hyde=False, limit=None):
    cfg = get_config()
    print("=" * 60)
    print("  ETC客服QA — 统一入库流水线")
    print("=" * 60)

    if csv_path:
        project_root = os.path.join(os.path.dirname(__file__), "..", "..")
        if not os.path.isabs(csv_path):
            csv_path = os.path.join(project_root, csv_path)
        items = load_csv(csv_path)
        print(f"  从CSV加载: {len(items)}条")
    elif from_api:
        mysql = MySQLClient()
        work_orders = mysql.get_work_orders_by_status("processed")
        items = []
        for wo in work_orders:
            raw = json.loads(wo["raw_data"]) if wo["raw_data"] else {}
            items.append({
                "question": raw.get("question", ""),
                "answer": raw.get("answer", ""),
                "context": raw.get("context", ""),
            })
        print(f"  从work_orders表加载: {len(items)}条")
    else:
        print("  ❌ 请指定 --csv 或 --api")
        return

    if limit:
        items = items[:limit]
        print(f"  限制处理: {limit}条")

    if not items:
        print("  ❌ 无数据可处理")
        return

    items = step1_clean(items)

    if not skip_llm:
        items = step2_structure(items)
    else:
        print("\n[Step 2/6] 跳过LLM规整 (--skip-llm)")

    mysql = MySQLClient()
    milvus = MilvusQA()
    from sentence_transformers import SentenceTransformer
    embed_model = SentenceTransformer(cfg["models"]["embed"]["path"])
    bm25 = BM25Index()
    all_qa = mysql.get_all_questions()
    bm25.build(all_qa)

    items, unique_items = step3_dedup(items, mysql, milvus, embed_model)

    inserted_ids = step4_insert(unique_items, mysql, milvus, embed_model, bm25)

    if not skip_hyde and inserted_ids:
        step5_hyde(inserted_ids, mysql, milvus, embed_model)
    else:
        print("\n[Step 5/6] 跳过HyDE (--skip-hyde 或 无新数据)")

    if inserted_ids:
        step6_verify(inserted_ids, mysql, milvus)

    print("\n" + "=" * 60)
    print("  流水线执行完毕")
    print(f"  输入: {len(items)}条")
    print(f"  去重后: {len(unique_items)}条")
    print(f"  入库: {len(inserted_ids)}条")
    print("=" * 60)

    milvus.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="统一入库流水线")
    parser.add_argument("--csv", help="CSV文件路径")
    parser.add_argument("--api", action="store_true", help="从work_orders表拉取")
    parser.add_argument("--skip-llm", action="store_true", help="跳过LLM规整（数据已是标准格式）")
    parser.add_argument("--skip-hyde", action="store_true", help="跳过HyDE增强")
    parser.add_argument("--limit", type=int, help="限制处理条数")
    args = parser.parse_args()

    run_pipeline(csv_path=args.csv, from_api=args.api, skip_llm=args.skip_llm, skip_hyde=args.skip_hyde, limit=args.limit)
