from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from utils.jwt_utils import authenticate, create_token
from utils.rate_limit import limiter

router = APIRouter(prefix="/auth", tags=["auth"])


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
