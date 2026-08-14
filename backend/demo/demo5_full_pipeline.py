"""
Demo 5: 瀹㈡湇杈呭姪妫€绱㈠叏閾捐矾婕旂ず
灞曠ず: 瀹㈡埛闂 鈫?Agent鏍囧噯鍖?鈫?RAG妫€绱?鈫?缁欏鏈嶆彁绀哄€欓€?鈫?瀹㈡湇閫夋嫨鍥炵瓟

涓氬姟鍦烘櫙:
  瀹㈡埛鎵撶數璇濇弿杩伴棶棰?鈫?瀹㈡湇鍚埌鍚庤緭鍏ョ郴缁?鈫?绯荤粺鏍囧噯鍖?妫€绱?鈫?杩斿洖鍊欓€夌瓟妗?鈫?瀹㈡湇瀹℃牳鍚庡洖绛斿鎴?
杩愯: python demo/demo5_full_pipeline.py
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
    print("  Demo 5: 瀹㈡湇杈呭姪妫€绱㈠叏閾捐矾")
    print("  鍦烘櫙: 瀹㈡埛鎻忚堪闂 鈫?绯荤粺鏍囧噯鍖?妫€绱?鈫?缁欏鏈嶅€欓€夋彁绀?鈫?瀹㈡湇閫夋嫨鍥炵瓟")
    print(SEP)

    print("\n鍒濆鍖栫郴缁?..")
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
    service = QAService(recall, threshold, reranker, mysql)

    print(f"  鐭ヨ瘑搴撴潯鐩? {len(all_qa)}")
    print("  绯荤粺灏辩华锛乗n")

    test_cases = [
        {
            "customer": "鎴戞兂闂竴涓婨TC鎵ｈ垂寮傚父鎬庝箞澶勭悊鍟?,
            "context": "瀹㈡埛鏉ョ數鍜ㄨETC鎵ｈ垂寮傚父",
        },
        {
            "customer": "ETC璁惧涓嶄寒浜嗗拫鏁?,
            "context": "瀹㈡埛鍙嶉璁惧鏁呴殰",
        },
        {
            "customer": "濡備綍娉ㄩ攢ETC璐︽埛",
            "context": "瀹㈡埛鐢宠娉ㄩ攢",
        },
        {
            "customer": "钃濈墮OBU杩炴帴涓嶄笂鎬庝箞鍔?,
            "context": "瀹㈡埛鍙嶉钃濈墮杩炴帴闂",
        },
        {
            "customer": "涓婁釜鏈堝湪楂橀€熷彛琚鎵ｄ簡涓€娆¤垂浣嗘槸涓嶇煡閬撴槸鍝閫氳浜х敓鐨勬兂鏌ヤ竴涓嬫槑缁?,
            "context": "瀹㈡埛鎶曡瘔澶氭墸璐?,
        },
    ]

    for i, tc in enumerate(test_cases, 1):
        print(f"\n{'#' * 60}")
        print(f"  閫氳瘽 {i}/{len(test_cases)}")
        print(f"{'#' * 60}")

        print(f"\n  [鍦烘櫙] {tc['context']}")
        print(f"  [瀹㈡埛璇碷 \"{tc['customer']}\"")
        print(f"  [瀹㈡湇杈撳叆绯荤粺] \"{tc['customer']}\"")

        t_total = time.time()
        result = service.query(tc["customer"])
        t_total = time.time() - t_total

        print(f"\n  [绯荤粺澶勭悊] 鑰楁椂 {t_total:.2f}s")
        print(f"  鍘熷闂:   \"{result.query}\"")
        print(f"  鏍囧噯鍖栧悗:   \"{result.standardized_query}\"")
        print(f"  缃俊搴?     {result.confidence}")
        print(f"  鍊欓€夋暟閲?   {result.total_candidates}")

        if result.candidates:
            print(f"\n  [缁欏鏈嶇殑鍊欓€夋彁绀篯")
            for j, c in enumerate(result.candidates[:3], 1):
                print(f"    [{j}] 鍒嗘暟={c.score:.4f} | {c.category_l1}/{c.category_l2}")
                print(f"        闂: \"{c.question}\"")
                print(f"        绛旀: \"{c.answer[:80]}{'...' if len(c.answer) > 80 else ''}\"")
                if c.internal_process:
                    print(f"        鍐呴儴娴佺▼: \"{c.internal_process[:60]}\"")
                if c.feedback_dept:
                    print(f"        鍙嶉閮ㄩ棬: {c.feedback_dept}")

            print(f"\n  [瀹㈡湇瀹℃牳]")
            print(f"  瀹㈡湇閫夋嫨鍊欓€?[1] 鍥炵瓟瀹㈡埛")
            top = result.candidates[0]
            print(f"  瀹㈡湇鍥炵瓟瀹㈡埛: \"{top.answer[:100]}\"")
            if top.internal_process:
                print(f"  鍐呴儴鎿嶄綔: \"{top.internal_process[:80]}\"")
            if top.feedback_dept:
                print(f"  闇€娴佽浆鑷? {top.feedback_dept}")
        else:
            print(f"\n  [绯荤粺鎻愮ず] 鏈壘鍒板尮閰嶇瓟妗堬紝寤鸿杞汉宸ュ鐞?)

        if i < len(test_cases):
            input(f"\n>>> 鎸夊洖杞︾户缁笅涓€涓€氳瘽 ({i}/{len(test_cases)}) ...")

    print(f"\n{SEP}")
    print("  Demo 5 瀹屾垚")
    print(SEP)


if __name__ == "__main__":
    main()