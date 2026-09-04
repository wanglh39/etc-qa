import os
from datetime import datetime, timedelta

import jwt

from utils.logger import get_logger
from utils.password import verify_password

logger = get_logger("utils.jwt_utils")

_SECRET_KEY = os.environ.get("ETC_QA_JWT_SECRET", "").strip()
if not _SECRET_KEY:
    raise RuntimeError(
        "ETC_QA_JWT_SECRET 未设置：JWT 密钥不再使用内置默认值。"
        "请通过环境变量或 .env 配置随机强密钥，"
        '生成方式: python -c "import secrets; print(secrets.token_urlsafe(48))"'
    )

SECRET_KEY = _SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# 初始用户数据：角色/部门为系统固定元数据，密码从环境变量（.env）注入。
# 密码为空表示未配置，此时无 DB 回退登录会被拒绝（fail-closed），不再使用默认弱密码。
USERS = {
    "superadmin": {
        "password": os.environ.get("ETC_QA_SUPERADMIN_PASSWORD", ""),
        "role": "superadmin",
        "dept": "",
    },
    "admin": {"password": os.environ.get("ETC_QA_ADMIN_PASSWORD", ""), "role": "admin", "dept": ""},
    "service": {"password": os.environ.get("ETC_QA_SERVICE_PASSWORD", ""), "role": "service", "dept": ""},
    "dept": {"password": os.environ.get("ETC_QA_DEPT_PASSWORD", ""), "role": "dept", "dept": "aftersale"},
    "ops": {"password": os.environ.get("ETC_QA_OPS_PASSWORD", ""), "role": "ops", "dept": ""},
}


def create_token(username: str, role: str, dept: str, impersonated_by: str | None = None) -> str:
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": username,
        "role": role,
        "dept": dept,
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    if impersonated_by:
        payload["impersonated_by"] = impersonated_by
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


_mysql_client = None


def set_mysql_client(client):
    global _mysql_client
    _mysql_client = client


def authenticate(username: str, password: str) -> dict | None:
    if _mysql_client is not None:
        # DB 可用时，DB 是唯一鉴权真源：禁用/不存在/密码错/DB异常一律拒绝登录，
        # 不再回退到硬编码 USERS，避免内置账号成为不可禁用的后门。
        try:
            user = _mysql_client.get_user_by_username(username)
            if user and user.get("status") == "active" and verify_password(password, user["password_hash"]):
                return {"username": username, "role": user["role"], "dept": user.get("dept", "")}
        except Exception as e:
            logger.error(f"DB鉴权失败，拒绝登录(fail-closed): {e}")
        return None
    # 无 DB（本地开发/测试）：回退硬编码 USERS，未配置密码则拒绝
    user = USERS.get(username)
    if user and user.get("password") and verify_password(password, user["password"]):
        return {"username": username, "role": user["role"], "dept": user["dept"]}
    return None
