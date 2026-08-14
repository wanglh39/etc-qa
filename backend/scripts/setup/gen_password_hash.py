"""生成登录密码哈希，用于更新 .env 中的 ETC_QA_*_PASSWORD。

用法（在 backend 目录下运行）:
    python scripts/setup/gen_password_hash.py                  # 交互式输入
    python scripts/setup/gen_password_hash.py --password xxx    # 直接传入
    python scripts/setup/gen_password_hash.py admin_pw svc_pw   # 批量，每个生成一行
"""

import argparse
import getpass
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from utils.password import hash_password


def main():
    parser = argparse.ArgumentParser(description="生成密码哈希")
    parser.add_argument("--password", "-p", help="要哈希的密码")
    parser.add_argument("passwords", nargs="*", help="多个密码（每个生成一行）")
    args = parser.parse_args()

    if args.password:
        values = [args.password]
    elif args.passwords:
        values = args.passwords
    else:
        pw = getpass.getpass("请输入密码: ")
        if not pw:
            print("密码不能为空")
            sys.exit(1)
        values = [pw]

    for v in values:
        print(hash_password(v))


if __name__ == "__main__":
    main()
