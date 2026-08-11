import argparse
import os


def train(
    base_model: str = "FunAudioLLM/Fun-ASR-Nano-2512",
    train_data: str = "data/asr_finetune/train_data.json",
    output_dir: str = "models/asr/finetuned",
    lora_rank: int = 8,
    lora_alpha: int = 16,
    epochs: int = 3,
    learning_rate: float = 1e-4,
    batch_size: int = 4,
):
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 60)
    print("FunASR LoRA微调训练")
    print("=" * 60)
    print(f"基座模型: {base_model}")
    print(f"训练数据: {train_data}")
    print(f"输出目录: {output_dir}")
    print(f"LoRA rank: {lora_rank}, alpha: {lora_alpha}")
    print(f"epochs: {epochs}, lr: {learning_rate}, batch_size: {batch_size}")
    print()
    print("注意: 需要GPU环境 + funasr微调依赖")
    print("运行前请确认:")
    print("  1. CUDA可用")
    print("  2. 训练数据已通过prepare_data.py生成")
    print("  3. funasr已安装微调依赖: pip install funasr[finetune]")
    print()

    try:
        from funasr import AutoModel
        print("开始训练...")
        print("TODO: 实现具体微调逻辑")
        print("参考: https://github.com/modelscope/FunASR/blob/main/examples/finetune")
    except ImportError:
        print("ERROR: funasr未安装")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ASR LoRA微调训练")
    parser.add_argument("--base-model", default="FunAudioLLM/Fun-ASR-Nano-2512")
    parser.add_argument("--train-data", default="data/asr_finetune/train_data.json")
    parser.add_argument("--output-dir", default="models/asr/finetuned")
    parser.add_argument("--lora-rank", type=int, default=8)
    parser.add_argument("--lora-alpha", type=int, default=16)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--batch-size", type=int, default=4)
    args = parser.parse_args()
    train(
        base_model=args.base_model,
        train_data=args.train_data,
        output_dir=args.output_dir,
        lora_rank=args.lora_rank,
        lora_alpha=args.lora_alpha,
        epochs=args.epochs,
        learning_rate=args.lr,
        batch_size=args.batch_size,
    )
