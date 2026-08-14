"""
Demo 3: 入库预处理演示
展示: 工单数据 → clean_text → structure_ingest → hyde_rewrite → 标准化入库条目

运行: python demo/demo3_agent_ingest.py
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


def demo_clean_text(question, answer):
    from agent.processors.clean_text import clean_text
    from agent.state import AgentState

    print(f"\n{SEP}")
    print("步骤1: clean_text（防御性清洗）")
    print(SEP)
    print(f"  问题输入: \"{question}\"")
    print(f"  答案输入: \"{answer}\"")

    state = AgentState(raw_question=question, raw_answer=answer)
    result = clean_text(state)

    print(f"  问题输出: \"{result['question']}\"")
    print(f"  答案输出: \"{result['answer']}\"")

    return result["question"], result["answer"]


def demo_structure_ingest(question, answer):
    from agent.processors.structure_ingest import structure_ingest
    from agent.state import AgentState

    print(f"\n{SEP}")
    print("步骤2: structure_ingest（结构化规整+分类）")
    print(SEP)
    print(f"  输入: \"{question}\"")

    state = AgentState(raw_question=question, question=question, answer=answer)
    t0 = time.time()
    result = structure_ingest(state)
    elapsed = time.time() - t0

    print(f"  改写后问题: \"{result.get('question', question)}\"")
    print(f"  结构化答案: \"{result.get('answer', '')}\"")
    print(f"  内部流程: \"{result.get('internal_process', '')}\"")
    print(f"  反馈部门: \"{result.get('feedback_dept', '')}\"")
    print(f"  一级分类: {result.get('category_l1', '')}")
    print(f"  二级分类: {result.get('category_l2', '')}")
    print(f"  分类置信度: {result.get('category_confidence', 'N/A')}")
    print(f"  需人工审核: {result.get('needs_review', False)}")
    print(f"  耗时: {elapsed:.2f}s")

    return result


def demo_hyde_rewrite(question, answer):
    from agent.processors.hyde_rewrite import hyde_rewrite
    from agent.state import AgentState

    print(f"\n{SEP}")
    print("步骤3: hyde_rewrite（条件改写）")
    print(SEP)
    print(f"  输入: \"{question}\"")
    print("  判断是否需要HyDE改写...")

    state = AgentState(raw_question=question, question=question, answer=answer)
    t0 = time.time()
    result = hyde_rewrite(state)
    elapsed = time.time() - t0

    need_rewrite = result.get("need_rewrite", None)
    hyde_questions = result.get("hyde_questions", [])

    if need_rewrite is not None:
        print(f"  是否需要改写: {need_rewrite}")
    if need_rewrite and hyde_questions:
        print(f"  生成的假设性问题:")
        for j, hq in enumerate(hyde_questions, 1):
            print(f"    {j}. \"{hq}\"")
    elif not need_rewrite:
        print("  跳过改写（问题已足够标准）")
    print(f"  耗时: {elapsed:.2f}s")

    return result


def main():
    print(SEP)
    print("  Demo 3: 入库预处理")
    print(SEP)

    print("\n加载配置和模型...")
    load_config()

    test_cases = [
        {
            "question": "客户张三（电话：13800138000）反馈：ETC重复扣费了上个月在同一高速口扣了两次",
            "answer": "核实扣费记录，确认重复扣费后3个工作日退款至原账户",
        },
        {
            "question": "用户来电说OBU设备蓝牙连不上，手机搜不到设备信号",
            "answer": "引导用户重置OBU蓝牙模块，重新配对连接",
        },
    ]

    for i, tc in enumerate(test_cases, 1):
        print(f"\n{'#' * 60}")
        print(f"  测试用例 {i}/{len(test_cases)}")
        print(f"  工单问题: \"{tc['question']}\"")
        print(f"  工单答案: \"{tc['answer']}\"")
        print(f"{'#' * 60}")

        cleaned_q, cleaned_a = demo_clean_text(tc["question"], tc["answer"])
        ingest_result = demo_structure_ingest(cleaned_q, cleaned_a)
        hyde_result = demo_hyde_rewrite(
            ingest_result.get("question", cleaned_q),
            ingest_result.get("answer", cleaned_a),
        )

        print(f"\n  📌 最终入库条目:")
        print(f"    问题: \"{ingest_result.get('question', cleaned_q)}\"")
        print(f"    答案: \"{ingest_result.get('answer', cleaned_a)}\"")
        print(f"    分类: {ingest_result.get('category_l1', '')}/{ingest_result.get('category_l2', '')}")

        if i < len(test_cases):
            input(f"\n>>> 按回车继续下一个用例 ({i}/{len(test_cases)}) ...")

    print(f"\n{SEP}")
    print("  Demo 3 完成")
    print(SEP)


if __name__ == "__main__":
    main()