from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from utils.jwt_utils import verify_token
from utils.logger import get_logger

logger = get_logger("auth")

security = HTTPBearer(auto_error=False)


async def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> dict:
    if credentials is None:
        raise HTTPException(status_code=401, detail="未提供认证令牌")
    try:
        payload = verify_token(credentials.credentials)
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="令牌无效或已过期")


def require_role(*roles: str, page: str = ""):
    async def role_checker(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") in roles:
            return user
        if page:
            try:
                from api.routes import mysql_client

                if mysql_client:
                    perms = mysql_client.get_role_permissions(user.get("role", ""))
                    if page in perms:
                        return user
            except Exception as e:
                logger.warning(f"permissions兜底检查失败: {e}")
        raise HTTPException(status_code=403, detail="权限不足")

    return role_checker
