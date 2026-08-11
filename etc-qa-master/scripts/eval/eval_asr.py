"""
ASR端到端测试：语音识别 → 文本纠错 → RAG检索 → 答案验证
用法：
  1. pip install edge-tts
  2. python scripts/eval_asr.py              # 完整测试（合成+识别+检索）
  3. python scripts/eval_asr.py --skip-tts   # 跳过合成，用已有音频
  4. python scripts/eval_asr.py --rag-only   # 只测RAG（用test_questions.json的文本）
"""
import argparse
import asyncio
import json
import os
import sys
from collections import defaultdict
from difflib import SequenceMatcher

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ['ETC_QA_ENV'] = os.environ.get('ETC_QA_ENV', 'dev')

OUTPUT_DIR = os.path.join(ROOT, "output")
SAMPLES_DIR = os.path.join(ROOT, "data", "asr_samples")
TEST_QUESTIONS_PATH = os.path.join(SAMPLES_DIR, "test_questions.json")

VOICE = "zh-CN-XiaoxiaoNeural"


def calculate_cer(reference: str, hypothesis: str) -> float:
    import re
    strip_re = re.compile(r'[，。？！、；：""'r'（）\s]')
    ref_clean = strip_re.sub('', reference)
    hyp_clean = strip_re.sub('', hypothesis)
    if not ref_clean:
        return 1.0 if hyp_clean else 0.0
    matcher = SequenceMatcher(None, ref_clean, hyp_clean)
    edits = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != "equal":
            edits += max(i2 - i1, j2 - j1)
    return edits / len(ref_clean)


async def synthesize_audio(text: str, output_path: str):
    import edge_tts
    communicate = edge_tts.Communicate(text, VOICE)
    mp3_path = output_path.replace(".wav", ".mp3")
    await communicate.save(mp3_path)
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_mp3(mp3_path)
        audio.export(output_path, format="wav")
        os.remove(mp3_path)
    except ImportError:
        if os.path.exists(mp3_path):
            os.rename(mp3_path, output_path)


def find_expected_id(expected_question: str, question_to_ids: dict) -> int:
    for q, qid in question_to_ids.items():
        q_clean = q.replace("\n", "").replace(" ", "")
        e_clean = expected_question.replace("\n", "").replace(" ", "")
        if e_clean in q_clean or q_clean in e_clean:
            return qid
    return None


def load_qa_index(mysql_client):
    all_qa = mysql_client.get_all_questions()
    question_to_ids = {}
    for qa in all_qa:
        q = qa["question"]
        if q not in question_to_ids:
            question_to_ids[q] = qa["id"]
    qa_dict = {qa["id"]: qa for qa in all_qa}
    return question_to_ids, qa_dict


def load_test_questions() -> list:
    if os.path.exists(TEST_QUESTIONS_PATH):
        with open(TEST_QUESTIONS_PATH, encoding="utf-8") as f:
            return json.load(f)
    print(f"测试数据不存在: {TEST_QUESTIONS_PATH}")
    sys.exit(1)


def run_asr_test(args):
    print("=" * 60)
    print("ASR端到端测试")
    print("=" * 60)

    test_questions = load_test_questions()
    print(f"加载测试数据: {len(test_questions)}条 (from {TEST_QUESTIONS_PATH})")

    if not args.rag_only:
        try:
            import edge_tts
        except ImportError:
            print("请先安装: pip install edge-tts")
            sys.exit(1)

    from asr.service import _apply_corrections, _load_corrections, get_asr_service
    asr_service = get_asr_service()
    corrections = _load_corrections()
    print(f"加载纠错表: {len(corrections)}条 (DB优先→config/asr.yaml兜底)")

    if not asr_service._enabled and not args.rag_only:
        print("ASR未启用，请在config/asr.yaml中设置asr.enabled=true")
        sys.exit(1)

    rag_service = None
    if not args.asr_only:
        from app import create_service
        print("初始化RAG服务...")
        rag_service = create_service()

    from db.mysql_client import MySQLClient
    mysql = MySQLClient()
    question_to_ids, qa_dict = load_qa_index(mysql)

    if not args.skip_tts and not args.rag_only:
        os.makedirs(SAMPLES_DIR, exist_ok=True)
        print(f"\n--- 第1步：合成音频 ({len(test_questions)}条) ---")
        for i, item in enumerate(test_questions, 1):
            wav_path = os.path.join(SAMPLES_DIR, f"sample_{i:02d}.wav")
            if os.path.exists(wav_path) and not args.force_tts:
                print(f"  [{i}/{len(test_questions)}] 已存在: {wav_path}")
                continue
            print(f"  [{i}/{len(test_questions)}] 合成: {item['text']}")
            asyncio.run(synthesize_audio(item["text"], wav_path))

        metadata = [
            {"filename": f"sample_{i:02d}.wav", **item}
            for i, item in enumerate(test_questions, 1)
        ]
        with open(os.path.join(SAMPLES_DIR, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

    results = []
    total_cer = 0
    total_cer_corrected = 0
    rag_hits = 0
    rag_total = 0

    print("\n--- 第2步：ASR识别 + 纠错 + RAG检索 ---")
    for i, item in enumerate(test_questions, 1):
        original_text = item["text"]
        category = item.get("category_l1", "")
        keyword = item.get("keyword", "")
        wav_path = os.path.join(SAMPLES_DIR, f"sample_{i:02d}.wav")

        if args.rag_only:
            asr_text = original_text
            confidence = 1.0
            duration_ms = 0
        else:
            if not os.path.exists(wav_path):
                print(f"  [{i}] 音频不存在: {wav_path}，跳过")
                continue

            try:
                resp = asr_service.transcribe(wav_path)
                asr_text_raw = resp.text
                confidence = resp.confidence
                duration_ms = resp.duration_ms
                asr_text = asr_text_raw
            except Exception as e:
                print(f"  [{i}] ASR识别失败: {e}")
                results.append({
                    "index": i, "original": original_text, "asr_text": "",
                    "corrected": "", "cer": 1.0, "cer_corrected": 1.0,
                    "confidence": 0, "duration_ms": 0,
                    "rag_hit": False, "error": str(e),
                })
                continue

        corrected = _apply_corrections(asr_text, corrections) if corrections else asr_text
        import re as _re
        _punct_re = _re.compile(r'[，。？！、；：""''（）]$')
        corrected = _punct_re.sub('', corrected)
        cer = calculate_cer(original_text, asr_text)
        cer_corrected = calculate_cer(original_text, corrected)
        total_cer += cer
        total_cer_corrected += cer_corrected

        expected_id = find_expected_id(original_text, question_to_ids)
        rag_hit = False
        rag_top1 = ""
        rag_top1_score = 0

        if rag_service and expected_id is not None:
            try:
                rag_result = rag_service.query(corrected)
                if rag_result.candidates:
                    top_id = rag_result.candidates[0].qa_id
                    rag_top1 = rag_result.candidates[0].question
                    rag_top1_score = rag_result.candidates[0].score
                    rag_hit = (top_id == expected_id)
                    rag_total += 1
                    if rag_hit:
                        rag_hits += 1
            except Exception as e:
                print(f"  [{i}] RAG检索失败: {e}")

        cer_mark = "OK" if cer < 0.1 else ("WARN" if cer < 0.2 else "FAIL")
        rag_mark = "HIT" if rag_hit else "MISS"

        print(f"  [{i:2d}] 原文: {original_text}")
        if not args.rag_only:
            print(f"       识别: {asr_text} (conf={confidence:.2f}, {duration_ms}ms)")
        if corrected != asr_text:
            print(f"       纠错: {corrected}")
        print(f"       CER: {cer:.1%}→{cer_corrected:.1%} [{cer_mark}]  RAG: [{rag_mark}]")

        results.append({
            "index": i, "original": original_text, "asr_text": asr_text,
            "corrected": corrected, "cer": round(cer, 4),
            "cer_corrected": round(cer_corrected, 4),
            "confidence": confidence, "duration_ms": duration_ms,
            "rag_hit": rag_hit, "rag_top1": rag_top1,
            "rag_top1_score": rag_top1_score,
            "category": category, "keyword": keyword,
        })

    n = len(results)
    avg_cer = total_cer / n if n else 0
    avg_cer_corrected = total_cer_corrected / n if n else 0
    rag_recall = rag_hits / rag_total if rag_total else 0

    print(f"\n{'='*60}")
    print("测试结果汇总")
    print(f"{'='*60}")
    print(f"  样本数:       {n}")
    print(f"  平均CER:      {avg_cer:.1%}")
    print(f"  纠错后CER:    {avg_cer_corrected:.1%}")
    print(f"  RAG Recall@1: {rag_recall:.1%} ({rag_hits}/{rag_total})")

    cer_dist = defaultdict(int)
    for r in results:
        c = r["cer_corrected"]
        if c == 0:
            cer_dist["0%"] += 1
        elif c < 0.05:
            cer_dist["<5%"] += 1
        elif c < 0.1:
            cer_dist["5-10%"] += 1
        elif c < 0.2:
            cer_dist["10-20%"] += 1
        else:
            cer_dist[">20%"] += 1
    print(f"  CER分布:      {dict(cer_dist)}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    report_path = os.path.join(OUTPUT_DIR, "eval_asr_report.json")
    report = {
        "summary": {
            "total": n,
            "avg_cer": round(avg_cer, 4),
            "avg_cer_corrected": round(avg_cer_corrected, 4),
            "rag_recall_at_1": round(rag_recall, 4),
            "rag_hits": rag_hits,
            "rag_total": rag_total,
            "cer_distribution": dict(cer_dist),
        },
        "corrections_count": len(corrections),
        "details": results,
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n报告已保存: {report_path}")

    if rag_service:
        from db.milvus_client import MilvusQA
        try:
            MilvusQA().close()
        except Exception:
            pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ASR端到端测试")
    parser.add_argument("--skip-tts", action="store_true", help="跳过音频合成")
    parser.add_argument("--force-tts", action="store_true", help="强制重新合成音频")
    parser.add_argument("--rag-only", action="store_true", help="只测RAG（用原始文本，不经过ASR）")
    parser.add_argument("--asr-only", action="store_true", help="只测ASR（不测RAG检索）")
    args = parser.parse_args()
    run_asr_test(args)
