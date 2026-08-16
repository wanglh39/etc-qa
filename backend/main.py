import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from utils.logger import setup_logging, get_logger

setup_logging()

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.auth import router as auth_router
from api.routes import router
from app import create_service
from utils.config import get_config
from utils.password import check_password_policy

check_password_policy()

cfg = get_config()
server_cfg = cfg.get("server", {})
logger = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("应用启动中 (lifespan startup)...")
    service = create_service()
    app.state.service = service
    logger.info("应用启动完成，开始接受请求")
    yield
    logger.info("应用关闭中 (lifespan shutdown)...")
    try:
        if hasattr(service, "recall") and hasattr(service.recall, "milvus"):
            service.recall.milvus.close()
            logger.info("Milvus连接已关闭")
    except Exception as e:
        logger.warning(f"关闭Milvus连接时出错: {e}")
    logger.info("应用已关闭")


app = FastAPI(
    title=server_cfg.get("title", "ETC客服QA智能检索系统"),
    version=server_cfg.get("version", "1.0.0"),
    lifespan=lifespan,
)

allow_origins = server_cfg.get("cors_origins", [])
_env_origins = os.environ.get("ETC_QA_CORS_ORIGINS")
if _env_origins:
    allow_origins = [o.strip() for o in _env_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.include_router(auth_router, prefix="/api")
app.include_router(router, prefix="/api")


if __name__ == "__main__":
    workers = server_cfg.get("workers", 1)
    uvicorn.run(
        "main:app",
        host=server_cfg.get("host", "0.0.0.0"),
        port=server_cfg.get("port", 8000),
        workers=workers,
        reload=server_cfg.get("reload", False),
    )
