from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from utils.auth_middleware import get_current_user, require_role
from utils.jwt_utils import authenticate, create_token
from utils.logger import get_logger
from utils.rate_limit import limiter

router = APIRouter(prefix="/auth", tags=["auth"])

logger = get_logger("api.auth")

IMPERSONATE_TARGETS = {
    "admin": {"username": "admin", "role": "admin", "dept": ""},
    "ops": {"username": "ops", "role": "ops", "dept": ""},
    "service": {"username": "service", "role": "service", "dept": ""},
    "dept": {"username": "dept", "role": "dept", "dept": "aftersale"},
}


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    dept: str


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, request: Request):
    ip = request.client.host if request.client else "unknown"
    if not limiter.check(f"login:ip:{ip}", 30, 60):
        raise HTTPException(status_code=429, detail="尝试过于频繁，请稍后再试")
    if not limiter.check(f"login:user:{ip}:{req.username}", 5, 60):
        raise HTTPException(status_code=429, detail="尝试过于频繁，请稍后再试")

    user = authenticate(req.username, req.password)
    if user is None:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = create_token(user["username"], user["role"], user["dept"])
    return LoginResponse(
        access_token=token,
        role=user["role"],
        dept=user["dept"],
    )


@router.get("/verify")
def verify_token_endpoint(user: dict = Depends(get_current_user)):
    return {"username": user["sub"], "role": user["role"], "dept": user.get("dept", "")}


class ImpersonateRequest(BaseModel):
    target_role: str


class ImpersonateResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    dept: str
    username: str


@router.post("/impersonate", response_model=ImpersonateResponse)
def impersonate(req: ImpersonateRequest, user: dict = Depends(require_role("superadmin"))):
    target = IMPERSONATE_TARGETS.get(req.target_role)
    if target is None:
        raise HTTPException(status_code=400, detail=f"不支持的角色: {req.target_role}")
    token = create_token(
        username=target["username"],
        role=target["role"],
        dept=target["dept"],
        impersonated_by=user["sub"],
    )
    logger.info(f"超管 {user['sub']} 模拟登录为 {target['role']}")
    try:
        from utils.jwt_utils import _mysql_client
        if _mysql_client is not None:
            _mysql_client.insert_operation_log(
                user["sub"], "impersonate", "auth", 0,
                f"模拟登录为 {target['role']}"
            )
    except Exception as e:
        logger.warning(f"模拟登录操作日志写入失败: {e}")
    return ImpersonateResponse(
        access_token=token,
        role=target["role"],
        dept=target["dept"],
        username=target["username"],
    )
