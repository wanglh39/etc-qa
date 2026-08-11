from dotenv import load_dotenv

load_dotenv()

from utils.logger import setup_logging

setup_logging()

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.auth import router as auth_router
from api.routes import router
from app import create_service
from utils.config import get_config

cfg = get_config()
server_cfg = cfg.get("server", {})

app = FastAPI(title=server_cfg.get("title", "ETC客服QA智能检索系统"), version=server_cfg.get("version", "1.0.0"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

service = create_service()


app.include_router(auth_router, prefix="/api")
app.include_router(router, prefix="/api")


if __name__ == "__main__":
    workers = server_cfg.get("workers", 1)
    uvicorn.run(
        "main:app",
        host=server_cfg.get("host", "0.0.0.0"),
        port=server_cfg.get("port", 8000),
        workers=workers,
        reload=(workers == 1),
    )
