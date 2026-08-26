"""
Demo 5: 客服辅助检索全链路演示
展示: 客户问题 → Agent标准化 → RAG检索 → 给客服提示候选 → 客服选择回答

业务场景:
  客户打电话描述问题 → 客服听到后输入系统 → 系统标准化+检索 → 返回候选答案 → 客服审核后回答客户

运行: python demo/demo5_full_pipeline.py
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
from rag.service import QAService
from rag.threshold import ThresholdJudge
from utils.config import load_config

SEP = "=" * 60


def main():
    print(SEP)
    print("  Demo 5: 客服辅助检索全链路")
    print("  场景: 客户描述问题 → 系统标准化+检索 → 给客服候选提示 → 客服选择回答")
    print(SEP)

    print("\n初始化系统...")
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
    service = QAService(recall, threshold, reranker, mysql)

    print(f"  知识库条目: {len(all_qa)}")
    print("  系统就绪！\n")

    test_cases = [
        {
            "customer": "我想问一下ETC扣费异常怎么处理啊",
            "context": "客户来电咨询ETC扣费异常",
        },
        {
            "customer": "ETC设备不亮了咋整",
            "context": "客户反馈设备故障",
        },
        {
            "customer": "如何注销ETC账户",
            "context": "客户申请注销",
        },
        {
            "customer": "蓝牙OBU连接不上怎么办",
            "context": "客户反馈蓝牙连接问题",
        },
        {
            "customer": "上个月在高速口被多扣了一次费但是不知道是哪次通行产生的想查一下明细",
            "context": "客户投诉多扣费",
        },
    ]

    for i, tc in enumerate(test_cases, 1):
        print(f"\n{'#' * 60}")
        print(f"  通话 {i}/{len(test_cases)}")
        print(f"{'#' * 60}")

        print(f"\n  [场景] {tc['context']}")
        print(f'  [客户说] "{tc["customer"]}"')
        print(f'  [客服输入系统] "{tc["customer"]}"')

        t_total = time.time()
        result = service.query(tc["customer"])
        t_total = time.time() - t_total

        print(f"\n  [系统处理] 耗时 {t_total:.2f}s")
        print(f'  原始问题:   "{result.query}"')
        print(f'  标准化后:   "{result.standardized_query}"')
        print(f"  置信度:     {result.confidence}")
        print(f"  候选数量:   {result.total_candidates}")

        if result.candidates:
            print(f"\n  [给客服的候选提示]")
            for j, c in enumerate(result.candidates[:3], 1):
                print(f"    [{j}] 分数={c.score:.4f} | {c.category_l1}/{c.category_l2}")
                print(f'        问题: "{c.question}"')
                print(f'        答案: "{c.answer[:80]}{"..." if len(c.answer) > 80 else ""}"')
                if c.internal_process:
                    print(f'        内部流程: "{c.internal_process[:60]}"')
                if c.feedback_dept:
                    print(f"        反馈部门: {c.feedback_dept}")

            print(f"\n  [客服审核]")
            print(f"  客服选择候选 [1] 回答客户")
            top = result.candidates[0]
            print(f'  客服回答客户: "{top.answer[:100]}"')
            if top.internal_process:
                print(f'  内部操作: "{top.internal_process[:80]}"')
            if top.feedback_dept:
                print(f"  需流转至: {top.feedback_dept}")
        else:
            print(f"\n  [系统提示] 未找到匹配答案，建议转人工处理")

        if i < len(test_cases):
            input(f"\n>>> 按回车继续下一个通话 ({i}/{len(test_cases)}) ...")

    print(f"\n{SEP}")
    print("  Demo 5 完成")
    print(SEP)


if __name__ == "__main__":
    main()
