from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from utils.auth_middleware import get_current_user, require_role
from utils.jwt_utils import authenticate, create_token
from utils.logger import get_logger
from utils.rate_limit import limiter

router = APIRouter(prefix="/auth", tags=["auth"])

logger = get_logger("api.auth")


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
    permissions: list[str] = []


@router.post("/impersonate", response_model=ImpersonateResponse)
def impersonate(req: ImpersonateRequest, user: dict = Depends(require_role("superadmin"))):
    from utils.jwt_utils import _mysql_client

    if _mysql_client is None:
        raise HTTPException(status_code=500, detail="服务未初始化")
    permissions = _mysql_client.get_role_permissions(req.target_role)
    if not permissions and req.target_role not in ("admin", "ops", "service", "dept"):
        row = _mysql_client.list_roles()
        existing_keys = [r["role_key"] for r in row]
        if req.target_role not in existing_keys:
            raise HTTPException(status_code=400, detail=f"不支持的角色: {req.target_role}")
    target_user = None
    try:
        conn = _mysql_client._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT username, dept FROM users WHERE role=%s AND status='active' LIMIT 1",
            (req.target_role,),
        )
        result = cursor.fetchone()
        cursor.close()
        if result:
            target_user = {"username": result[0], "dept": result[1] or ""}
    except Exception:
        pass
    username = target_user["username"] if target_user else req.target_role
    dept = target_user["dept"] if target_user else ""
    token = create_token(
        username=username,
        role=req.target_role,
        dept=dept,
        impersonated_by=user["sub"],
    )
    logger.info(f"超管 {user['sub']} 模拟登录为 {req.target_role}")
    try:
        _mysql_client.insert_operation_log(user["sub"], "impersonate", "auth", 0, f"模拟登录为 {req.target_role}")
    except Exception as e:
        logger.warning(f"模拟登录操作日志写入失败: {e}")
    return ImpersonateResponse(
        access_token=token,
        role=req.target_role,
        dept=dept,
        username=username,
        permissions=permissions,
    )
