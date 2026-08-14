"""
合成双声道多段对话测试数据：
  从 test_questions.json 读取客户分段+客服引导文本
  → 用edge-tts分别合成 → 拼成stereo WAV（客户左声道+客服右声道）

用法：
  1. pip install edge-tts soundfile numpy
  2. python scripts/eval/synthesize_data.py              # 合成所有（已存在则跳过）
  3. python scripts/eval/synthesize_data.py --force       # 强制重新合成

以后可从真实业务导出音频替换这些合成数据，评测脚本不需要改。
"""
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
    parser = argparse.ArgumentParser(description="合成双声道多段对话测试数据")
    parser.add_argument("--force", action="store_true", help="强制重新合成（覆盖已有）")
    args = parser.parse_args()

    try:
        import edge_tts
    except ImportError:
        print("请先安装: pip install edge-tts")
        sys.exit(1)

    if not os.path.exists(TEST_QUESTIONS_PATH):
        print(f"测试数据不存在: {TEST_QUESTIONS_PATH}")
        sys.exit(1)

    with open(TEST_QUESTIONS_PATH, encoding="utf-8") as f:
        test_questions = json.load(f)

    os.makedirs(SAMPLES_DIR, exist_ok=True)
    print(f"合成双声道多段对话音频: {len(test_questions)}条\n")

    for i, item in enumerate(test_questions, 1):
        stereo_path = os.path.join(SAMPLES_DIR, f"sample_{i:02d}.wav")
        if os.path.exists(stereo_path) and not args.force:
            print(f"  [{i}/{len(test_questions)}] 已存在，跳过: {stereo_path}")
            continue

        customer_segs = item["customer_segments"]
        agent_segs = item["agent_segments"]
        print(f"  [{i}/{len(test_questions)}] 合成:")
        print(f"       客户({len(customer_segs)}段): {customer_segs}")
        print(f"       客服({len(agent_segs)}段): {agent_segs}")
        synthesize_stereo_multi_segment(customer_segs, agent_segs, stereo_path)

    metadata = [
        {"filename": f"sample_{i:02d}.wav", **item}
        for i, item in enumerate(test_questions, 1)
    ]
    with open(os.path.join(SAMPLES_DIR, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"\n完成! 音频保存在: {SAMPLES_DIR}")
    print(f"元数据保存在: {os.path.join(SAMPLES_DIR, 'metadata.json')}")
    print(f"现在可以运行: python scripts/eval/eval_asr.py")


if __name__ == "__main__":
    main()