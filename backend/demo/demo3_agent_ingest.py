"""
Demo 3: 鍏ュ簱棰勫鐞嗘紨绀?灞曠ず: 宸ュ崟鏁版嵁 鈫?clean_text 鈫?structure_ingest 鈫?hyde_rewrite 鈫?鏍囧噯鍖栧叆搴撴潯鐩?
杩愯: python demo/demo3_agent_ingest.py
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
    print("姝ラ1: clean_text锛堥槻寰℃€ф竻娲楋級")
    print(SEP)
    print(f"  闂杈撳叆: \"{question}\"")
    print(f"  绛旀杈撳叆: \"{answer}\"")

    state = AgentState(raw_question=question, raw_answer=answer)
    result = clean_text(state)

    print(f"  闂杈撳嚭: \"{result['question']}\"")
    print(f"  绛旀杈撳嚭: \"{result['answer']}\"")

    return result["question"], result["answer"]


def demo_structure_ingest(question, answer):
    from agent.processors.structure_ingest import structure_ingest
    from agent.state import AgentState

    print(f"\n{SEP}")
    print("姝ラ2: structure_ingest锛堢粨鏋勫寲瑙勬暣+鍒嗙被锛?)
    print(SEP)
    print(f"  杈撳叆: \"{question}\"")

    state = AgentState(raw_question=question, question=question, answer=answer)
    t0 = time.time()
    result = structure_ingest(state)
    elapsed = time.time() - t0

    print(f"  鏀瑰啓鍚庨棶棰? \"{result.get('question', question)}\"")
    print(f"  缁撴瀯鍖栫瓟妗? \"{result.get('answer', '')}\"")
    print(f"  鍐呴儴娴佺▼: \"{result.get('internal_process', '')}\"")
    print(f"  鍙嶉閮ㄩ棬: \"{result.get('feedback_dept', '')}\"")
    print(f"  涓€绾у垎绫? {result.get('category_l1', '')}")
    print(f"  浜岀骇鍒嗙被: {result.get('category_l2', '')}")
    print(f"  鍒嗙被缃俊搴? {result.get('category_confidence', 'N/A')}")
    print(f"  闇€浜哄伐瀹℃牳: {result.get('needs_review', False)}")
    print(f"  鑰楁椂: {elapsed:.2f}s")

    return result


def demo_hyde_rewrite(question, answer):
    from agent.processors.hyde_rewrite import hyde_rewrite
    from agent.state import AgentState

    print(f"\n{SEP}")
    print("姝ラ3: hyde_rewrite锛堟潯浠舵敼鍐欙級")
    print(SEP)
    print(f"  杈撳叆: \"{question}\"")
    print("  鍒ゆ柇鏄惁闇€瑕丠yDE鏀瑰啓...")

    state = AgentState(raw_question=question, question=question, answer=answer)
    t0 = time.time()
    result = hyde_rewrite(state)
    elapsed = time.time() - t0

    need_rewrite = result.get("need_rewrite", None)
    hyde_questions = result.get("hyde_questions", [])

    if need_rewrite is not None:
        print(f"  鏄惁闇€瑕佹敼鍐? {need_rewrite}")
    if need_rewrite and hyde_questions:
        print(f"  鐢熸垚鐨勫亣璁炬€ч棶棰?")
        for j, hq in enumerate(hyde_questions, 1):
            print(f"    {j}. \"{hq}\"")
    elif not need_rewrite:
        print("  璺宠繃鏀瑰啓锛堥棶棰樺凡瓒冲鏍囧噯锛?)
    print(f"  鑰楁椂: {elapsed:.2f}s")

    return result


def main():
    print(SEP)
    print("  Demo 3: 鍏ュ簱棰勫鐞?)
    print(SEP)

    print("\n鍔犺浇閰嶇疆鍜屾ā鍨?..")
    load_config()

    test_cases = [
        {
            "question": "瀹㈡埛寮犱笁锛堢數璇濓細13800138000锛夊弽棣堬細ETC閲嶅鎵ｈ垂浜嗕笂涓湀鍦ㄥ悓涓€楂橀€熷彛鎵ｄ簡涓ゆ",
            "answer": "鏍稿疄鎵ｈ垂璁板綍锛岀‘璁ら噸澶嶆墸璐瑰悗3涓伐浣滄棩閫€娆捐嚦鍘熻处鎴?,
        },
        {
            "question": "鐢ㄦ埛鏉ョ數璇碠BU璁惧钃濈墮杩炰笉涓婏紝鎵嬫満鎼滀笉鍒拌澶囦俊鍙?,
            "answer": "寮曞鐢ㄦ埛閲嶇疆OBU钃濈墮妯″潡锛岄噸鏂伴厤瀵硅繛鎺?,
        },
    ]

    for i, tc in enumerate(test_cases, 1):
        print(f"\n{'#' * 60}")
        print(f"  娴嬭瘯鐢ㄤ緥 {i}/{len(test_cases)}")
        print(f"  宸ュ崟闂: \"{tc['question']}\"")
        print(f"  宸ュ崟绛旀: \"{tc['answer']}\"")
        print(f"{'#' * 60}")

        cleaned_q, cleaned_a = demo_clean_text(tc["question"], tc["answer"])
        ingest_result = demo_structure_ingest(cleaned_q, cleaned_a)
        hyde_result = demo_hyde_rewrite(
            ingest_result.get("question", cleaned_q),
            ingest_result.get("answer", cleaned_a),
        )

        print(f"\n  馃搶 鏈€缁堝叆搴撴潯鐩?")
        print(f"    闂: \"{ingest_result.get('question', cleaned_q)}\"")
        print(f"    绛旀: \"{ingest_result.get('answer', cleaned_a)}\"")
        print(f"    鍒嗙被: {ingest_result.get('category_l1', '')}/{ingest_result.get('category_l2', '')}")

        if i < len(test_cases):
            input(f"\n>>> 鎸夊洖杞︾户缁笅涓€涓敤渚?({i}/{len(test_cases)}) ...")

    print(f"\n{SEP}")
    print("  Demo 3 瀹屾垚")
    print(SEP)


if __name__ == "__main__":
    main()