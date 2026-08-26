import os

os.environ['ETC_QA_ENV'] = os.environ.get('ETC_QA_ENV', 'test')
from dotenv import load_dotenv

load_dotenv()
import sys

sys.path.insert(0, '.')
import csv

from db.milvus_client import MilvusQA
from db.mysql_client import MySQLClient
from rag.bm25_index import BM25Index
from rag.recall import RecallEngine
from rag.reranker import Reranker
from rag.siliconflow import get_embedding_client, get_rerank_client
from utils.config import load_config

try:
    import langsmith
    from langsmith.evaluation import evaluate
    HAS_LANGSMITH = True
except ImportError:
    HAS_LANGSMITH = False
    print("langsmith not installed. Run: pip install langsmith")

cfg = load_config()

embed_model = get_embedding_client()
rerank_model = get_rerank_client()
mysql = MySQLClient()
milvus = MilvusQA()
all_qa = mysql.get_all_questions()
bm25 = BM25Index()
bm25.build(all_qa)
qa_pairs_dict = {qa["id"]: qa for qa in all_qa}
recall_eng = RecallEngine(embed_model, milvus, bm25)
reranker = Reranker(rerank_model, mysql_client=mysql)

question_to_ids = {}
for qa in all_qa:
    q = qa["question"]
    if q not in question_to_ids:
        question_to_ids[q] = qa["id"]

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
test_csv_path = os.path.join(PROJECT_ROOT, cfg.get("data", {}).get("test_csv", "data/eval/test_rag.csv"))
test_data = []
with open(test_csv_path, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        test_data.append(row)

MAX_TEST = int(sys.argv[1]) if len(sys.argv) > 1 else 100
test_data = test_data[:MAX_TEST]

examples = []
for row in test_data:
    expected_q = row["standard_question"]
    expected_id = None
    for q, qid in question_to_ids.items():
        if expected_q in q or q in expected_q:
            expected_id = qid
            break
    if expected_id is not None:
        examples.append({
            "inputs": {"question": row["user_query"]},
            "outputs": {"expected_id": expected_id, "expected_question": expected_q},
        })


def target_func(inputs: dict) -> dict:
    query = inputs["question"]
    query_vector = recall_eng.encode_query(query)
    candidates = recall_eng.recall(query, query_vector, use_hyde=True)
    candidates = reranker.rerank(query, candidates)
    top_ids = [qa_id for qa_id, score in candidates[:10]]
    top_scores = [score for _, score in candidates[:10]]
    top_questions = [qa_pairs_dict.get(qid, {}).get("question", "") for qid in top_ids]
    return {
        "top_ids": top_ids,
        "top_scores": top_scores,
        "top_questions": top_questions,
    }


def recall_at_1(run, example):
    expected_id = example.outputs["expected_id"]
    top_ids = run.outputs["top_ids"]
    return {"score": 1 if top_ids and top_ids[0] == expected_id else 0}


def recall_at_3(run, example):
    expected_id = example.outputs["expected_id"]
    top_ids = run.outputs["top_ids"]
    return {"score": 1 if expected_id in top_ids[:3] else 0}


def mrr(run, example):
    expected_id = example.outputs["expected_id"]
    top_ids = run.outputs["top_ids"]
    for rank, qid in enumerate(top_ids, 1):
        if qid == expected_id:
            return {"score": 1.0 / rank}
    return {"score": 0.0}


if not HAS_LANGSMITH:
    print("Running without LangSmith (local mode)...")
    total = len(examples)
    h1 = h3 = 0
    mrr_sum = 0.0
    for i, ex in enumerate(examples):
        result = target_func(ex["inputs"])
        expected_id = ex["outputs"]["expected_id"]
        top_ids = result["top_ids"]
        if top_ids and top_ids[0] == expected_id:
            h1 += 1
        if expected_id in top_ids[:3]:
            h3 += 1
        for rank, qid in enumerate(top_ids, 1):
            if qid == expected_id:
                mrr_sum += 1.0 / rank
                break
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{total}")
    print(f"\nR@1={h1/total:.4f} R@3={h3/total:.4f} MRR={mrr_sum/total:.4f}")
else:
    dataset_name = "etc-qa-rag-eval"
    try:
        client = langsmith.Client()
        ds = client.create_dataset(dataset_name=dataset_name)
        for ex in examples:
            client.create_example(
                inputs=ex["inputs"],
                outputs=ex["outputs"],
                dataset_id=ds.id,
            )
    except Exception as e:
        print(f"Dataset creation note: {e}")

    results = evaluate(
        target_func,
        data=examples,
        evaluators=[recall_at_1, recall_at_3, mrr],
        experiment_prefix="etc-qa-rag",
    )
    print(f"\nResults: {results}")

milvus.close()
