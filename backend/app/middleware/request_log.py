"""请求日志中间件：为每个请求生成 request_id，记录耗时与状态码。"""

from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging_config import request_id_ctx

logger = logging.getLogger("app.request")


class RequestLogMiddleware(BaseHTTPMiddleware):
    """记录 ``方法 路径 状态码 耗时``，并把 request_id 回写到响应头。

    注意：出于安全考虑，日志中不会记录请求体（避免明文密码落盘）。
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = uuid.uuid4().hex[:12]
        # 同一个 request 对象与下游 handler 共享 scope["state"]，异常处理器也能读到
        request.state.request_id = request_id
        token = request_id_ctx.set(request_id)
        start = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            elapsed = (time.perf_counter() - start) * 1000
            logger.exception(
                "请求异常 | %s %s | %.1fms | client=%s",
                request.method,
                request.url.path,
                elapsed,
                request.client.host if request.client else "-",
            )
            raise
        else:
            elapsed = (time.perf_counter() - start) * 1000
            response.headers["X-Request-ID"] = request_id
            log = logger.warning if response.status_code >= 400 else logger.info
            log(
                "请求完成 | %s %s | status=%s | %.1fms | client=%s",
                request.method,
                request.url.path,
                response.status_code,
                elapsed,
                request.client.host if request.client else "-",
            )
            return response
        finally:
            request_id_ctx.reset(token)
