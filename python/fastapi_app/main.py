from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .database import close_db, get_session_factory, init_db
from .exceptions import NiuQIError
from .routers import assets, export, generation, health, projects, settings as settings_router, styles, upload
from .schemas import ErrorDetail, ErrorResponse
from .storage import StorageManager
from .services.style_service import StyleService


def configure_logging() -> None:
    settings = get_settings()
    logs_dir = settings.resolved_data_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()

    formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    file_handler = RotatingFileHandler(
        logs_dir / "app.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    if os.getenv("NIUQI2D_DEV") == "1":
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root.addHandler(console_handler)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    settings = get_settings()
    storage = StorageManager(str(settings.resolved_data_dir))
    await storage.initialize()
    app.state.storage = storage
    await init_db()
    async with get_session_factory()() as session:
        await StyleService(session).ensure_presets()
    yield
    await close_db()


def build_error_response(
    code: str,
    message: str,
    status_code: int,
    details: dict[str, Any] | None,
) -> JSONResponse:
    response = ErrorResponse(error=ErrorDetail(code=code, message=message, details=details))
    return JSONResponse(status_code=status_code, content=response.model_dump())


app = FastAPI(title="NiuQI2D", version="1.0.0", lifespan=lifespan)

settings = get_settings()
images_dir = settings.resolved_data_dir / "images"
images_dir.mkdir(parents=True, exist_ok=True)
app.mount("/images", StaticFiles(directory=images_dir), name="images")

if os.getenv("NIUQI2D_DEV") == "1":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )
else:
    # 非开发模式也启用 CORS，以便前后端独立运行时正常工作
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.exception_handler(NiuQIError)
async def niuqi_error_handler(request: Request, exc: NiuQIError) -> JSONResponse:
    logging.getLogger(__name__).warning("Handled error at %s: %s", request.url.path, exc.message)
    return build_error_response(exc.code, exc.message, exc.status_code, exc.details)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return build_error_response(
        "INVALID_PARAM",
        "请求参数无效",
        422,
        {"errors": exc.errors()},
    )


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logging.getLogger(__name__).exception("Unhandled error at %s", request.url.path)
    return build_error_response("INTERNAL_ERROR", "服务器内部错误", 500, None)


app.include_router(health.router)
app.include_router(upload.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")
app.include_router(styles.router, prefix="/api/v1")
app.include_router(generation.router, prefix="/api/v1")
app.include_router(assets.router, prefix="/api/v1")
app.include_router(assets.tags_router, prefix="/api/v1")
app.include_router(export.router, prefix="/api/v1")
app.include_router(settings_router.router, prefix="/api/v1")
