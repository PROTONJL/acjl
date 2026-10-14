"""健康检查。"""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["基础"])


@router.get("/health", summary="健康检查", description="探活接口，同时探测数据库连通性")
def health(db: Session = Depends(get_db)) -> dict:
    database_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:  # pragma: no cover - 依赖外部环境
        logger.exception("健康检查：数据库连接失败")
        database_status = "error"

    return {
        "status": "ok" if database_status == "ok" else "degraded",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": database_status,
        # 与库中时间保持一致：统一使用服务器本地时间
        "server_time": datetime.now().isoformat(),
    }
