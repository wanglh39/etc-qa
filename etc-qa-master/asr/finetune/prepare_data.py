import argparse
import json
import os


def prepare_data(audio_dir: str, label_file: str, output_dir: str):
    if not os.path.exists(audio_dir):
        raise FileNotFoundError(f"音频目录不存在: {audio_dir}")
    if not os.path.exists(label_file):
        raise FileNotFoundError(f"标注文件不存在: {label_file}")

    os.makedirs(output_dir, exist_ok=True)

    with open(label_file, encoding="utf-8") as f:
        labels = json.load(f)

    samples = []
    for item in labels:
        audio_path = os.path.join(audio_dir, item["audio"])
        if os.path.exists(audio_path):
            samples.append({
                "audio": audio_path,
                "text": item["text"],
            })

    output_file = os.path.join(output_dir, "train_data.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(samples, f, ensure_ascii=False, indent=2)

    print(f"准备训练数据: {len(samples)}条 → {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ASR微调数据预处理")
    parser.add_argument("--audio-dir", required=True, help="音频文件目录")
    parser.add_argument("--label-file", required=True, help="标注JSON文件")
    parser.add_argument("--output-dir", default="data/asr_finetune", help="输出目录")
    args = parser.parse_args()
    prepare_data(args.audio_dir, args.label_file, args.output_dir)
