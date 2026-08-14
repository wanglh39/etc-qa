import os
import sys
import time
import statistics

os.environ['ETC_QA_ENV'] = os.environ.get('ETC_QA_ENV', 'test')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import argparse
from collections import defaultdict

from db.mysql_client import MySQLClient
from db.milvus_client import MilvusQA
from rag.bm25_index import BM25Index
from rag.recall import RecallEngine
from rag.reranker import Reranker
from rag.service import QAService
from rag.threshold import ThresholdJudge
from utils.config import load_config
from utils.logger import get_logger

logger = get_logger("scripts.eval.eval_rag_perf")

TEST_QUERIES = [
    "ETC鎵ｈ垂寮傚父鎬庝箞澶勭悊",
    "榛戝悕鍗曞浣曡В闄?,
    "鍙戠エ鎬庝箞鐢宠",
    "ETC璁惧涓嶄寒浜嗕絾鏄摑鐗欒兘杩炰笂",
    "鎴戜笂涓湀鍦ㄥ悓涓€涓珮閫熷彛琚墸浜嗕袱娆¤垂鎬庝箞鍔?,
    "ETC鎬庝箞娉ㄩ攢",
    "ETC缁戝畾鐨勯摱琛屽崱鑳戒笉鑳芥崲",
    "ETC閲嶅鎵ｈ垂鎬庝箞閫€娆?,
    "ETC婵€娲绘祦绋嬫槸浠€涔?,
    "ETC璐﹀崟鎬庝箞鏌ヨ",
]


def _percentile(data, p):
    if not data:
        return 0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * p / 100
    f = int(k)
    c = f + 1 if f + 1 < len(sorted_data) else f
    return sorted_data[f] + (sorted_data[c] - sorted_data[f]) * (k - f)


def init_rag_service():
    cfg = load_config()
    print("鍒濆鍖朢AG鏈嶅姟...")
    t0 = time.perf_counter()

    mysql = MySQLClient()
    milvus = MilvusQA()
    all_qa = mysql.get_all_questions()
    print(f"  MySQL: {len(all_qa)}鏉A璁板綍")

    bm25 = BM25Index()
    bm25.build(all_qa)
    print(f"  BM25绱㈠紩鏋勫缓瀹屾垚")

    embed_path = cfg["models"]["embed"]["path"]
    from sentence_transformers import CrossEncoder, SentenceTransformer
    embed_model = SentenceTransformer(embed_path)
    print(f"  Embedding妯″瀷鍔犺浇: {embed_path}")

    rerank_path = cfg["models"]["rerank"]["path"]
    rerank_model = CrossEncoder(rerank_path)
    print(f"  Reranker妯″瀷鍔犺浇: {rerank_path}")

    recall_eng = RecallEngine(embed_model, milvus, bm25)
    reranker = Reranker(rerank_model, mysql_client=mysql)
    threshold = ThresholdJudge()
    qa_service = QAService(recall_eng, threshold, reranker, mysql)

    t1 = time.perf_counter()
    print(f"RAG鏈嶅姟鍒濆鍖栧畬鎴? {t1-t0:.2f}s\n")
    return qa_service, recall_eng, reranker, threshold, mysql


def run_perf_benchmark(qa_service, recall_eng, reranker, threshold, mysql,
                       queries, iterations, warmup):
    timings = defaultdict(list)

    if warmup > 0:
        print(f"棰勭儹 {warmup} 娆?..")
        for i in range(warmup):
            q = queries[i % len(queries)]
            try:
                qa_service.query(q)
            except Exception as e:
                print(f"  棰勭儹寮傚父(蹇界暐): {e}")
        print("棰勭儹瀹屾垚\n")

    print(f"寮€濮嬫祴閫? {len(queries)}涓棶棰?脳 {iterations}杞?= {len(queries)*iterations}娆℃煡璇n")

    for round_num in range(iterations):
        for q in queries:
            _run_single_query(qa_service, recall_eng, reranker, threshold, mysql, q, timings)

    _print_report(timings, len(queries) * iterations)


def _run_single_query(qa_service, recall_eng, reranker, threshold, mysql, question, timings):
    t_total_start = time.perf_counter()

    t0 = time.perf_counter()
    try:
        standardized = qa_service._standardize(question)
    except Exception as e:
        standardized = question
        timings["standardize_errors"].append(1)
    t1 = time.perf_counter()
    timings["1_standardize_llm"].append((t1 - t0) * 1000)

    t0 = time.perf_counter()
    active_qa_ids = qa_service._get_active_ids()
    t1 = time.perf_counter()
    timings["2_get_active_ids"].append((t1 - t0) * 1000)

    t0 = time.perf_counter()
    query_vector = recall_eng.encode_query(standardized)
    t1 = time.perf_counter()
    timings["3_encode_query"].append((t1 - t0) * 1000)

    t0 = time.perf_counter()
    candidates = recall_eng.recall(standardized, query_vector, active_qa_ids=active_qa_ids)
    t1 = time.perf_counter()
    timings["4_recall_total"].append((t1 - t0) * 1000)

    t0 = time.perf_counter()
    candidates_reranked = reranker.rerank(standardized, candidates)
    t1 = time.perf_counter()
    timings["5_rerank"].append((t1 - t0) * 1000)

    t0 = time.perf_counter()
    confidence, filtered = threshold.filter_candidates(candidates_reranked)
    t1 = time.perf_counter()
    timings["6_threshold"].append((t1 - t0) * 1000)

    t0 = time.perf_counter()
    qa_ids = [qa_id for qa_id, score in filtered]
    qa_records = mysql.get_by_ids(qa_ids)
    t1 = time.perf_counter()
    timings["7_mysql_get_by_ids"].append((t1 - t0) * 1000)

    t_total_end = time.perf_counter()
    timings["0_total"].append((t_total_end - t_total_start) * 1000)


def _print_report(timings, total_queries):
    steps = [
        "0_total",
        "1_standardize_llm",
        "2_get_active_ids",
        "3_encode_query",
        "4_recall_total",
        "5_rerank",
        "6_threshold",
        "7_mysql_get_by_ids",
    ]

    step_names = {
        "0_total": "鎬昏€楁椂",
        "1_standardize_llm": "鈶燣LM鏍囧噯鍖?,
        "2_get_active_ids": "鈶℃椿璺僆D缂撳瓨",
        "3_encode_query": "鈶mbedding缂栫爜",
        "4_recall_total": "鈶ｅ弻璺彫鍥?RRF",
        "5_rerank": "鈶rossEncoder閲嶆帓",
        "6_threshold": "鈶ラ槇鍊艰繃婊?,
        "7_mysql_get_by_ids": "鈶ySQL鍙栬褰?,
    }

    print("=" * 90)
    print(f"RAG妫€绱㈡€ц兘鎶ュ憡 ({total_queries}娆℃煡璇?")
    print("=" * 90)
    print(f"{'姝ラ':<22} {'mean':>8} {'p50':>8} {'p95':>8} {'p99':>8} {'min':>8} {'max':>8}  鍗曚綅:ms")
    print("-" * 90)

    total_mean = 0
    for step in steps:
        data = timings.get(step, [])
        if not data:
            continue
        mean = statistics.mean(data)
        p50 = _percentile(data, 50)
        p95 = _percentile(data, 95)
        p99 = _percentile(data, 99)
        mn = min(data)
        mx = max(data)

        if step != "0_total":
            total_mean += mean

        name = step_names.get(step, step)
        print(f"{name:<22} {mean:>8.1f} {p50:>8.1f} {p95:>8.1f} {p99:>8.1f} {mn:>8.1f} {mx:>8.1f}")

    print("-" * 90)
    print(f"{'鍚勬涔嬪拰':<22} {total_mean:>8.1f}")
    print()

    step_times = []
    for step in steps[1:]:
        data = timings.get(step, [])
        if data:
            step_times.append((step_names.get(step, step), statistics.mean(data)))

    step_times.sort(key=lambda x: x[1], reverse=True)
    print("鐡堕鎺掑簭锛堜粠鎱㈠埌蹇級:")
    for i, (name, ms) in enumerate(step_times):
        pct = ms / total_mean * 100 if total_mean > 0 else 0
        bar = "鈻? * int(pct / 2)
        print(f"  {i+1}. {name:<20} {ms:>7.1f}ms ({pct:>5.1f}%) {bar}")

    print()
    errors = timings.get("standardize_errors", [])
    if errors:
        print(f"鈿?LLM鏍囧噯鍖栧け璐?{len(errors)} 娆?)


def main():
    parser = argparse.ArgumentParser(description="RAG妫€绱㈡€ц兘鍩哄噯娴嬭瘯")
    parser.add_argument("--iterations", type=int, default=3, help="姣忚疆鏌ヨ鐨勯噸澶嶈疆鏁帮紙榛樿3锛?)
    parser.add_argument("--warmup", type=int, default=2, help="棰勭儹鏌ヨ娆℃暟锛堥粯璁?锛?)
    parser.add_argument("--queries", nargs="*", default=None, help="鑷畾涔夋煡璇㈤棶棰樺垪琛?)
    args = parser.parse_args()

    queries = args.queries if args.queries else TEST_QUERIES

    qa_service, recall_eng, reranker, threshold, mysql = init_rag_service()
    run_perf_benchmark(qa_service, recall_eng, reranker, threshold, mysql,
                       queries, args.iterations, args.warmup)


if __name__ == "__main__":
    main()