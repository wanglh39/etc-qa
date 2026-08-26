"""
从QA数据中挑10条典型ETC客服问题，用edge-tts合成演示音频。
用法：
  1. pip install edge-tts
  2. python scripts/generate_asr_samples.py
输出：data/asr_samples/ 目录下10个wav文件 + 1个metadata.json
"""

import asyncio
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QA_CSV = os.path.join(ROOT, "data", "processed", "qa_filled.csv")
OUTPUT_DIR = os.path.join(ROOT, "data", "asr_samples")

SAMPLE_QUESTIONS = [
    "ETC扣费异常怎么处理",
    "ETC退款需要多长时间",
    "ETC黑名单怎么解除",
    "ETC设备没电了怎么办",
    "ETC注销流程是什么",
    "如何办理ETC新办",
    "ETC蓝牙连接不上怎么解决",
    "ETC发票怎么开具",
    "ETC充值失败怎么办",
    "ETC抬杆失败如何处理",
]

VOICE = "zh-CN-XiaoxiaoNeural"


async def synthesize(text: str, output_path: str):
    import edge_tts

    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(output_path)


async def main():
    try:
        import edge_tts
    except ImportError:
        print("请先安装: pip install edge-tts")
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    metadata = []
    for i, question in enumerate(SAMPLE_QUESTIONS, 1):
        filename = f"sample_{i:02d}.wav"
        filepath = os.path.join(OUTPUT_DIR, filename)
        print(f"[{i}/10] 合成: {question} -> {filename}")
        mp3_path = filepath.replace(".wav", ".mp3")
        await synthesize(question, mp3_path)

        try:
            from pydub import AudioSegment

            audio = AudioSegment.from_mp3(mp3_path)
            audio.export(filepath, format="wav")
            os.remove(mp3_path)
        except ImportError:
            if os.path.exists(mp3_path):
                os.rename(mp3_path, filepath)

        metadata.append(
            {
                "filename": filename,
                "text": question,
                "sample_id": i,
            }
        )

    meta_path = os.path.join(OUTPUT_DIR, "metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"\n完成！共生成 {len(metadata)} 个音频文件到 {OUTPUT_DIR}")
    print(f"元数据: {meta_path}")
    print("\n演示命令:")
    print(f'  curl -X POST http://localhost:8000/api/v1/asr -F "file=@{OUTPUT_DIR}/sample_01.wav"')


if __name__ == "__main__":
    asyncio.run(main())
