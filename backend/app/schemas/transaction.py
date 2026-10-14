"""收支明细相关的请求 / 响应模型。"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models.enums import TransactionType

Remark = Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)]

# max_digits 只做「结构」兜底（防止超出 DECIMAL(12,2) 溢出，返回 422）；
# 「必须 > 0 / 最多两位小数」属于业务规则，由业务层校验并返回 400
AmountField = Annotated[Decimal, Field(max_digits=12)]


class TransactionCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "type": "expense",
                "amount": "25.80",
                "category_id": 1,
                "remark": "午餐",
                "occurred_at": "2026-10-14",
            }
        },
    )

    type: TransactionType
    amount: AmountField
    category_id: int
    occurred_at: date
    remark: Optional[Remark] = None


class TransactionUpdate(BaseModel):
    """部分更新：只传需要改的字段；显式传 null 表示清空 remark。"""

    model_config = ConfigDict(extra="forbid")

    type: Optional[TransactionType] = None
    amount: Optional[AmountField] = None
    category_id: Optional[int] = None
    occurred_at: Optional[date] = None
    remark: Optional[Remark] = None


class TransactionQuery(BaseModel):
    """明细列表查询条件（全部走 Query String）。"""

    page: int = Field(1, ge=1, le=100000, description="页码，从 1 开始")
    page_size: int = Field(20, ge=1, le=100, description="每页条数，最大 100")
    type: Optional[TransactionType] = Field(None, description="按收支类型筛选")
    category_id: Optional[int] = Field(None, description="按分类筛选")
    start_date: Optional[date] = Field(None, description="记账日期 >= start_date")
    end_date: Optional[date] = Field(None, description="记账日期 <= end_date")
    keyword: Optional[Annotated[str, StringConstraints(strip_whitespace=True, max_length=50)]] = Field(
        None, description="备注模糊匹配"
    )
    sort_by: Literal["occurred_at", "amount", "created_at"] = Field("occurred_at", description="排序字段")
    order: Literal["asc", "desc"] = Field("desc", description="排序方向")


class TransactionOut(BaseModel):
    """明细出参。金额以「两位小数字符串」返回，避免 JS 浮点精度问题。"""

    id: int
    type: TransactionType
    amount: str = Field(..., description="金额字符串，固定两位小数，恒为正数")
    category_id: int
    category_name: Optional[str] = None
    category_icon: Optional[str] = None
    remark: Optional[str] = None
    occurred_at: date
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, tx) -> "TransactionOut":
        return cls(
            id=tx.id,
            type=tx.type,
            amount=f"{Decimal(tx.amount):.2f}",
            category_id=tx.category_id,
            category_name=tx.category.name if tx.category else None,
            category_icon=tx.category.icon if tx.category else None,
            remark=tx.remark,
            occurred_at=tx.occurred_at,
            created_at=tx.created_at,
            updated_at=tx.updated_at,
        )


class TransactionSummary(BaseModel):
    """收支汇总。"""

    total_income: str = Field(..., description="总收入，两位小数字符串")
    total_expense: str = Field(..., description="总支出，两位小数字符串")
    balance: str = Field(..., description="结余 = 总收入 - 总支出")
    income_count: int = 0
    expense_count: int = 0
    start_date: Optional[date] = None
    end_date: Optional[date] = None

