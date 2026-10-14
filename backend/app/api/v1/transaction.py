"""收支明细接口。"""

from __future__ import annotations

import logging
from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.exceptions import BizError
from app.core.validators import validate_amount
from app.crud import category as category_crud
from app.crud import transaction as transaction_crud
from app.db.session import get_db
from app.models.enums import TransactionType
from app.models.user import User
from app.schemas.common import ApiResponse, PageData, success
from app.schemas.transaction import (
    TransactionCreate,
    TransactionOut,
    TransactionQuery,
    TransactionSummary,
    TransactionUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transactions", tags=["收支明细"])


def _resolve_category(db: Session, category_id: int, user_id: int, tx_type: TransactionType):
    """校验分类可用性与收支类型一致性（不合规 → 400）。"""
    category = category_crud.get_accessible(db, category_id, user_id)
    if category is None:
        raise BizError("分类不存在或不属于当前用户", status_code=400)
    if category.type != tx_type:
        raise BizError(
            f"分类「{category.name}」的收支类型与本次提交的 type 不一致", status_code=400
        )
    return category


def _check_date_range(start_date: Optional[date], end_date: Optional[date]) -> None:
    if start_date and end_date and start_date > end_date:
        raise BizError("开始日期不能晚于结束日期", status_code=400)


# 注意：/summary 必须注册在 /{transaction_id} 之前，否则会被路径参数吞掉
@router.get(
    "/summary",
    response_model=ApiResponse[TransactionSummary],
    summary="收支汇总",
    description=(
        "按与明细列表相同的筛选条件（type / category_id / start_date / end_date）"
        "统计总收入、总支出与结余，金额与列表一致返回两位小数字符串。"
    ),
)
def transaction_summary(
    type: Optional[TransactionType] = Query(None, description="income / expense"),
    category_id: Optional[int] = Query(None, description="按分类筛选"),
    start_date: Optional[date] = Query(None, description="记账日期 >= 该日期（YYYY-MM-DD）"),
    end_date: Optional[date] = Query(None, description="记账日期 <= 该日期（YYYY-MM-DD）"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _check_date_range(start_date, end_date)
    query = TransactionQuery(
        page=1,
        page_size=1,
        type=type,
        category_id=category_id,
        start_date=start_date,
        end_date=end_date,
    )
    data = transaction_crud.summary(db, user_id=current_user.id, query=query)
    return success(TransactionSummary(**data))


@router.post(
    "",
    response_model=ApiResponse[TransactionOut],
    status_code=status.HTTP_201_CREATED,
    summary="新增收支记录",
    description=(
        "金额必须大于 0 且最多两位小数（不合规返回 400）；"
        "分类必须存在、属于当前用户可见范围，且分类类型与 type 一致（否则 400）。"
    ),
)
def create_transaction(
    payload: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    validate_amount(payload.amount)
    _resolve_category(db, payload.category_id, current_user.id, payload.type)

    created = transaction_crud.create(
        db,
        user_id=current_user.id,
        tx_type=payload.type,
        amount=payload.amount,
        category_id=payload.category_id,
        occurred_at=payload.occurred_at,
        remark=payload.remark,
    )
    # 重新查询以预先加载 category，避免出参序列化时的额外查询
    tx = transaction_crud.get(db, created.id, current_user.id)
    logger.info(
        "新增记账 | user_id=%s | tx_id=%s | type=%s | amount=%s",
        current_user.id,
        created.id,
        payload.type.value,
        payload.amount,
    )
    return success(TransactionOut.from_model(tx), message="创建成功", code=201)


@router.get(
    "",
    response_model=ApiResponse[PageData[TransactionOut]],
    summary="收支明细列表",
    description="分页 + 多条件筛选，结果只包含当前用户未删除的记录。",
)
def list_transactions(
    query: Annotated[TransactionQuery, Query()],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _check_date_range(query.start_date, query.end_date)
    items, total = transaction_crud.list_page(db, user_id=current_user.id, query=query)
    page = PageData.build(
        [TransactionOut.from_model(item) for item in items],
        total=total,
        page=query.page,
        page_size=query.page_size,
    )
    return success(page)


@router.get(
    "/{transaction_id}",
    response_model=ApiResponse[TransactionOut],
    summary="收支明细详情",
    description="记录不存在、已被删除或属于其他用户，统一返回 404。",
)
def get_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    tx = transaction_crud.get(db, transaction_id, current_user.id)
    if tx is None:
        raise BizError("记录不存在或已被删除", status_code=404)
    return success(TransactionOut.from_model(tx))


@router.put(
    "/{transaction_id}",
    response_model=ApiResponse[TransactionOut],
    summary="修改收支记录",
    description="部分更新：只传需要修改的字段；显式传 `\"remark\": null` 表示清空备注。",
)
def update_transaction(
    transaction_id: int,
    payload: TransactionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    tx = transaction_crud.get(db, transaction_id, current_user.id)
    if tx is None:
        raise BizError("记录不存在或已被删除", status_code=404)

    values = payload.model_dump(exclude_unset=True)
    if not values:
        raise BizError("没有需要更新的字段", status_code=400)

    effective_type: TransactionType = values.get("type") or tx.type
    effective_category_id: int = values.get("category_id") or tx.category_id

    if "amount" in values:
        validate_amount(payload.amount)
    _resolve_category(db, effective_category_id, current_user.id, effective_type)

    updated = transaction_crud.update(db, tx, values)
    tx = transaction_crud.get(db, updated.id, current_user.id)
    logger.info(
        "修改记账 | user_id=%s | tx_id=%s | 字段=%s",
        current_user.id,
        transaction_id,
        sorted(values.keys()),
    )
    return success(TransactionOut.from_model(tx), message="更新成功")


@router.delete(
    "/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="删除收支记录",
    description="软删除：删除后再查询该记录返回 404，但数据仍保留在库中（is_deleted=1）。",
)
def delete_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    tx = transaction_crud.get(db, transaction_id, current_user.id)
    if tx is None:
        raise BizError("记录不存在或已被删除", status_code=404)

    transaction_crud.soft_delete(db, tx)
    logger.info("删除记账 | user_id=%s | tx_id=%s", current_user.id, transaction_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
