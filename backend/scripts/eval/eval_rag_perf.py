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
    "ETC扣费异常怎么处理",
    "黑名单如何解除",
    "发票怎么申请",
    "ETC设备不亮了但是蓝牙能连上",
    "我上个月在同一个高速口被扣了两次费怎么办",
    "ETC怎么注销",
    "ETC绑定的银行卡能不能换",
    "ETC重复扣费怎么退款",
    "ETC激活流程是什么",
    "ETC账单怎么查询",
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
    print("初始化RAG服务...")
    t0 = time.perf_counter()

    mysql = MySQLClient()
    milvus = MilvusQA()
    all_qa = mysql.get_all_questions()
    print(f"  MySQL: {len(all_qa)}条QA记录")

    bm25 = BM25Index()
    bm25.build(all_qa)
    print(f"  BM25索引构建完成")

    embed_path = cfg["models"]["embed"]["path"]
    from sentence_transformers import CrossEncoder, SentenceTransformer
    embed_model = SentenceTransformer(embed_path)
    print(f"  Embedding模型加载: {embed_path}")

    rerank_path = cfg["models"]["rerank"]["path"]
    rerank_model = CrossEncoder(rerank_path)
    print(f"  Reranker模型加载: {rerank_path}")

    recall_eng = RecallEngine(embed_model, milvus, bm25)
    reranker = Reranker(rerank_model, mysql_client=mysql)
    threshold = ThresholdJudge()
    qa_service = QAService(recall_eng, threshold, reranker, mysql)

    t1 = time.perf_counter()
    print(f"RAG服务初始化完成: {t1-t0:.2f}s\n")
    return qa_service, recall_eng, reranker, threshold, mysql


def run_perf_benchmark(qa_service, recall_eng, reranker, threshold, mysql,
                       queries, iterations, warmup):
    timings = defaultdict(list)

    if warmup > 0:
        print(f"预热 {warmup} 次...")
        for i in range(warmup):
            q = queries[i % len(queries)]
            try:
                qa_service.query(q)
            except Exception as e:
                print(f"  预热异常(忽略): {e}")
        print("预热完成\n")

    print(f"开始测速: {len(queries)}个问题 × {iterations}轮 = {len(queries)*iterations}次查询\n")

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
        "0_total": "总耗时",
        "1_standardize_llm": "①LLM标准化",
        "2_get_active_ids": "②活跃ID缓存",
        "3_encode_query": "③Embedding编码",
        "4_recall_total": "④双路召回+RRF",
        "5_rerank": "⑤CrossEncoder重排",
        "6_threshold": "⑥阈值过滤",
        "7_mysql_get_by_ids": "⑦MySQL取记录",
    }

    print("=" * 90)
    print(f"RAG检索性能报告 ({total_queries}次查询)")
    print("=" * 90)
    print(f"{'步骤':<22} {'mean':>8} {'p50':>8} {'p95':>8} {'p99':>8} {'min':>8} {'max':>8}  单位:ms")
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
    print(f"{'各步之和':<22} {total_mean:>8.1f}")
    print()

    step_times = []
    for step in steps[1:]:
        data = timings.get(step, [])
        if data:
            step_times.append((step_names.get(step, step), statistics.mean(data)))

    step_times.sort(key=lambda x: x[1], reverse=True)
    print("瓶颈排序（从慢到快）:")
    for i, (name, ms) in enumerate(step_times):
        pct = ms / total_mean * 100 if total_mean > 0 else 0
        bar = "█" * int(pct / 2)
        print(f"  {i+1}. {name:<20} {ms:>7.1f}ms ({pct:>5.1f}%) {bar}")

    print()
    errors = timings.get("standardize_errors", [])
    if errors:
        print(f"⚠ LLM标准化失败 {len(errors)} 次")


def main():
    parser = argparse.ArgumentParser(description="RAG检索性能基准测试")
    parser.add_argument("--iterations", type=int, default=3, help="每轮查询的重复轮数（默认3）")
    parser.add_argument("--warmup", type=int, default=2, help="预热查询次数（默认2）")
    parser.add_argument("--queries", nargs="*", default=None, help="自定义查询问题列表")
    args = parser.parse_args()

    queries = args.queries if args.queries else TEST_QUERIES

    qa_service, recall_eng, reranker, threshold, mysql = init_rag_service()
    run_perf_benchmark(qa_service, recall_eng, reranker, threshold, mysql,
                       queries, args.iterations, args.warmup)


if __name__ == "__main__":
    main()