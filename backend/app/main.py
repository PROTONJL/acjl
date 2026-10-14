"""个人记账本 - FastAPI 应用入口。

启动方式（在 ``backend/`` 目录下）::

    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

接口文档：
    - Swagger UI: http://localhost:8000/docs
    - OpenAPI JSON（Apifox 可直接导入）: http://localhost:8000/openapi.json
    - 前端页面: http://localhost:8000/
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import BASE_DIR, settings
from app.core.exceptions import register_exception_handlers
from app.core.logging_config import setup_logging
from app.db.session import engine
from app.middleware.request_log import RequestLogMiddleware

# 日志必须在应用创建前初始化
setup_logging()
logger = logging.getLogger(__name__)

FRONTEND_DIR: Path = BASE_DIR.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """启动/关闭钩子：做配置体检与数据库连通性检查。"""
    for warning in settings.startup_warnings():
        logger.warning("配置提醒：%s", warning)

    if settings.STARTUP_DB_CHECK:
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            logger.info(
                "数据库连接正常 | %s:%s/%s",
                settings.DB_HOST,
                settings.DB_PORT,
                settings.DB_NAME,
            )
        except Exception:
            logger.error(
                "数据库连接失败，请检查 backend/.env 配置与 MySQL 服务状态"
                "（初始化：python -m app.db.init_db）",
                exc_info=True,
            )

    logger.info(
        "%s v%s 启动完成 | 环境=%s",
        settings.APP_NAME,
        settings.APP_VERSION,
        "debug" if settings.DEBUG else "prod",
    )
    yield
    engine.dispose()
    logger.info("应用已关闭，数据库连接池已释放")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "个人记账本后端 API。\n\n"
            "**统一响应结构**：`{code, message, data}`，其中 `code` 与 HTTP 状态码一致；"
            "错误时（422）额外返回 `errors` 字段级明细。\n\n"
            "**校验约定**：类型/结构/格式错误 → 422；业务与安全策略（密码强度、"
            "金额必须大于 0 等）→ 400。详见 docs/VALIDATION-MATRIX.md。"
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # 请求日志 + request_id
    app.add_middleware(RequestLogMiddleware)

    # CORS：默认放开，生产环境请在 .env 中用 CORS_ORIGINS 指定白名单
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    _mount_frontend(app)
    return app


def _mount_frontend(app: FastAPI) -> None:
    """挂载前端静态资源（Vue3 CDN 版，无需 npm 构建）。"""
    if not FRONTEND_DIR.exists():
        logger.warning("前端目录不存在，跳过静态资源挂载：%s", FRONTEND_DIR)
        return

    static_dir = FRONTEND_DIR / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/", include_in_schema=False)
    def index_page() -> FileResponse:
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/login", include_in_schema=False)
    def login_page() -> FileResponse:
        return FileResponse(FRONTEND_DIR / "login.html")


app = create_app()
