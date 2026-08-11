from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from utils.jwt_utils import verify_token

security = HTTPBearer(auto_error=False)


async def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> dict:
    if credentials is None:
        raise HTTPException(status_code=401, detail="未提供认证令牌")
    try:
        payload = verify_token(credentials.credentials)
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="令牌无效或已过期")
