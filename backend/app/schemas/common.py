"""通用响应结构：统一响应体、分页、字段级错误。"""

from __future__ import annotations

import math
from typing import Any, Generic, List, Optional, Sequence, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一响应体：``code`` 与 HTTP 状态码保持一致。

    出错时（如 422）会额外带上 ``errors`` 字段的字段级明细，
    具体结构见 docs/API.md。
    """

    model_config = ConfigDict(
        json_schema_extra={"example": {"code": 200, "message": "success", "data": None}}
    )

    code: int = 200
    message: str = "success"
    data: Optional[T] = None


class PageData(BaseModel, Generic[T]):
    """分页数据。"""

    items: List[T] = Field(default_factory=list)
    total: int = Field(0, description="满足条件的记录总数")
    page: int = Field(1, description="当前页码，从 1 开始")
    page_size: int = Field(20, description="每页条数")
    pages: int = Field(0, description="总页数")

    @classmethod
    def build(
        cls,
        items: Sequence[T],
        total: int,
        page: int,
        page_size: int,
    ) -> "PageData[T]":
        pages = math.ceil(total / page_size) if page_size > 0 else 0
        return cls(items=list(items), total=total, page=page, page_size=page_size, pages=pages)


def success(data: Any = None, message: str = "success", code: int = 200) -> dict:
    """构造统一成功响应体。"""
    return {"code": code, "message": message, "data": data}
