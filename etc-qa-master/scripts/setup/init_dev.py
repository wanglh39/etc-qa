"""
开发环境初始化脚本
1. 检查.env文件
2. 检查模型是否存在
3. 启动MySQL Docker容器
4. 初始化数据库+导入数据
5. 初始化Milvus

运行: python scripts/setup/init_dev.py
"""

import os
import subprocess
import sys

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")


def check_env_file():
    env_path = os.path.join(PROJECT_ROOT, ".env")
    template_path = os.path.join(PROJECT_ROOT, ".env.template")

    if not os.path.exists(env_path):
        if os.path.exists(template_path):
            print("📋 未找到 .env 文件，从模板复制...")
            import shutil
            shutil.copy(template_path, env_path)
            print(f"  ✓ 已创建 .env，请编辑填入你的 DEEPSEEK_API_KEY")
            print(f"  路径: {env_path}")
            return False
        else:
            print("❌ 未找到 .env 和 .env.template，请手动创建 .env")
            return False

    with open(env_path, encoding="utf-8") as f:
        content = f.read()

    if "sk-your-deepseek-api-key-here" in content:
        print("⚠️  .env 中 DEEPSEEK_API_KEY 还是模板值，请替换为真实Key")
        print(f"  路径: {env_path}")
        return False

    print("✓ .env 文件检查通过")
    return True


def check_models():
    models_dir = os.path.join(PROJECT_ROOT, "models")
    required = {
        "embed": "BAAI/bge-large-zh-v1.5",
        "rerank": "BAAI/bge-reranker-large",
        "asr": "FunAudioLLM/Fun-ASR-Nano-2512",
    }

    missing = []
    for name, model_id in required.items():
        found = False
        if os.path.isdir(models_dir):
            for root, dirs, files in os.walk(models_dir):
                for d in dirs:
                    normalized = d.replace("___", ".")
                    if model_id.split("/")[-1].replace(".", "___") in d or model_id.split("/")[-1] in d:
                        found = True
                        break
                if found:
                    break

        if found:
            print(f"  ✓ {name}: {model_id}")
        else:
            print(f"  ✗ {name}: {model_id} (未找到)")
            missing.append(name)

    if missing:
        print(f"\n⚠️  缺少模型: {', '.join(missing)}")
        print("请先运行模型下载脚本:")
        print(f"  python scripts/setup/download_models.py --models {','.join(missing)}")
        return False

    print("✓ 所有模型就绪")
    return True


def check_docker():
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            print(f"✓ Docker: {result.stdout.strip()}")
            return True
    except Exception:
        pass

    print("❌ 未检测到Docker，请先安装Docker Desktop")
    print("  下载: https://www.docker.com/products/docker-desktop/")
    return False


def start_mysql():
    print("\n=== 启动MySQL容器 ===")
    result = subprocess.run(
        ["docker", "compose", "-f", "docker-compose.dev.yml", "up", "-d", "mysql"],
        capture_output=True, text=True,
        cwd=PROJECT_ROOT
    )
    if result.returncode != 0:
        print(f"❌ MySQL容器启动失败:\n{result.stderr}")
        return False

    print("  等待MySQL就绪...")
    import time
    for i in range(30):
        result = subprocess.run(
            ["docker", "compose", "-f", "docker-compose.dev.yml", "exec", "mysql",
             "mysqladmin", "ping", "-h", "localhost", "-u", "root", "-p123456"],
            capture_output=True, text=True,
            cwd=PROJECT_ROOT
        )
        if result.returncode == 0:
            print("  ✓ MySQL已就绪")
            return True
        time.sleep(2)

    print("  ❌ MySQL启动超时(60秒)")
    return False


def init_database():
    print("\n=== 初始化数据库 ===")
    env = os.environ.copy()
    env["ETC_QA_ENV"] = "dev"

    result = subprocess.run(
        [sys.executable, "scripts/data/init_db.py", "dev"],
        capture_output=True, text=True,
        cwd=PROJECT_ROOT,
        env=env
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"❌ 数据库初始化失败:\n{result.stderr}")
        return False

    print("✓ 数据库初始化完成")
    return True


def main():
    print("=" * 50)
    print("ETC客服QA — 开发环境初始化")
    print("=" * 50)

    checks = [
        ("环境变量", check_env_file),
        ("模型文件", check_models),
        ("Docker", check_docker),
    ]

    failed = []
    for name, check_fn in checks:
        print(f"\n--- 检查: {name} ---")
        if not check_fn():
            failed.append(name)

    if failed:
        print(f"\n❌ 以下检查未通过: {', '.join(failed)}")
        print("请修复后重新运行本脚本")
        sys.exit(1)

    if not start_mysql():
        sys.exit(1)

    if not init_database():
        sys.exit(1)

    print("\n" + "=" * 50)
    print("✓ 开发环境初始化完成！")
    print()
    print("启动方式:")
    print("  Docker: docker compose -f docker-compose.dev.yml up etc-qa")
    print("  本地:   python main.py")
    print()
    print("API文档: http://localhost:8000/docs")


if __name__ == "__main__":
    main()