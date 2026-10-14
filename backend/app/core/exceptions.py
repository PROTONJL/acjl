"""统一业务异常与全局异常处理器。

响应体约定（所有错误响应结构一致）::

    {"code": 400, "message": "金额必须大于 0", "data": null, "errors": [...]}

``code`` 与 HTTP 状态码保持一致，前端与 Apifox 断言时二者都可用。
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional, Sequence

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

STATUS_MESSAGE = {
    400: "请求参数有误",
    401: "未认证或登录状态已失效",
    403: "无权访问该资源",
    404: "资源不存在",
    405: "请求方法不被允许",
    409: "资源冲突",
    422: "请求参数校验失败",
    500: "服务器内部错误",
}

MAX_INPUT_PREVIEW = 100


class BizError(Exception):
    """业务异常：由业务层主动抛出，携带期望的 HTTP 状态码与提示语。"""

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        code: Optional[int] = None,
        errors: Optional[Sequence[dict]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code if code is not None else status_code
        self.errors = list(errors) if errors else None


def error_payload(
    code: int,
    message: str,
    errors: Optional[Sequence[dict]] = None,
) -> dict:
    """构造统一的错误响应体。"""
    payload: dict[str, Any] = {"code": code, "message": message, "data": None}
    if errors:
        payload["errors"] = list(errors)
    return payload


def _preview(value: Any) -> Any:
    """把非法入参安全地放进响应体里（避免不可序列化 / 过长内容）。"""
    if value is None or isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, str):
        return value if len(value) <= MAX_INPUT_PREVIEW else value[:MAX_INPUT_PREVIEW] + "..."
    if isinstance(value, (list, dict)):
        return value if len(str(value)) <= MAX_INPUT_PREVIEW else str(value)[:MAX_INPUT_PREVIEW] + "..."
    return str(value)[:MAX_INPUT_PREVIEW]


def _format_validation_errors(exc: RequestValidationError) -> List[dict]:
    """把 Pydantic 的校验错误整理成字段级明细，便于接口测试定位。"""
    details: List[dict] = []
    for err in exc.errors():
        location = err.get("loc", ())
        # loc 形如 ("body", "amount") / ("query", "page")，这里保留完整路径
        field = ".".join(str(part) for part in location) or "body"
        details.append(
            {
                "field": field,
                "message": err.get("msg", "参数非法"),
                "type": err.get("type", "value_error"),
                "input": _preview(err.get("input")),
            }
        )
    return details


def register_exception_handlers(app: FastAPI) -> None:  # noqa: C901 - 处理器集中注册，保持可读性
    """注册全局异常处理器，保证任何异常都返回统一结构。"""

    @app.exception_handler(BizError)
    async def biz_error_handler(request: Request, exc: BizError) -> JSONResponse:
        logger.warning(
            "业务异常 | %s %s | status=%s | %s",
            request.method,
            request.url.path,
            exc.status_code,
            exc.message,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(exc.code, exc.message, exc.errors),
            headers={"X-Request-ID": getattr(request.state, "request_id", "-")},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = _format_validation_errors(exc)
        logger.warning(
            "参数校验失败(422) | %s %s | %s",
            request.method,
            request.url.path,
            details,
        )
        return JSONResponse(
            status_code=422,
            content=error_payload(422, STATUS_MESSAGE[422], details),
            headers={"X-Request-ID": getattr(request.state, "request_id", "-")},
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        message = STATUS_MESSAGE.get(exc.status_code)
        if isinstance(exc.detail, str) and exc.detail:
            message = exc.detail
        elif not message:
            message = "请求失败"
        logger.warning(
            "HTTP 异常 | %s %s | status=%s | %s",
            request.method,
            request.url.path,
            exc.status_code,
            message,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(exc.status_code, message),
            headers={"X-Request-ID": getattr(request.state, "request_id", "-")},
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.exception(
            "数据库异常 | %s %s | %s", request.method, request.url.path, type(exc).__name__
        )
        return JSONResponse(
            status_code=500,
            content=error_payload(500, "数据库操作失败，请稍后重试"),
            headers={"X-Request-ID": getattr(request.state, "request_id", "-")},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "未捕获异常 | %s %s | %s", request.method, request.url.path, type(exc).__name__
        )
        return JSONResponse(
            status_code=500,
            content=error_payload(500, STATUS_MESSAGE[500]),
            headers={"X-Request-ID": getattr(request.state, "request_id", "-")},
        )
