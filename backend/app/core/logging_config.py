"""日志配置：控制台 + 按天轮转文件（应用日志 / 错误日志分离）。

每个请求都会分配一个 ``request_id``（见 ``middleware/request_log.py``），
通过 ``ContextVar`` 注入到日志格式中，便于把一次请求的所有日志串起来。
"""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from app.core.config import settings

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | rid=%(request_id)s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class RequestIdFilter(logging.Filter):
    """把当前请求的 request_id 注入到每条日志记录上。"""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003 - 标准接口名
        record.request_id = request_id_ctx.get()
        return True


def _file_handler(path: Path, level: int, formatter: logging.Formatter) -> TimedRotatingFileHandler:
    handler = TimedRotatingFileHandler(
        filename=str(path),
        when="midnight",
        backupCount=settings.LOG_RETENTION_DAYS,
        encoding="utf-8",
        delay=True,
    )
    handler.setLevel(level)
    handler.setFormatter(formatter)
    handler.addFilter(RequestIdFilter())
    return handler


def setup_logging() -> None:
    """初始化根日志器，需在任何业务日志输出之前调用。"""
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Windows 控制台默认使用系统代码页（中文为 GBK），
    # 这里只放宽错误处理策略，避免个别字符导致日志输出抛异常；
    # 落盘日志始终使用 UTF-8。
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(errors="backslashreplace")
        except (ValueError, OSError):  # pragma: no cover - 环境相关
            pass

    log_dir = Path(settings.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    # 用 pythonw.exe / 无控制台方式后台运行时 sys.stdout 为 None，
    # 此时只写文件日志，避免 emit 阶段抛异常导致日志丢失。
    if sys.stdout is not None:
        console = logging.StreamHandler(stream=sys.stdout)
        console.setLevel(level)
        console.setFormatter(formatter)
        console.addFilter(RequestIdFilter())
        root.addHandler(console)

    root.addHandler(_file_handler(log_dir / "app.log", level, formatter))
    # 错误日志单独一份，只记录 ERROR 及以上，方便排查线上问题
    root.addHandler(_file_handler(log_dir / "error.log", logging.ERROR, formatter))

    # uvicorn 自带 handler 会导致日志重复，这里统一交给根日志器
    for name in ("uvicorn", "uvicorn.error"):
        uv_logger = logging.getLogger(name)
        uv_logger.handlers.clear()
        uv_logger.propagate = True
    access_logger = logging.getLogger("uvicorn.access")
    access_logger.handlers.clear()
    access_logger.propagate = True
    # 请求日志由 RequestLogMiddleware 输出（信息更全），降低 uvicorn access 噪音
    access_logger.setLevel(logging.WARNING)

    # SQLAlchemy 仅在需要调试 SQL 时打开
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DB_ECHO else logging.WARNING
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
