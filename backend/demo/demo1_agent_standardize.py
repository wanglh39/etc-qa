"""
Demo 1: Agent鏍囧噯鍖栭澶勭悊婕旂ず
灞曠ず: 鍘熷闂 鈫?clean_text 鈫?standardize_query 鈫?鏍囧噯鍖栭棶棰?
杩愯: python demo/demo1_agent_standardize.py
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
    print("姝ラ1: clean_text锛堥槻寰℃€ф竻娲楋級")
    print(SEP)
    print(f"  杈撳叆: \"{question}\"")

    state = AgentState(raw_question=question)
    result = clean_text(state)
    cleaned = result["question"]

    print(f"  杈撳嚭: \"{cleaned}\"")

    if cleaned != question:
        print("  鍙樺寲: 鉁?鏈夋竻娲楁晥鏋?)
    else:
        print("  鍙樺寲: 鏃犲彉鍖栵紙璇ラ棶棰樻棤闇€娓呮礂锛?)

    return cleaned


def demo_standardize_query(question):
    from agent.processors.standardize_query import standardize_query
    from agent.state import AgentState

    print(f"\n{SEP}")
    print("姝ラ2: standardize_query锛堟櫤鑳借鏁达級")
    print(SEP)
    print(f"  杈撳叆: \"{question}\"")
    print("  绛栫暐: 瑙勫垯浼樺厛 + LLM鍏滃簳")

    state = AgentState(raw_question=question, question=question)
    t0 = time.time()
    result = standardize_query(state)
    elapsed = time.time() - t0

    standardized = result.get("question", question)
    need_rewrite = result.get("need_rewrite", None)
    rewrite_confidence = result.get("rewrite_confidence", None)

    print(f"  杈撳嚭: \"{standardized}\"")
    if need_rewrite is not None:
        print(f"  鏄惁鏀瑰啓: {need_rewrite}")
    if rewrite_confidence is not None:
        print(f"  鏀瑰啓缃俊搴? {rewrite_confidence}")
    print(f"  鑰楁椂: {elapsed:.2f}s")

    if standardized != question:
        print("  鍙樺寲: 鉁?鏈夎鏁存晥鏋?)
    else:
        print("  鍙樺寲: 鏃犲彉鍖?)

    return standardized


def main():
    print(SEP)
    print("  Demo 1: Agent鏍囧噯鍖栭澶勭悊")
    print(SEP)

    print("\n鍔犺浇閰嶇疆鍜屾ā鍨?..")
    load_config()

    test_cases = [
        "鎴戞兂闂竴涓婨TC鎵ｈ垂寮傚父鎬庝箞澶勭悊鍟?,
        "瀹㈡埛寮犱笁锛堢數璇濓細13800138000锛夊弽棣堬細ETC閲嶅鎵ｈ垂浜?,
        "鍜嬫暣鍟奅TC璁惧涓嶄寒浜?,
        "ETC鎬庝箞娉ㄩ攢",
        "璇烽棶涓€涓嬮偅涓摑鐗橭BU杩炴帴涓嶄笂鎬庝箞鍔炲憿璋㈣阿",
        "涓婁釜鏈堝湪楂橀€熷彛琚鎵ｄ簡涓€娆¤垂浣嗘槸涓嶇煡閬撴槸鍝閫氳浜х敓鐨勬兂鏌ヤ竴涓嬫槑缁?,
        "閫氳鍚庝竴鐩存病鏀跺埌鎵ｈ垂閫氱煡鎷呭績鏄笉鏄紡鎵ｄ簡杩樻槸绯荤粺鍑洪棶棰樹簡",
    ]

    for i, raw_q in enumerate(test_cases, 1):
        print(f"\n{'#' * 60}")
        print(f"  娴嬭瘯鐢ㄤ緥 {i}/{len(test_cases)}")
        print(f"  鍘熷闂: \"{raw_q}\"")
        print(f"{'#' * 60}")

        cleaned = demo_clean_text(raw_q)
        standardized = demo_standardize_query(cleaned)

        print(f"\n  馃搶 鏈€缁堢粨鏋? \"{raw_q}\" 鈫?\"{standardized}\"")

        if i < len(test_cases):
            input(f"\n>>> 鎸夊洖杞︾户缁笅涓€涓敤渚?({i}/{len(test_cases)}) ...")

    print(f"\n{SEP}")
    print("  Demo 1 瀹屾垚")
    print(SEP)


if __name__ == "__main__":
    main()