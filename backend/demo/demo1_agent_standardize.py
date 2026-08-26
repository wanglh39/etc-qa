"""
Demo 1: Agent标准化预处理演示
展示: 原始问题 → clean_text → standardize_query → 标准化问题

运行: python demo/demo1_agent_standardize.py
"""

import os
import sys
import time

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("ETC_QA_ENV", "dev")

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, PROJECT_ROOT)

from utils.config import load_config

SEP = "=" * 60


def demo_clean_text(question):
    from agent.processors.clean_text import clean_text
    from agent.state import AgentState

    print(f"\n{SEP}")
    print("步骤1: clean_text（防御性清洗）")
    print(SEP)
    print(f'  输入: "{question}"')

    state = AgentState(raw_question=question)
    result = clean_text(state)
    cleaned = result["question"]

    print(f'  输出: "{cleaned}"')

    if cleaned != question:
        print("  变化: ✅ 有清洗效果")
    else:
        print("  变化: 无变化（该问题无需清洗）")

    return cleaned


def demo_standardize_query(question):
    from agent.processors.standardize_query import standardize_query
    from agent.state import AgentState

    print(f"\n{SEP}")
    print("步骤2: standardize_query（智能规整）")
    print(SEP)
    print(f'  输入: "{question}"')
    print("  策略: 规则优先 + LLM兜底")

    state = AgentState(raw_question=question, question=question)
    t0 = time.time()
    result = standardize_query(state)
    elapsed = time.time() - t0

    standardized = result.get("question", question)
    need_rewrite = result.get("need_rewrite", None)
    rewrite_confidence = result.get("rewrite_confidence", None)

    print(f'  输出: "{standardized}"')
    if need_rewrite is not None:
        print(f"  是否改写: {need_rewrite}")
    if rewrite_confidence is not None:
        print(f"  改写置信度: {rewrite_confidence}")
    print(f"  耗时: {elapsed:.2f}s")

    if standardized != question:
        print("  变化: ✅ 有规整效果")
    else:
        print("  变化: 无变化")

    return standardized


def main():
    print(SEP)
    print("  Demo 1: Agent标准化预处理")
    print(SEP)

    print("\n加载配置和模型...")
    load_config()

    test_cases = [
        "我想问一下ETC扣费异常怎么处理啊",
        "客户张三（电话：13800138000）反馈：ETC重复扣费了",
        "咋整啊ETC设备不亮了",
        "ETC怎么注销",
        "请问一下那个蓝牙OBU连接不上怎么办呢谢谢",
        "上个月在高速口被多扣了一次费但是不知道是哪次通行产生的想查一下明细",
        "通行后一直没收到扣费通知担心是不是漏扣了还是系统出问题了",
    ]

    for i, raw_q in enumerate(test_cases, 1):
        print(f"\n{'#' * 60}")
        print(f"  测试用例 {i}/{len(test_cases)}")
        print(f'  原始问题: "{raw_q}"')
        print(f"{'#' * 60}")

        cleaned = demo_clean_text(raw_q)
        standardized = demo_standardize_query(cleaned)

        print(f'\n  📌 最终结果: "{raw_q}" → "{standardized}"')

        if i < len(test_cases):
            input(f"\n>>> 按回车继续下一个用例 ({i}/{len(test_cases)}) ...")

    print(f"\n{SEP}")
    print("  Demo 1 完成")
    print(SEP)


if __name__ == "__main__":
    main()
