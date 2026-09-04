import hashlib
import hmac
import secrets

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 260000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), ITERATIONS)
    return f"{ALGORITHM}${ITERATIONS}${salt}${dk.hex()}"


def _parse(stored: str):
    parts = stored.split("$")
    if len(parts) != 4 or parts[0] != ALGORITHM:
        return None
    try:
        return int(parts[1]), parts[2], parts[3]
    except ValueError:
        return None


def verify_password(password: str, stored: str) -> bool:
    parsed = _parse(stored)
    if parsed is None:
        # 兼容历史明文密码（迁移期），仍用恒定时间比较
        return hmac.compare_digest(password, stored)
    iterations, salt, expected = parsed
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return hmac.compare_digest(dk.hex(), expected)


def needs_rehash(stored: str) -> bool:
    return _parse(stored) is None


def check_password_policy():
    from utils.jwt_utils import USERS

    for username, meta in USERS.items():
        stored = meta.get("password", "") or ""
        if not stored:
            print(f"[提示] 账号 {username} 未配置密码环境变量，无DB回退登录已禁用")
            continue
        if needs_rehash(stored):
            print(f"[安全告警] 账号 {username} 密码为明文，请用 pbkdf2_sha256 哈希配置")
        elif verify_password("123456", stored):
            print(f"[安全告警] 账号 {username} 仍使用弱密码 123456，请尽快修改")
