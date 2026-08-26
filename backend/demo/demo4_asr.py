"""
Demo 4: 客服通话场景演示
展示: 客户打电话 → 语音识别 → 领域纠错 → RAG检索 → 给客服提示候选答案 → 客服选择回答

运行: python demo/demo4_asr.py
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
    return QAService(recall, threshold, reranker, mysql)


def simulate_customer_call(asr_text, rag_service):
    print(f'\n  客户说: "{asr_text}"')

    t0 = time.time()
    rag_result = rag_service.query(asr_text)
    elapsed = time.time() - t0

    print(f"\n  系统检索完成 ({elapsed:.2f}s):")
    print(f'  标准化: "{rag_result.standardized_query}"')
    print(f"  置信度: {rag_result.confidence}")

    if rag_result.candidates:
        print(f"\n  给客服的候选提示:")
        for j, c in enumerate(rag_result.candidates[:3], 1):
            print(f"    [{j}] 分数={c.score:.4f} | {c.category_l1}/{c.category_l2}")
            print(f'        问题: "{c.question}"')
            print(f'        答案: "{c.answer[:80]}{"..." if len(c.answer) > 80 else ""}"')
            if c.internal_process:
                print(f'        内部流程: "{c.internal_process[:60]}"')
            if c.feedback_dept:
                print(f"        反馈部门: {c.feedback_dept}")

        print(f"\n  客服审核: 选择候选 [1] 回答客户")
        top = rag_result.candidates[0]
        print(f'  客服回答: "{top.answer[:100]}"')
    else:
        print(f"\n  未找到匹配答案，建议转人工处理")

    return rag_result


def main():
    print(SEP)
    print("  Demo 4: 客服通话场景演示")
    print("  场景: 客户打电话 → 语音识别 → RAG检索 → 给客服提示候选答案")
    print(SEP)

    print("\n加载配置...")
    cfg = load_config()

    asr_cfg = cfg.get("asr", {})
    if not asr_cfg.get("enabled", False):
        print("  ASR未启用，请在config/asr.yaml中设置 asr.enabled=true")
        return

    print("\n初始化ASR模型...")
    from asr.service import ASRService

    asr = ASRService()

    diarize_cfg = asr_cfg.get("diarize", {})
    diarize_enabled = diarize_cfg.get("enabled", False)
    if diarize_enabled:
        print("  说话人分离: 已启用")
    else:
        print("  说话人分离: 未启用")

    print("\n初始化RAG检索服务...")
    rag_service = init_rag_service(cfg)

    samples_dir = os.path.join(PROJECT_ROOT, "data", "asr_samples")
    if not os.path.isdir(samples_dir):
        print(f"  未找到音频样本目录: {samples_dir}")
        return

    wav_files = sorted([f for f in os.listdir(samples_dir) if f.endswith(".wav")])
    if not wav_files:
        print("  音频样本目录为空")
        return

    print(f"\n  找到 {len(wav_files)} 个音频样本")
    print(f"  知识库条目: {len(rag_service.mysql.get_all_questions())}")

    test_count = min(5, len(wav_files))
    for i, wav_file in enumerate(wav_files[:test_count], 1):
        wav_path = os.path.join(samples_dir, wav_file)
        print(f"\n{'#' * 60}")
        print(f"  通话 {i}/{test_count}: {wav_file}")
        print(f"{'#' * 60}")

        print(f"\n  [客户来电] 音频文件: {wav_file}")

        print(f"\n  [语音识别]")
        t0 = time.time()
        result = asr.transcribe(wav_path)
        asr_time = time.time() - t0
        print(f'  识别结果: "{result.text}"')
        print(f"  置信度: {result.confidence} | 耗时: {asr_time:.2f}s")

        if result.segments:
            speakers = set(s.speaker for s in result.segments)
            print(f"  说话人分离: 检测到 {len(speakers)} 位说话人")
            for seg in result.segments:
                print(f'    [{seg.start:.1f}s-{seg.end:.1f}s] {seg.speaker}: "{seg.text}"')

        if not result.text.strip():
            print("  识别为空，跳过检索")
            continue

        print(f"\n  [RAG检索 → 给客服提示]")
        simulate_customer_call(result.text, rag_service)

        if i < test_count:
            input(f"\n>>> 按回车继续下一个通话 ({i}/{test_count}) ...")

    print(f"\n{SEP}")
    print("  Demo 4 完成")
    print(SEP)


if __name__ == "__main__":
    main()
