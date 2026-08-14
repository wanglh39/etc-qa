"""
Demo 2: RAG鏅鸿兘妫€绱㈡紨绀?灞曠ず: 鏍囧噯鍖栭棶棰?鈫?鍚戦噺鍙洖 + BM25鍙洖 鈫?RRF鍚堝苟 鈫?Reranker绮炬帓 鈫?闃堝€煎垽瀹?
杩愯: python demo/demo2_rag_retrieval.py
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
    print("  Demo 2: RAG鏅鸿兘妫€绱?)
    print(SEP)

    print("\n鍔犺浇閰嶇疆鍜屾ā鍨?..")
    cfg = load_config()

    import torch
    torch.set_num_threads(1)

    print("  鍔犺浇Embedding妯″瀷...")
    embed_model = SentenceTransformer(cfg["models"]["embed"]["path"])
    print("  鍔犺浇Reranker妯″瀷...")
    rerank_model = CrossEncoder(cfg["models"]["rerank"]["path"])
    print("  鍒濆鍖栨暟鎹簱...")
    mysql = MySQLClient()
    milvus = MilvusQA()
    print("  鏋勫缓BM25绱㈠紩...")
    bm25 = BM25Index()
    all_qa = mysql.get_all_questions()
    bm25.build(all_qa)

    recall = RecallEngine(embed_model, milvus, bm25)
    reranker = Reranker(rerank_model, mysql_client=mysql)
    threshold = ThresholdJudge()

    active_ids = mysql.get_active_ids()
    print(f"  鐭ヨ瘑搴撴椿璺冩潯鐩? {len(active_ids)}")

    test_questions = [
        "ETC鎵ｈ垂寮傚父濡備綍澶勭悊",
        "ETC璁惧涓嶄寒鎬庝箞鍔?,
        "濡備綍娉ㄩ攢ETC",
    ]

    for i, question in enumerate(test_questions, 1):
        print(f"\n{'#' * 60}")
        print(f"  鏌ヨ {i}/{len(test_questions)}: \"{question}\"")
        print(f"{'#' * 60}")

        query_vector = recall.encode_query(question)

        print(f"\n{SEP}")
        print("姝ラ1: 鍙岃矾骞惰鍙洖")
        print(SEP)

        t0 = time.time()
        vec_results = recall.vector_recall(query_vector, active_qa_ids=active_ids)
        vec_time = time.time() - t0
        print(f"  鍚戦噺鍙洖: {len(vec_results)} 鏉? 鑰楁椂 {vec_time:.2f}s")
        for qa_id, score in vec_results[:3]:
            r = mysql.get_by_id(qa_id)
            q_text = r["question"] if r else "?"
            print(f"    - [{qa_id}] {score:.4f} \"{q_text}\"")

        t0 = time.time()
        bm25_results = recall.bm25_recall(question, active_qa_ids=active_ids)
        bm25_time = time.time() - t0
        print(f"  BM25鍙洖: {len(bm25_results)} 鏉? 鑰楁椂 {bm25_time:.2f}s")
        for qa_id, score in bm25_results[:3]:
            r = mysql.get_by_id(qa_id)
            q_text = r["question"] if r else "?"
            print(f"    - [{qa_id}] {score:.4f} \"{q_text}\"")

        print(f"\n{SEP}")
        print("姝ラ2: RRF铻嶅悎")
        print(SEP)
        merged = recall.recall(question, query_vector, active_qa_ids=active_ids)
        print(f"  鍚堝苟鍚庡€欓€? {len(merged)} 鏉?)

        print(f"\n{SEP}")
        print("姝ラ3: Reranker绮炬帓")
        print(SEP)
        t0 = time.time()
        reranked = reranker.rerank(question, merged)
        rerank_time = time.time() - t0
        print(f"  绮炬帓鑰楁椂: {rerank_time:.2f}s")
        for qa_id, score in reranked[:5]:
            r = mysql.get_by_id(qa_id)
            q_text = r["question"] if r else "?"
            print(f"    - [{qa_id}] {score:.4f} \"{q_text}\"")

        print(f"\n{SEP}")
        print("姝ラ4: 闃堝€煎垽瀹?)
        print(SEP)
        confidence, filtered = threshold.filter_candidates(reranked)
        print(f"  缃俊搴? {confidence}")
        print(f"  杩斿洖鍊欓€? {len(filtered)} 鏉?)

        if len(reranked) >= 2:
            gap = reranked[0][1] - reranked[1][1]
            print(f"  Top1-Top2宸€? {gap:.4f}")
        print(f"  Top1鍒嗘暟: {reranked[0][1]:.4f}")

        print(f"\n  馃搶 鏈€缁堢粨鏋? 缃俊搴?{confidence}, 杩斿洖{len(filtered)}鏉″€欓€?)

        if i < len(test_questions):
            input(f"\n>>> 鎸夊洖杞︾户缁笅涓€涓煡璇?({i}/{len(test_questions)}) ...")

    print(f"\n{SEP}")
    print("  Demo 2 瀹屾垚")
    print(SEP)


if __name__ == "__main__":
    main()