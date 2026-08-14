"""
瀹㈡湇杈呭姪妫€绱㈡祴璇勶紙鍙屽０閬撳娈靛璇濈増锛夛細
  璇诲彇宸叉湁鍙屽０閬撻煶棰?鈫?澹伴亾鍒嗙 鈫?涓ゆ潯閾捐矾瀵规瘮锛?    1. 绂荤嚎鍩虹嚎锛歏AD鍒囧垎鈫掓瘡娈电绾緼SR鈫掔疮绉啋CER vs 鎵€鏈夋鎷兼帴
    2. 浼祦寮忎笟鍔￠摼璺細鏁翠釜瀹㈡埛澹伴亾鈫扨seudoStreamingBackend(VAD+Fun-ASR-Nano)鈫掕繃婊も啋绱Н鈫扖ER vs final_question
  RAG Recall@1锛氱敤浼祦寮忚繃婊ゅ悗鐨勬枃鏈绱?
鍓嶇疆鏉′欢锛氬厛杩愯 python scripts/samples/synthesize_data.py 鍚堟垚娴嬭瘯闊抽
  锛堟垨浠庣湡瀹炰笟鍔″鍑洪煶棰戞斁鍒?data/asr_samples/锛?
鐢ㄦ硶锛?  1. python scripts/eval/eval_asr.py              # 瀹屾暣娴嬭瘯锛圓SR+RAG锛?  2. python scripts/eval/eval_asr.py --rag-only   # 鍙祴RAG锛堢敤final_question鏂囨湰锛屼笉缁忚繃ASR锛?  3. python scripts/eval/eval_asr.py --asr-only   # 鍙祴ASR锛堜笉娴婻AG妫€绱級
"""
import argparse
import json
import os
import sys
import tempfile
from collections import defaultdict
from difflib import SequenceMatcher

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
os.environ['ETC_QA_ENV'] = os.environ.get('ETC_QA_ENV', 'dev')

OUTPUT_DIR = os.path.join(ROOT, "output")
SAMPLES_DIR = os.path.join(ROOT, "data", "asr_samples")
TEST_QUESTIONS_PATH = os.path.join(SAMPLES_DIR, "test_questions.json")


def calculate_cer(reference: str, hypothesis: str) -> float:
    import re
    strip_re = re.compile(r'[锛屻€傦紵锛併€侊紱锛?"'r'锛堬級\s]')
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


def separate_channels(stereo_path: str, customer_side: str = "left"):
    import soundfile as sf

    data, sr = sf.read(stereo_path)
    if data.ndim == 1:
        return stereo_path, stereo_path, sr

    left = data[:, 0]
    right = data[:, 1]

    base = stereo_path.rsplit(".", 1)[0]
    customer_path = f"{base}_customer.wav"
    agent_path = f"{base}_agent.wav"

    if customer_side == "left":
        sf.write(customer_path, left, sr, subtype="PCM_16")
        sf.write(agent_path, right, sr, subtype="PCM_16")
    else:
        sf.write(customer_path, right, sr, subtype="PCM_16")
        sf.write(agent_path, left, sr, subtype="PCM_16")
    return customer_path, agent_path, sr


def vad_split(wav_path: str, threshold_db: int = 30, min_silence_ms: int = 200):
    import soundfile as sf
    import numpy as np

    data, sr = sf.read(wav_path)
    if data.ndim > 1:
        data = data[:, 0]

    frame_ms = 30
    hop_ms = 10
    frame_len = int(sr * frame_ms / 1000)
    hop_len = int(sr * hop_ms / 1000)
    min_silence_frames = int(min_silence_ms / hop_ms)

    if len(data) < frame_len:
        return [(0, len(data))], sr, data

    ref = np.max(np.abs(data)) + 1e-10
    threshold = ref * (10 ** (-threshold_db / 20))

    is_speech = []
    for i in range(0, len(data) - frame_len + 1, hop_len):
        frame = data[i:i + frame_len]
        rms = np.sqrt(np.mean(frame ** 2))
        is_speech.append(rms > threshold)

    segments = []
    in_speech = False
    start = 0
    silence_count = 0
    for i, speech in enumerate(is_speech):
        pos = i * hop_len
        if speech:
            if not in_speech:
                start = pos
                in_speech = True
            silence_count = 0
        else:
            if in_speech:
                silence_count += 1
                if silence_count >= min_silence_frames:
                    segments.append((start, pos))
                    in_speech = False
                    silence_count = 0
    if in_speech:
        segments.append((start, len(data)))

    return segments, sr, data


def save_segment(data, sr, start, end, output_path: str):
    import soundfile as sf
    segment = data[start:end]
    sf.write(output_path, segment, sr, subtype="PCM_16")


def run_pseudo_streaming_pipeline(streaming_service, wav_path: str, chunk_samples: int = 4800):
    import soundfile as sf
    from asr.streaming import StreamingCallback
    from asr.ws_helpers import _is_greeting, _is_correction, _has_pronoun
    from asr.ws_state import QueryAccumulator, ContextWindow, QueryCache
    from asr.service import _apply_corrections, _load_corrections
    from utils.config import get_config

    cfg = get_config().get("asr", {}).get("streaming", {})
    filter_greeting = cfg.get("filter_greeting", True)
    min_query_length = cfg.get("min_query_length", 4)
    correction_enabled = cfg.get("correction_enabled", True)
    coreference_enabled = cfg.get("coreference_enabled", True)
    dedup_enabled = cfg.get("dedup_enabled", True)
    accumulate_mode = cfg.get("accumulate_mode", "sentence")
    max_sentences = cfg.get("accumulate_max_sentences", 3)
    text_corrections = _load_corrections()

    accumulator = QueryAccumulator(max_sentences=max_sentences)
    context_window = ContextWindow(cfg.get("context_window_size", 3))
    query_cache = QueryCache(
        min_interval=cfg.get("dedup_min_interval", 5),
        similarity_threshold=cfg.get("dedup_similarity", 0.8),
    )

    filtered_msgs = []
    valid_texts = []

    class _FilterCb(StreamingCallback):
        def on_final(self, text, is_end=False):
            if not text:
                return
            if text_corrections:
                text = _apply_corrections(text, text_corrections)
            if filter_greeting and _is_greeting(text):
                filtered_msgs.append({"text": text, "reason": "greeting"})
                return
            if len(text.strip()) < min_query_length:
                filtered_msgs.append({"text": text, "reason": "too_short"})
                return
            if correction_enabled and _is_correction(text):
                accumulator.pop_last()
                filtered_msgs.append({"text": text, "reason": "correction"})
                return
            query_text = text
            if coreference_enabled and _has_pronoun(text):
                query_text = context_window.resolve_pronoun(text)
            if dedup_enabled and query_cache.should_skip(query_text):
                filtered_msgs.append({"text": text, "reason": "duplicate"})
                return
            if accumulate_mode == "sentence":
                valid_texts.append(query_text)
            else:
                result = accumulator.add(query_text)
                if result:
                    valid_texts.extend(result)
            context_window.add(query_text)

        def on_error(self, error):
            print(f"       浼祦寮忛敊璇? {error}")

    data, sr = sf.read(wav_path, dtype="int16")
    if data.ndim > 1:
        data = data[:, 0]
    pcm_bytes = data.tobytes()
    chunk_bytes = chunk_samples * 2

    streaming_service.start_stream(_FilterCb())
    for i in range(0, len(pcm_bytes), chunk_bytes):
        streaming_service.send_audio(pcm_bytes[i:i + chunk_bytes])
    streaming_service.stop_stream()

    if accumulate_mode != "sentence":
        remaining = accumulator.flush()
        if remaining:
            valid_texts.extend(remaining)

    return "".join(valid_texts), filtered_msgs


def find_expected_id(expected_question: str, question_to_ids: dict) -> int:
    e_clean = expected_question.replace("\n", "").replace(" ", "")
    for q, qid in question_to_ids.items():
        q_clean = q.replace("\n", "").replace(" ", "")
        if e_clean in q_clean or q_clean in e_clean:
            return qid
    best_ratio = 0.0
    best_id = None
    for q, qid in question_to_ids.items():
        q_clean = q.replace("\n", "").replace(" ", "")
        ratio = SequenceMatcher(None, e_clean, q_clean).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_id = qid
    if best_ratio >= 0.6:
        return best_id
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
    print(f"娴嬭瘯鏁版嵁涓嶅瓨鍦? {TEST_QUESTIONS_PATH}")
    sys.exit(1)


def run_asr_test(args):
    print("=" * 60)
    print("ASR绔埌绔祴璇曪紙鍙屽０閬撳娈靛璇濈増 - 浼祦寮忥級")
    print("=" * 60)

    test_questions = load_test_questions()
    print(f"鍔犺浇娴嬭瘯鏁版嵁: {len(test_questions)}鏉?(from {TEST_QUESTIONS_PATH})")

    first_wav = os.path.join(SAMPLES_DIR, "sample_01.wav")
    if not args.rag_only and not os.path.exists(first_wav):
        print(f"\n闊抽涓嶅瓨鍦? {first_wav}")
        print("璇峰厛鍚堟垚鏁版嵁: python scripts/samples/synthesize_data.py")
        print("鎴栦粠鐪熷疄涓氬姟瀵煎嚭闊抽鍒?data/asr_samples/")
        sys.exit(1)

    from asr.service import _apply_corrections, _load_corrections, get_asr_service
    asr_service = get_asr_service()
    corrections = _load_corrections()
    print(f"鍔犺浇绾犻敊琛? {len(corrections)}鏉?(DB浼樺厛鈫抍onfig/asr.yaml鍏滃簳)")

    if not asr_service._enabled and not args.rag_only:
        print("ASR鏈惎鐢紝璇峰湪config/asr.yaml涓缃產sr.enabled=true")
        sys.exit(1)

    from utils.config import get_config
    cfg = get_config()
    customer_side = cfg.get("asr", {}).get("streaming", {}).get("channel_customer_side", "left")
    print(f"澹伴亾閰嶇疆: 瀹㈡埛鍦▄customer_side}澹伴亾")

    streaming_service = None
    if not args.rag_only:
        from asr.streaming import get_streaming_service
        streaming_service = get_streaming_service()
        if streaming_service.enabled:
            print(f"浼祦寮廇SR: 宸插惎鐢?(mode={streaming_service.mode})")
        else:
            streaming_service = None
            print("浼祦寮廇SR: 鏈惎鐢紝浠呮祴绂荤嚎鍩虹嚎")

    rag_service = None
    if not args.asr_only:
        from app import create_service
        print("鍒濆鍖朢AG鏈嶅姟...")
        rag_service = create_service()

    from db.mysql_client import MySQLClient
    mysql = MySQLClient()
    question_to_ids, qa_dict = load_qa_index(mysql)

    results = []
    total_offline_cer = 0
    total_pseudo_cer = 0
    pseudo_count = 0
    total_agent_cer = 0
    rag_hits = 0
    rag_total = 0
    vad_match_count = 0
    vad_total = 0

    print("\n--- 澹伴亾鍒嗙 鈫?绂荤嚎鍩虹嚎 + 浼祦寮忎笟鍔￠摼璺?鈫?RAG妫€绱?---")
    for i, item in enumerate(test_questions, 1):
        customer_segs = item["customer_segments"]
        agent_segs = item["agent_segments"]
        final_question = item["final_question"]
        category = item.get("category_l1", "")
        keyword = item.get("keyword", "")
        stereo_path = os.path.join(SAMPLES_DIR, f"sample_{i:02d}.wav")

        print(f"\n  [{i:2d}] 瀹㈡埛鍒嗘: {customer_segs}")
        print(f"       鏈€缁堥棶棰? \"{final_question}\"")

        if args.rag_only:
            offline_accumulated = final_question
            agent_asr_text = "".join(agent_segs)
            pseudo_filtered_text = final_question
            filtered_msgs = []
            vad_segments_count = len(customer_segs)
        else:
            if not os.path.exists(stereo_path):
                print(f"       闊抽涓嶅瓨鍦? {stereo_path}锛岃烦杩?)
                continue

            customer_wav, agent_wav, sr = separate_channels(stereo_path, customer_side)

            vad_segments, vad_sr, vad_data = vad_split(customer_wav, threshold_db=30, min_silence_ms=200)
            vad_segments_count = len(vad_segments)
            expected_seg_count = len(customer_segs)
            vad_total += 1
            if vad_segments_count == expected_seg_count:
                vad_match_count += 1
            print(f"       VAD鍒囧垎: {vad_segments_count}娈?(鏈熸湜{expected_seg_count}娈? {'鉁? if vad_segments_count == expected_seg_count else '鉁?}")

            seg_texts = []
            tmp_dir = tempfile.mkdtemp(prefix="eval_asr_")
            for j, (start, end) in enumerate(vad_segments):
                seg_path = os.path.join(tmp_dir, f"seg_{j}.wav")
                save_segment(vad_data, vad_sr, start, end, seg_path)
                try:
                    resp = asr_service.transcribe(seg_path)
                    seg_texts.append(resp.text)
                    print(f"       娈礫{j+1}] 绂荤嚎ASR: \"{resp.text}\"")
                except Exception as e:
                    print(f"       娈礫{j+1}] 绂荤嚎ASR澶辫触: {e}")
                    seg_texts.append("")

            for f in os.listdir(tmp_dir):
                os.remove(os.path.join(tmp_dir, f))
            os.rmdir(tmp_dir)

            offline_accumulated = "".join(seg_texts)

            try:
                resp_a = asr_service.transcribe(agent_wav)
                agent_asr_text = resp_a.text
            except Exception as e:
                print(f"       瀹㈡湇澹伴亾ASR澶辫触: {e}")
                agent_asr_text = ""

            pseudo_filtered_text = None
            filtered_msgs = []
            if streaming_service:
                try:
                    pseudo_filtered_text, filtered_msgs = run_pseudo_streaming_pipeline(
                        streaming_service, customer_wav
                    )
                    if filtered_msgs:
                        print(f"       杩囨护鎺墈len(filtered_msgs)}娈? {filtered_msgs}")
                    print(f"       浼祦寮忕粨鏋? \"{pseudo_filtered_text}\"")
                except Exception as e:
                    print(f"       浼祦寮忓け璐? {e}")

        offline_corrected = _apply_corrections(offline_accumulated, corrections) if corrections else offline_accumulated
        import re as _re
        _punct_re = _re.compile(r'[锛屻€傦紵锛併€侊紱锛?"''锛堬級]$')
        offline_corrected = _punct_re.sub('', offline_corrected)

        customer_full_text = "".join(customer_segs)
        offline_cer = calculate_cer(customer_full_text, offline_accumulated)
        offline_cer_corrected = calculate_cer(customer_full_text, offline_corrected)
        agent_cer = calculate_cer("".join(agent_segs), agent_asr_text)
        total_offline_cer += offline_cer
        total_agent_cer += agent_cer

        pseudo_cer = None
        if pseudo_filtered_text is not None:
            pseudo_cer = calculate_cer(final_question, pseudo_filtered_text)
            total_pseudo_cer += pseudo_cer
            pseudo_count += 1

        if not args.rag_only:
            print(f"       绂荤嚎绱Н: \"{offline_accumulated}\"")
            print(f"       瀹㈡湇璇嗗埆:   \"{agent_asr_text}\"")

        rag_query_text = pseudo_filtered_text if pseudo_filtered_text else offline_corrected
        if "expected_qa_id" in item:
            expected_id = item["expected_qa_id"]
        else:
            expected_id = find_expected_id(final_question, question_to_ids)
        rag_hit = False
        rag_top1 = ""
        rag_top1_score = 0
        rag_candidates = []

        if rag_service and expected_id is not None:
            try:
                rag_result = rag_service.query(rag_query_text)
                if rag_result.candidates:
                    rag_candidates = rag_result.candidates[:3]
                    top_id = rag_result.candidates[0].qa_id
                    rag_top1 = rag_result.candidates[0].question
                    rag_top1_score = rag_result.candidates[0].score
                    rag_hit = (top_id == expected_id)
                    rag_total += 1
                    if rag_hit:
                        rag_hits += 1
            except Exception as e:
                print(f"       RAG妫€绱㈠け璐? {e}")

        offline_cer_mark = "OK" if offline_cer < 0.1 else ("WARN" if offline_cer < 0.2 else "FAIL")
        rag_mark = "HIT" if rag_hit else "MISS"

        if rag_candidates:
            print(f"       缁欏鏈嶇殑鍊欓€夋彁绀?")
            for j, c in enumerate(rag_candidates, 1):
                mark = "鈫?瀹㈡湇閫夋嫨" if j == 1 else ""
                print(f"         [{j}] 鍒嗘暟={c.score:.4f} \"{c.question}\" {mark}")
            print(f"         绛旀: \"{rag_candidates[0].answer[:60]}...\"")
        print(f"       绂荤嚎CER: {offline_cer:.1%}鈫抺offline_cer_corrected:.1%} [{offline_cer_mark}]  "
              f"瀹㈡湇CER: {agent_cer:.1%}  "
              f"RAG: [{rag_mark}]"
              + (f"  浼祦寮廋ER: {pseudo_cer:.1%}" if pseudo_cer is not None else ""))

        results.append({
            "index": i,
            "customer_segments": customer_segs,
            "agent_segments": agent_segs,
            "final_question": final_question,
            "offline_accumulated_text": offline_accumulated,
            "pseudo_filtered_text": pseudo_filtered_text,
            "filtered_msgs": filtered_msgs,
            "agent_asr_text": agent_asr_text,
            "offline_corrected": offline_corrected,
            "offline_cer": round(offline_cer, 4),
            "offline_cer_corrected": round(offline_cer_corrected, 4),
            "agent_cer": round(agent_cer, 4),
            "pseudo_cer": round(pseudo_cer, 4) if pseudo_cer is not None else None,
            "vad_segments_count": vad_segments_count,
            "expected_seg_count": len(customer_segs),
            "rag_hit": rag_hit,
            "rag_top1": rag_top1,
            "rag_top1_score": rag_top1_score,
            "category": category,
            "keyword": keyword,
        })

    n = len(results)
    avg_offline_cer = total_offline_cer / n if n else 0
    avg_agent_cer = total_agent_cer / n if n else 0
    avg_pseudo_cer = total_pseudo_cer / pseudo_count if pseudo_count else 0
    rag_recall = rag_hits / rag_total if rag_total else 0
    vad_match_rate = vad_match_count / vad_total if vad_total else 0

    print(f"\n{'='*60}")
    print("瀹㈡湇杈呭姪妫€绱㈡祴璇曠粨鏋滄眹鎬伙紙鍙屽０閬撳娈靛璇濈増 - 浼祦寮忥級")
    print(f"{'='*60}")
    print(f"  娴嬭瘯鍦烘櫙: 瀹㈡埛鍒嗘璇磋瘽 鈫?澹伴亾鍒嗙 鈫?浼祦寮?VAD+Fun-ASR-Nano) 鈫?杩囨护 鈫?RAG妫€绱?)
    print(f"  鏍锋湰鏁?          {n}")
    print(f"  VAD鍒囧垎鍖归厤鐜?   {vad_match_rate:.1%} ({vad_match_count}/{vad_total})")
    print(f"  绂荤嚎鍩虹嚎CER:     {avg_offline_cer:.1%}")
    if pseudo_count > 0:
        print(f"  浼祦寮廋ER:       {avg_pseudo_cer:.1%} ({pseudo_count}鏉? 瀵规瘮final_question)")
        print(f"  绂荤嚎vs浼祦寮忓樊寮? {avg_offline_cer - avg_pseudo_cer:+.1%}")
    print(f"  瀹㈡湇澹伴亾CER:     {avg_agent_cer:.1%}")
    print(f"  RAG Recall@1:    {rag_recall:.1%} ({rag_hits}/{rag_total})")
    print(f"  璇存槑: 浼祦寮廋ER瀵规瘮final_question(寮€鍦虹櫧宸茶繃婊?, 绂荤嚎CER瀵规瘮鎵€鏈夋鎷兼帴")

    cer_dist = defaultdict(int)
    for r in results:
        c = r.get("pseudo_cer") if r.get("pseudo_cer") is not None else r["offline_cer_corrected"]
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
    print(f"  CER鍒嗗竷:         {dict(cer_dist)}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    report_path = os.path.join(OUTPUT_DIR, "eval_asr_report.json")
    report = {
        "summary": {
            "total": n,
            "vad_match_rate": round(vad_match_rate, 4),
            "avg_offline_cer": round(avg_offline_cer, 4),
            "avg_pseudo_cer": round(avg_pseudo_cer, 4) if pseudo_count else None,
            "pseudo_count": pseudo_count,
            "avg_agent_cer": round(avg_agent_cer, 4),
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
    print(f"\n鎶ュ憡宸蹭繚瀛? {report_path}")

    if rag_service:
        from db.milvus_client import MilvusQA
        try:
            MilvusQA().close()
        except Exception:
            pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ASR绔埌绔祴璇曪紙鍙屽０閬撳娈靛璇濈増 - 浼祦寮忥級")
    parser.add_argument("--rag-only", action="store_true", help="鍙祴RAG锛堢敤final_question鏂囨湰锛屼笉缁忚繃ASR锛?)
    parser.add_argument("--asr-only", action="store_true", help="鍙祴ASR锛堜笉娴婻AG妫€绱級")
    args = parser.parse_args()
    run_asr_test(args)