"""分类相关的请求 / 响应模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models.enums import TransactionType

CategoryName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)
]
CategoryIcon = Annotated[str, StringConstraints(strip_whitespace=True, max_length=50)]


class CategoryCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"example": {"name": "宠物", "type": "expense", "icon": "🐱", "sort_order": 100}},
    )

    name: CategoryName
    type: TransactionType
    icon: Optional[CategoryIcon] = None
    sort_order: int = Field(0, ge=0, le=9999)


class CategoryUpdate(BaseModel):
    """分类更新：不允许修改 type（已产生的记录会失去一致性）。"""

    model_config = ConfigDict(extra="forbid")

    name: Optional[CategoryName] = None
    icon: Optional[CategoryIcon] = None
    sort_order: Optional[int] = Field(None, ge=0, le=9999)


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: TransactionType
    icon: Optional[str] = None
    sort_order: int
    is_system: bool = Field(False, description="true=系统预置分类，不可修改或删除")
    created_at: datetime
