"""
模型下载脚本 — 从ModelScope下载Embedding/Reranker/ASR模型
运行: python scripts/setup/download_models.py [--models embed,rerank,asr] [--dir ./models]
"""

import argparse
import os
import sys

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, PROJECT_ROOT)


def download_embed(save_dir):
    from modelscope import snapshot_download
    print("\n[1/3] 下载 Embedding 模型 bge-large-zh-v1.5 (~1.3GB)...")
    path = snapshot_download(
        "BAAI/bge-large-zh-v1.5",
        cache_dir=os.path.join(save_dir, "hub"),
    )
    print(f"  ✓ Embedding 模型已下载到: {path}")
    return path


def download_rerank(save_dir):
    from modelscope import snapshot_download
    print("\n[2/3] 下载 Reranker 模型 bge-reranker-large (~2.2GB)...")
    path = snapshot_download(
        "BAAI/bge-reranker-large",
        cache_dir=os.path.join(save_dir, "hub"),
    )
    print(f"  ✓ Reranker 模型已下载到: {path}")
    return path


def download_asr(save_dir):
    from modelscope import snapshot_download
    print("\n[3/3] 下载 ASR 模型 Fun-ASR-Nano-2512 (~2.1GB)...")
    path = snapshot_download(
        "FunAudioLLM/Fun-ASR-Nano-2512",
        cache_dir=os.path.join(save_dir, "hub"),
    )
    print(f"  ✓ ASR 模型已下载到: {path}")
    return path


MODELS = {
    "embed": ("bge-large-zh-v1.5", download_embed),
    "rerank": ("bge-reranker-large", download_rerank),
    "asr": ("Fun-ASR-Nano-2512", download_asr),
}


def check_exists(save_dir, model_id):
    model_dir_name = model_id.replace("/", os.sep)
    candidate = os.path.join(save_dir, model_dir_name)
    if os.path.isdir(candidate):
        return candidate
    dot_name = model_id.replace("/", os.sep).replace(".", "___")
    candidate2 = os.path.join(save_dir, dot_name)
    if os.path.isdir(candidate2):
        return candidate2
    hub_dir = os.path.join(save_dir, "hub", "models", model_dir_name)
    if os.path.isdir(hub_dir):
        return hub_dir
    hub_dot = os.path.join(save_dir, "hub", "models", dot_name)
    if os.path.isdir(hub_dot):
        return hub_dot
    return None


def main():
    parser = argparse.ArgumentParser(description="下载ETC-QA所需模型")
    parser.add_argument(
        "--models",
        default="embed,rerank,asr",
        help="要下载的模型，逗号分隔: embed,rerank,asr (默认全部)"
    )
    parser.add_argument(
        "--dir",
        default=os.path.join(PROJECT_ROOT, "models"),
        help="模型保存目录 (默认: ./models)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制重新下载，即使模型已存在"
    )
    args = parser.parse_args()

    save_dir = os.path.abspath(args.dir)
    os.makedirs(save_dir, exist_ok=True)

    requested = [m.strip() for m in args.models.split(",")]
    for m in requested:
        if m not in MODELS:
            print(f"❌ 未知模型: {m}，可选: {list(MODELS.keys())}")
            sys.exit(1)

    print(f"模型保存目录: {save_dir}")
    print(f"将下载: {', '.join(requested)}")

    total_size_map = {"embed": "~1.3GB", "rerank": "~2.2GB", "asr": "~2.1GB"}
    total = sum(1 for _ in requested)
    est = " + ".join(total_size_map[m] for m in requested)
    print(f"预计下载量: {est}")

    results = {}
    for m in requested:
        model_id, download_fn = MODELS[m]
        existing = check_exists(save_dir, model_id)
        if existing and not args.force:
            print(f"\n[{m}] 模型已存在: {existing} (跳过，如需重新下载加 --force)")
            results[m] = existing
            continue
        try:
            path = download_fn(save_dir)
            results[m] = path
        except Exception as e:
            print(f"  ❌ 下载失败: {e}")
            print(f"  提示: 确保已安装 modelscope: pip install modelscope")
            results[m] = None

    print("\n" + "=" * 50)
    print("下载结果:")
    for m, path in results.items():
        status = f"✓ {path}" if path else "❌ 失败"
        print(f"  {m}: {status}")

    if not all(results.values()):
        print("\n部分模型下载失败，可单独重试:")
        failed = [m for m, p in results.items() if not p]
        print(f"  python scripts/setup/download_models.py --models {','.join(failed)}")
        sys.exit(1)

    print(f"\n全部模型就绪！目录: {save_dir}")
    print("Docker启动时会自动挂载此目录。")


if __name__ == "__main__":
    main()