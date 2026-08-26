"""
Demo 2: RAG智能检索演示
展示: 标准化问题 → 向量召回 + BM25召回 → RRF合并 → Reranker精排 → 阈值判定

运行: python demo/demo2_rag_retrieval.py
"""

import os
import sys
import time

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("ETC_QA_ENV", "dev")

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, PROJECT_ROOT)

from sentence_transformers import CrossEncoder, SentenceTransformer

from db.milvus_client import MilvusQA
from db.mysql_client import MySQLClient
from rag.bm25_index import BM25Index
from rag.recall import RecallEngine
from rag.reranker import Reranker
from rag.threshold import ThresholdJudge
from utils.config import load_config

SEP = "=" * 60


def main():
    print(SEP)
    print("  Demo 2: RAG智能检索")
    print(SEP)

    print("\n加载配置和模型...")
    cfg = load_config()

    import torch
    torch.set_num_threads(1)

    print("  加载Embedding模型...")
    embed_model = SentenceTransformer(cfg["models"]["embed"]["path"])
    print("  加载Reranker模型...")
    rerank_model = CrossEncoder(cfg["models"]["rerank"]["path"])
    print("  初始化数据库...")
    mysql = MySQLClient()
    milvus = MilvusQA()
    print("  构建BM25索引...")
    bm25 = BM25Index()
    all_qa = mysql.get_all_questions()
    bm25.build(all_qa)

    recall = RecallEngine(embed_model, milvus, bm25)
    reranker = Reranker(rerank_model, mysql_client=mysql)
    threshold = ThresholdJudge()

    active_ids = mysql.get_active_ids()
    print(f"  知识库活跃条目: {len(active_ids)}")

    test_questions = [
        "ETC扣费异常如何处理",
        "ETC设备不亮怎么办",
        "如何注销ETC",
    ]

    for i, question in enumerate(test_questions, 1):
        print(f"\n{'#' * 60}")
        print(f"  查询 {i}/{len(test_questions)}: \"{question}\"")
        print(f"{'#' * 60}")

        query_vector = recall.encode_query(question)

        print(f"\n{SEP}")
        print("步骤1: 双路并行召回")
        print(SEP)

        t0 = time.time()
        vec_results = recall.vector_recall(query_vector, active_qa_ids=active_ids)
        vec_time = time.time() - t0
        print(f"  向量召回: {len(vec_results)} 条, 耗时 {vec_time:.2f}s")
        for qa_id, score in vec_results[:3]:
            r = mysql.get_by_id(qa_id)
            q_text = r["question"] if r else "?"
            print(f"    - [{qa_id}] {score:.4f} \"{q_text}\"")

        t0 = time.time()
        bm25_results = recall.bm25_recall(question, active_qa_ids=active_ids)
        bm25_time = time.time() - t0
        print(f"  BM25召回: {len(bm25_results)} 条, 耗时 {bm25_time:.2f}s")
        for qa_id, score in bm25_results[:3]:
            r = mysql.get_by_id(qa_id)
            q_text = r["question"] if r else "?"
            print(f"    - [{qa_id}] {score:.4f} \"{q_text}\"")

        print(f"\n{SEP}")
        print("步骤2: RRF融合")
        print(SEP)
        merged = recall.recall(question, query_vector, active_qa_ids=active_ids)
        print(f"  合并后候选: {len(merged)} 条")

        print(f"\n{SEP}")
        print("步骤3: Reranker精排")
        print(SEP)
        t0 = time.time()
        reranked = reranker.rerank(question, merged)
        rerank_time = time.time() - t0
        print(f"  精排耗时: {rerank_time:.2f}s")
        for qa_id, score in reranked[:5]:
            r = mysql.get_by_id(qa_id)
            q_text = r["question"] if r else "?"
            print(f"    - [{qa_id}] {score:.4f} \"{q_text}\"")

        print(f"\n{SEP}")
        print("步骤4: 阈值判定")
        print(SEP)
        confidence, filtered = threshold.filter_candidates(reranked)
        print(f"  置信度: {confidence}")
        print(f"  返回候选: {len(filtered)} 条")

        if len(reranked) >= 2:
            gap = reranked[0][1] - reranked[1][1]
            print(f"  Top1-Top2差值: {gap:.4f}")
        print(f"  Top1分数: {reranked[0][1]:.4f}")

        print(f"\n  📌 最终结果: 置信度={confidence}, 返回{len(filtered)}条候选")

        if i < len(test_questions):
            input(f"\n>>> 按回车继续下一个查询 ({i}/{len(test_questions)}) ...")

    print(f"\n{SEP}")
    print("  Demo 2 完成")
    print(SEP)


if __name__ == "__main__":
    main()