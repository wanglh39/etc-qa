"""轮换内置账号密码。

用于已部署的服务器：init_db.py 用 INSERT IGNORE 只会在账号不存在时写入初始密码，
不会覆盖存量密码。本脚本从环境变量读取新密码并 UPDATE users 表。

用法（在 backend 目录下运行）:
    python scripts/data/rotate_seed_passwords.py [env]
      env: dev / test / prod，默认 prod

环境变量（支持明文，自动哈希；或 pbkdf2_sha256 哈希原样写入）:
    ETC_QA_SUPERADMIN_PASSWORD / ETC_QA_ADMIN_PASSWORD / ETC_QA_OPS_PASSWORD
    ETC_QA_SERVICE_PASSWORD / ETC_QA_DEPT_PASSWORD
未设置的账号会被跳过。
"""

import os
import sys

import pymysql

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

env = sys.argv[1] if len(sys.argv) > 1 else "prod"
os.environ["ETC_QA_ENV"] = env

from utils.config import load_config
from utils.password import hash_password

cfg = load_config()

MYSQL_HOST = cfg["mysql"]["host"]
MYSQL_PORT = cfg["mysql"]["port"]
MYSQL_USER = cfg["mysql"]["user"]
MYSQL_PASSWORD = cfg["mysql"]["password"]
MYSQL_DB = cfg["mysql"]["database"]

ACCOUNTS = [
    ("superadmin", "ETC_QA_SUPERADMIN_PASSWORD"),
    ("admin", "ETC_QA_ADMIN_PASSWORD"),
    ("ops", "ETC_QA_OPS_PASSWORD"),
    ("service", "ETC_QA_SERVICE_PASSWORD"),
    ("dept", "ETC_QA_DEPT_PASSWORD"),
]


def _resolve(raw: str) -> str:
    raw = raw.strip()
    return raw if raw.startswith("pbkdf2_sha256$") else hash_password(raw)


def main():
    conn = pymysql.connect(
        host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER, password=MYSQL_PASSWORD, database=MYSQL_DB, charset="utf8mb4"
    )
    cursor = conn.cursor()

    updated, skipped = [], []
    for username, env_var in ACCOUNTS:
        raw = os.environ.get(env_var, "").strip()
        if not raw:
            skipped.append(username)
            print(f"[跳过] 账号 {username}：环境变量 {env_var} 未设置")
            continue
        new_hash = _resolve(raw)
        cursor.execute("UPDATE users SET password_hash = %s WHERE username = %s", (new_hash, username))
        if cursor.rowcount == 0:
            print(f"[警告] 账号 {username} 在 users 表中不存在，未更新")
            skipped.append(username)
        else:
            updated.append(username)
            print(f"[已更新] 账号 {username} 密码已轮换")

    conn.commit()
    cursor.close()
    conn.close()

    print(f"\n完成：更新 {len(updated)} 个账号，跳过 {len(skipped)} 个")
    if skipped:
        print(f"跳过账号: {', '.join(skipped)}")


if __name__ == "__main__":
    main()
