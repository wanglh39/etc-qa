import os

os.environ["ETC_QA_ENV"] = os.environ.get("ETC_QA_ENV", "test")
import sys

sys.path.insert(0, ".")
import argparse

from agent.processors.hyde_rewrite import hyde_rewrite
from agent.state import AgentState
from db.milvus_client import MilvusQA
from db.mysql_client import MySQLClient
from rag.siliconflow import get_embedding_client
from utils.config import load_config

cfg = load_config()


def batch_import(dry_run=False):
    mysql = MySQLClient()
    milvus = MilvusQA()
    embed_model = get_embedding_client()
    query_prefix = cfg["models"]["query_prefix"]

    deduped_orders = mysql.get_work_orders_by_status("deduped")
    if not deduped_orders:
        print("No deduped work orders to import.")
        return

    print(f"Found {len(deduped_orders)} deduped work orders to import.")

    imported = 0
    errors = []

    for wo in deduped_orders:
        try:
            raw_data = wo.get("raw_data", "")
            if not raw_data:
                errors.append((wo["id"], "empty raw_data"))
                continue

            import json

            try:
                data = json.loads(raw_data)
            except json.JSONDecodeError:
                data = {"question": raw_data, "answer": ""}

            question = data.get("question", "")
            answer = data.get("answer", "")
            category_l1 = data.get("category_l1", "")
            category_l2 = data.get("category_l2", "")
            internal_process = data.get("internal_process", "")
            feedback_dept = data.get("feedback_dept", "")

            if not question:
                errors.append((wo["id"], "empty question"))
                continue

            if dry_run:
                print(f"  [DRY RUN] Would import: {question[:50]}")
                imported += 1
                continue

            qa_id = mysql.insert_qa(
                question=question,
                answer=answer,
                category_l1=category_l1,
                category_l2=category_l2,
                internal_process=internal_process,
                feedback_dept=feedback_dept,
            )

            question_text = query_prefix + question
            vector = embed_model.encode([question_text], normalize_embeddings=True).tolist()[0]
            milvus.insert(qa_id, vector, category_l1)

            hyde_qs = []
            if answer:
                state = AgentState(raw_question=question, question=question, answer=answer)
                hyde_result = hyde_rewrite(state)
                hyde_qs = hyde_result.get("hyde_questions", [])

            if hyde_qs:
                hyde_vectors = []
                for hq in hyde_qs:
                    hq_text = query_prefix + hq
                    hv = embed_model.encode([hq_text], normalize_embeddings=True).tolist()[0]
                    hyde_vectors.append(hv)
                milvus.insert(qa_id, vector, category_l1, hyde_vectors=hyde_vectors)

            mysql.update_work_order(wo["external_id"], raw_data, "imported")
            imported += 1
            print(f"  [{imported}/{len(deduped_orders)}] Imported qa_id={qa_id}: {question[:50]}")

        except Exception as e:
            errors.append((wo["id"], str(e)))
            print(f"  ERROR on work_order {wo['id']}: {e}")

    milvus.close()

    print(f"\nImport complete: {imported} imported, {len(errors)} errors")
    if errors:
        print("Errors:")
        for wo_id, err in errors:
            print(f"  work_order {wo_id}: {err}")

    verify_consistency(mysql, milvus)


def verify_consistency(mysql=None, milvus=None):
    if mysql is None:
        mysql = MySQLClient()
    if milvus is None:
        milvus = MilvusQA()

    print("\n=== Consistency Check ===")

    all_qa = mysql.get_all_questions()
    mysql_ids = set(qa["id"] for qa in all_qa)
    print(f"MySQL qa_pairs count: {len(mysql_ids)}")

    milvus.init_collection()
    milvus.client.load_collection(milvus.collection_name)
    results = milvus.client.query(
        collection_name=milvus.collection_name,
        filter="",
        output_fields=["qa_id", "is_hyde"],
    )

    milvus_qa_ids = set(r["qa_id"] for r in results)
    original_count = sum(1 for r in results if not r["is_hyde"])
    hyde_count = sum(1 for r in results if r["is_hyde"])
    print(f"Milvus total vectors: {len(results)} ({original_count} original + {hyde_count} HyDE)")
    print(f"Milvus unique qa_ids: {len(milvus_qa_ids)}")

    only_mysql = mysql_ids - milvus_qa_ids
    only_milvus = milvus_qa_ids - mysql_ids

    if only_mysql:
        print(f"WARNING: {len(only_mysql)} qa_ids in MySQL but not in Milvus: {sorted(only_mysql)[:10]}")
    if only_milvus:
        print(f"WARNING: {len(only_milvus)} qa_ids in Milvus but not in MySQL: {sorted(only_milvus)[:10]}")

    missing_original = mysql_ids - set(r["qa_id"] for r in results if not r["is_hyde"])
    if missing_original:
        print(f"WARNING: {len(missing_original)} qa_ids missing original vector in Milvus")

    if not only_mysql and not only_milvus and not missing_original:
        print("PASS: MySQL and Milvus are consistent.")

    milvus.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--verify-only", action="store_true", help="Only run consistency check")
    args = parser.parse_args()

    if args.verify_only:
        verify_consistency()
    else:
        batch_import(dry_run=args.dry_run)
