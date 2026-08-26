import os

os.environ["ETC_QA_ENV"] = os.environ.get("ETC_QA_ENV", "test")
import sys

sys.path.insert(0, ".")
import csv

from agent.processors.standardize_query import standardize_query
from agent.state import AgentState
from db.milvus_client import MilvusQA
from db.mysql_client import MySQLClient
from rag.bm25_index import BM25Index
from rag.recall import RecallEngine
from rag.reranker import Reranker
from rag.siliconflow import get_embedding_client, get_rerank_client
from utils.config import load_config

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


def find_expected_id(expected_question):
    for q, qid in question_to_ids.items():
        q_clean = q.replace("\n", "").replace(" ", "")
        e_clean = expected_question.replace("\n", "").replace(" ", "")
        if e_clean in q_clean or q_clean in e_clean:
            return qid
    return None


def do_search(query, use_hyde=True):
    query_vector = recall_eng.encode_query(query)
    candidates = recall_eng.recall(query, query_vector, use_hyde=use_hyde)
    candidates = reranker.rerank(query, candidates)
    return candidates


configs = [
    ("baseline", False, False),
    ("+standardize", True, False),
    ("+HyDE", False, True),
    ("+std+HyDE", True, True),
]

hits = {name: {"h1": 0, "h3": 0, "h5": 0, "h10": 0, "mrr": 0.0} for name, _, _ in configs}
total = 0
missed = 0
per_query_results = []

for i, item in enumerate(test_data):
    raw = item["user_query"]
    expected_question = item["standard_question"]
    expected_id = find_expected_id(expected_question)

    if expected_id is None:
        missed += 1
        continue

    total += 1

    try:
        state = AgentState(raw_question=raw)
        std_result = standardize_query(state)
        std = std_result.get("question", raw) or raw
    except Exception:
        std = raw

    config_results = {}
    for name, use_std, use_hyde in configs:
        q = std if use_std else raw
        candidates = do_search(q, use_hyde=use_hyde)
        top_ids = [qa_id for qa_id, score in candidates[:10]]
        top_scores = [score for _, score in candidates[:10]]

        h1 = 1 if expected_id in top_ids[:1] else 0
        h3 = 1 if expected_id in top_ids[:3] else 0
        h5 = 1 if expected_id in top_ids[:5] else 0
        h10 = 1 if expected_id in top_ids[:10] else 0
        mrr = 0.0
        for rank, qid in enumerate(top_ids, 1):
            if qid == expected_id:
                mrr = 1.0 / rank
                break

        hits[name]["h1"] += h1
        hits[name]["h3"] += h3
        hits[name]["h5"] += h5
        hits[name]["h10"] += h10
        hits[name]["mrr"] += mrr

        config_results[name] = {
            "h1": h1,
            "h3": h3,
            "mrr": mrr,
            "top1_id": top_ids[0] if top_ids else None,
            "top1_q": qa_pairs_dict.get(top_ids[0], {}).get("question", "") if top_ids else "",
            "top1_score": top_scores[0] if top_scores else 0,
        }

    per_query_results.append(
        {
            "raw": raw,
            "std": std,
            "expected_id": expected_id,
            "expected_q": expected_question,
            "configs": config_results,
        }
    )

    if (i + 1) % 50 == 0:
        print(f"  {i + 1}/{len(test_data)}", end=" ")
        for name, _, _ in configs:
            print(f"{name}:R@1={hits[name]['h1'] / total:.4f}", end=" ")
        print()

out_dir = os.path.join(os.path.dirname(__file__), "..", "..", "output")
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "eval_rag_report.txt")
with open(out_path, "w", encoding="utf-8") as f:
    f.write("RAG Evaluation Report\n")
    f.write(f"{'=' * 80}\n")
    f.write(f"Test: {len(test_data)}, Valid: {total}, Missed: {missed}\n")
    f.write(f"Reranker: enabled ({cfg['models']['rerank']['name']})\n\n")

    baseline_r1 = hits["baseline"]["h1"] / total if total > 0 else 0
    baseline_r3 = hits["baseline"]["h3"] / total if total > 0 else 0

    header = f"{'config':<16} {'R@1':<10} {'R@3':<10} {'R@5':<10} {'R@10':<10} {'MRR':<10} {'d_R@1':<10} {'d_R@3':<10}"
    f.write(header + "\n")
    f.write("-" * 80 + "\n")

    for name, _, _ in configs:
        r1 = hits[name]["h1"] / total if total > 0 else 0
        r3 = hits[name]["h3"] / total if total > 0 else 0
        r5 = hits[name]["h5"] / total if total > 0 else 0
        r10 = hits[name]["h10"] / total if total > 0 else 0
        mrr = hits[name]["mrr"] / total if total > 0 else 0
        d1 = r1 - baseline_r1
        d3 = r3 - baseline_r3
        f.write(f"{name:<16} {r1:<10.4f} {r3:<10.4f} {r5:<10.4f} {r10:<10.4f} {mrr:<10.4f} {d1:+<10.4f} {d3:+<10.4f}\n")

    miss_r1 = [r for r in per_query_results if not r["configs"]["baseline"]["h1"]]
    f.write(f"\n--- Baseline R@1 Failures: {len(miss_r1)} ---\n")
    for r in miss_r1[:30]:
        bl = r["configs"]["baseline"]
        f.write(f"  Query: {r['raw']}\n")
        f.write(f"  Expected: [{r['expected_id']}] {r['expected_q']}\n")
        f.write(f"  Got: [{bl['top1_id']}] {bl['top1_q']} (score={bl['top1_score']:.4f})\n")
        f.write(f"  In top3: {'Yes' if bl['h3'] else 'No'}\n\n")

    improved = [
        r
        for r in per_query_results
        if not r["configs"]["baseline"]["h3"] and any(r["configs"][n]["h3"] for n, _, _ in configs if n != "baseline")
    ]
    if improved:
        f.write(f"--- Cases baseline missed but enhanced hit (R@3): {len(improved)} ---\n")
        for r in improved[:20]:
            f.write(f"  Query: {r['raw'][:50]}\n")
            for name, _, _ in configs:
                cr = r["configs"][name]
                f.write(f"    {name}: h3={cr['h3']} top1={cr['top1_id']} score={cr['top1_score']:.4f}\n")
            f.write("\n")

milvus.close()
print(f"\nDone. Output: {out_path}")
