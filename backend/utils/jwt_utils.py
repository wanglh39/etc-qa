import os
from datetime import datetime, timedelta

import jwt

SECRET_KEY = os.environ.get("ETC_QA_JWT_SECRET", "etc-qa-jwt-secret-key-dev")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# 初始用户数据：角色/部门为系统固定元数据，密码从环境变量（.env）注入
USERS = {
    "admin": {"password": os.environ.get("ETC_QA_ADMIN_PASSWORD", "123456"), "role": "admin", "dept": ""},
    "service": {"password": os.environ.get("ETC_QA_SERVICE_PASSWORD", "123456"), "role": "service", "dept": ""},
    "dept": {"password": os.environ.get("ETC_QA_DEPT_PASSWORD", "123456"), "role": "dept", "dept": "aftersale"},
}


def create_token(username: str, role: str, dept: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": username,
        "role": role,
        "dept": dept,
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def authenticate(username: str, password: str) -> dict | None:
    user = USERS.get(username)
    if user and user["password"] == password:
        return {"username": username, "role": user["role"], "dept": user["dept"]}
    return None
