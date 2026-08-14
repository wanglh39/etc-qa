"""
Demo 4: 瀹㈡湇閫氳瘽鍦烘櫙婕旂ず
灞曠ず: 瀹㈡埛鎵撶數璇?鈫?璇煶璇嗗埆 鈫?棰嗗煙绾犻敊 鈫?RAG妫€绱?鈫?缁欏鏈嶆彁绀哄€欓€夌瓟妗?鈫?瀹㈡湇閫夋嫨鍥炵瓟

杩愯: python demo/demo4_asr.py
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


def init_rag_service(cfg):
    import torch
    torch.set_num_threads(1)
    from sentence_transformers import CrossEncoder, SentenceTransformer
    from db.milvus_client import MilvusQA
    from db.mysql_client import MySQLClient
    from rag.bm25_index import BM25Index
    from rag.recall import RecallEngine
    from rag.reranker import Reranker
    from rag.service import QAService
    from rag.threshold import ThresholdJudge

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
    return QAService(recall, threshold, reranker, mysql)


def simulate_customer_call(asr_text, rag_service):
    print(f"\n  瀹㈡埛璇? \"{asr_text}\"")

    t0 = time.time()
    rag_result = rag_service.query(asr_text)
    elapsed = time.time() - t0

    print(f"\n  绯荤粺妫€绱㈠畬鎴?({elapsed:.2f}s):")
    print(f"  鏍囧噯鍖? \"{rag_result.standardized_query}\"")
    print(f"  缃俊搴? {rag_result.confidence}")

    if rag_result.candidates:
        print(f"\n  缁欏鏈嶇殑鍊欓€夋彁绀?")
        for j, c in enumerate(rag_result.candidates[:3], 1):
            print(f"    [{j}] 鍒嗘暟={c.score:.4f} | {c.category_l1}/{c.category_l2}")
            print(f"        闂: \"{c.question}\"")
            print(f"        绛旀: \"{c.answer[:80]}{'...' if len(c.answer) > 80 else ''}\"")
            if c.internal_process:
                print(f"        鍐呴儴娴佺▼: \"{c.internal_process[:60]}\"")
            if c.feedback_dept:
                print(f"        鍙嶉閮ㄩ棬: {c.feedback_dept}")

        print(f"\n  瀹㈡湇瀹℃牳: 閫夋嫨鍊欓€?[1] 鍥炵瓟瀹㈡埛")
        top = rag_result.candidates[0]
        print(f"  瀹㈡湇鍥炵瓟: \"{top.answer[:100]}\"")
    else:
        print(f"\n  鏈壘鍒板尮閰嶇瓟妗堬紝寤鸿杞汉宸ュ鐞?)

    return rag_result


def main():
    print(SEP)
    print("  Demo 4: 瀹㈡湇閫氳瘽鍦烘櫙婕旂ず")
    print("  鍦烘櫙: 瀹㈡埛鎵撶數璇?鈫?璇煶璇嗗埆 鈫?RAG妫€绱?鈫?缁欏鏈嶆彁绀哄€欓€夌瓟妗?)
    print(SEP)

    print("\n鍔犺浇閰嶇疆...")
    cfg = load_config()

    asr_cfg = cfg.get("asr", {})
    if not asr_cfg.get("enabled", False):
        print("  ASR鏈惎鐢紝璇峰湪config/asr.yaml涓缃?asr.enabled=true")
        return

    print("\n鍒濆鍖朅SR妯″瀷...")
    from asr.service import ASRService
    asr = ASRService()

    diarize_cfg = asr_cfg.get("diarize", {})
    diarize_enabled = diarize_cfg.get("enabled", False)
    if diarize_enabled:
        print("  璇磋瘽浜哄垎绂? 宸插惎鐢?)
    else:
        print("  璇磋瘽浜哄垎绂? 鏈惎鐢?)

    print("\n鍒濆鍖朢AG妫€绱㈡湇鍔?..")
    rag_service = init_rag_service(cfg)

    samples_dir = os.path.join(PROJECT_ROOT, "data", "asr_samples")
    if not os.path.isdir(samples_dir):
        print(f"  鏈壘鍒伴煶棰戞牱鏈洰褰? {samples_dir}")
        return

    wav_files = sorted([f for f in os.listdir(samples_dir) if f.endswith(".wav")])
    if not wav_files:
        print("  闊抽鏍锋湰鐩綍涓虹┖")
        return

    print(f"\n  鎵惧埌 {len(wav_files)} 涓煶棰戞牱鏈?)
    print(f"  鐭ヨ瘑搴撴潯鐩? {len(rag_service.mysql.get_all_questions())}")

    test_count = min(5, len(wav_files))
    for i, wav_file in enumerate(wav_files[:test_count], 1):
        wav_path = os.path.join(samples_dir, wav_file)
        print(f"\n{'#' * 60}")
        print(f"  閫氳瘽 {i}/{test_count}: {wav_file}")
        print(f"{'#' * 60}")

        print(f"\n  [瀹㈡埛鏉ョ數] 闊抽鏂囦欢: {wav_file}")

        print(f"\n  [璇煶璇嗗埆]")
        t0 = time.time()
        result = asr.transcribe(wav_path)
        asr_time = time.time() - t0
        print(f"  璇嗗埆缁撴灉: \"{result.text}\"")
        print(f"  缃俊搴? {result.confidence} | 鑰楁椂: {asr_time:.2f}s")

        if result.segments:
            speakers = set(s.speaker for s in result.segments)
            print(f"  璇磋瘽浜哄垎绂? 妫€娴嬪埌 {len(speakers)} 浣嶈璇濅汉")
            for seg in result.segments:
                print(f"    [{seg.start:.1f}s-{seg.end:.1f}s] {seg.speaker}: \"{seg.text}\"")

        if not result.text.strip():
            print("  璇嗗埆涓虹┖锛岃烦杩囨绱?)
            continue

        print(f"\n  [RAG妫€绱?鈫?缁欏鏈嶆彁绀篯")
        simulate_customer_call(result.text, rag_service)

        if i < test_count:
            input(f"\n>>> 鎸夊洖杞︾户缁笅涓€涓€氳瘽 ({i}/{test_count}) ...")

    print(f"\n{SEP}")
    print("  Demo 4 瀹屾垚")
    print(SEP)


if __name__ == "__main__":
    main()