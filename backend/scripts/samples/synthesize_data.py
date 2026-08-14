"""
鍚堟垚鍙屽０閬撳娈靛璇濇祴璇曟暟鎹細
  浠?test_questions.json 璇诲彇瀹㈡埛鍒嗘+瀹㈡湇寮曞鏂囨湰
  鈫?鐢╡dge-tts鍒嗗埆鍚堟垚 鈫?鎷兼垚stereo WAV锛堝鎴峰乏澹伴亾+瀹㈡湇鍙冲０閬擄級

鐢ㄦ硶锛?  1. pip install edge-tts soundfile numpy
  2. python scripts/eval/synthesize_data.py              # 鍚堟垚鎵€鏈夛紙宸插瓨鍦ㄥ垯璺宠繃锛?  3. python scripts/eval/synthesize_data.py --force       # 寮哄埗閲嶆柊鍚堟垚

浠ュ悗鍙粠鐪熷疄涓氬姟瀵煎嚭闊抽鏇挎崲杩欎簺鍚堟垚鏁版嵁锛岃瘎娴嬭剼鏈笉闇€瑕佹敼銆?"""
import argparse
import asyncio
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

SAMPLES_DIR = os.path.join(ROOT, "data", "asr_samples")
TEST_QUESTIONS_PATH = os.path.join(SAMPLES_DIR, "test_questions.json")

VOICE_CUSTOMER = "zh-CN-XiaoxiaoNeural"
VOICE_AGENT = "zh-CN-YunyangNeural"
SILENCE_GAP_SEC = 0.5


async def _synthesize_mono(text: str, voice: str):
    import edge_tts
    import soundfile as sf
    communicate = edge_tts.Communicate(text, voice)
    mp3_path = os.path.join(SAMPLES_DIR, f"_tmp_{hash(text) & 0xFFFFFFFF}.mp3")
    await communicate.save(mp3_path)
    data, sr = sf.read(mp3_path)
    os.remove(mp3_path)
    return data, sr


def synthesize_stereo_multi_segment(customer_segments: list, agent_segments: list, output_path: str):
    import numpy as np
    import soundfile as sf

    sr = None
    customer_parts = []
    for seg_text in customer_segments:
        data, s = asyncio.run(_synthesize_mono(seg_text, VOICE_CUSTOMER))
        if sr is None:
            sr = s
        customer_parts.append(data)
        customer_parts.append(np.zeros(int(sr * SILENCE_GAP_SEC), dtype=np.float32))

    agent_parts = []
    for seg_text in agent_segments:
        data, s = asyncio.run(_synthesize_mono(seg_text, VOICE_AGENT))
        agent_parts.append(data)
        agent_parts.append(np.zeros(int(sr * SILENCE_GAP_SEC), dtype=np.float32))

    customer_full = np.concatenate(customer_parts) if customer_parts else np.zeros(0, dtype=np.float32)
    agent_full = np.concatenate(agent_parts) if agent_parts else np.zeros(0, dtype=np.float32)

    max_len = max(len(customer_full), len(agent_full))
    customer_padded = np.zeros(max_len, dtype=np.float32)
    agent_padded = np.zeros(max_len, dtype=np.float32)
    customer_padded[:len(customer_full)] = customer_full
    agent_padded[:len(agent_full)] = agent_full

    stereo = np.column_stack([customer_padded, agent_padded])
    sf.write(output_path, stereo, sr, subtype="PCM_16")
    return sr


def main():
    parser = argparse.ArgumentParser(description="鍚堟垚鍙屽０閬撳娈靛璇濇祴璇曟暟鎹?)
    parser.add_argument("--force", action="store_true", help="寮哄埗閲嶆柊鍚堟垚锛堣鐩栧凡鏈夛級")
    args = parser.parse_args()

    try:
        import edge_tts
    except ImportError:
        print("璇峰厛瀹夎: pip install edge-tts")
        sys.exit(1)

    if not os.path.exists(TEST_QUESTIONS_PATH):
        print(f"娴嬭瘯鏁版嵁涓嶅瓨鍦? {TEST_QUESTIONS_PATH}")
        sys.exit(1)

    with open(TEST_QUESTIONS_PATH, encoding="utf-8") as f:
        test_questions = json.load(f)

    os.makedirs(SAMPLES_DIR, exist_ok=True)
    print(f"鍚堟垚鍙屽０閬撳娈靛璇濋煶棰? {len(test_questions)}鏉n")

    for i, item in enumerate(test_questions, 1):
        stereo_path = os.path.join(SAMPLES_DIR, f"sample_{i:02d}.wav")
        if os.path.exists(stereo_path) and not args.force:
            print(f"  [{i}/{len(test_questions)}] 宸插瓨鍦紝璺宠繃: {stereo_path}")
            continue

        customer_segs = item["customer_segments"]
        agent_segs = item["agent_segments"]
        print(f"  [{i}/{len(test_questions)}] 鍚堟垚:")
        print(f"       瀹㈡埛({len(customer_segs)}娈?: {customer_segs}")
        print(f"       瀹㈡湇({len(agent_segs)}娈?: {agent_segs}")
        synthesize_stereo_multi_segment(customer_segs, agent_segs, stereo_path)

    metadata = [
        {"filename": f"sample_{i:02d}.wav", **item}
        for i, item in enumerate(test_questions, 1)
    ]
    with open(os.path.join(SAMPLES_DIR, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"\n瀹屾垚! 闊抽淇濆瓨鍦? {SAMPLES_DIR}")
    print(f"鍏冩暟鎹繚瀛樺湪: {os.path.join(SAMPLES_DIR, 'metadata.json')}")
    print(f"鐜板湪鍙互杩愯: python scripts/eval/eval_asr.py")


if __name__ == "__main__":
    main()