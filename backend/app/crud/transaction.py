"""收支明细数据访问。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy import Select, case, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.enums import TransactionType
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionQuery

SORT_COLUMNS = {
    "occurred_at": Transaction.occurred_at,
    "amount": Transaction.amount,
    "created_at": Transaction.created_at,
}


def _base_conditions(user_id: int, query: Optional[TransactionQuery] = None) -> list:
    """所有查询都以 user_id + 未删除 为第一条件，保证数据隔离。"""
    if query is not None:
        start_date = query.start_date
        end_date = query.end_date
    else:
        start_date = None
        end_date = None

    conditions: list = [
        Transaction.user_id == user_id,
        Transaction.is_deleted.is_(False),
    ]
    if query is not None:
        if query.type is not None:
            conditions.append(Transaction.type == query.type)
        if query.category_id is not None:
            conditions.append(Transaction.category_id == query.category_id)
        if query.keyword:
            conditions.append(Transaction.remark.like(f"%{query.keyword}%"))
    if start_date is not None:
        conditions.append(Transaction.occurred_at >= start_date)
    if end_date is not None:
        conditions.append(Transaction.occurred_at <= end_date)
    return conditions


def create(
    db: Session,
    *,
    user_id: int,
    tx_type: TransactionType,
    amount: Decimal,
    category_id: int,
    occurred_at: date,
    remark: Optional[str] = None,
) -> Transaction:
    tx = Transaction(
        user_id=user_id,
        type=tx_type,
        amount=amount,
        category_id=category_id,
        occurred_at=occurred_at,
        remark=remark,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def get(db: Session, transaction_id: int, user_id: int) -> Optional[Transaction]:
    """按 ID 取明细，且必须属于当前用户、未被删除。"""
    return db.scalar(
        select(Transaction)
        .options(joinedload(Transaction.category))
        .where(
            Transaction.id == transaction_id,
            Transaction.user_id == user_id,
            Transaction.is_deleted.is_(False),
        )
    )


def list_page(
    db: Session,
    *,
    user_id: int,
    query: TransactionQuery,
) -> Tuple[List[Transaction], int]:
    conditions = _base_conditions(user_id, query)

    total = int(db.scalar(select(func.count(Transaction.id)).where(*conditions)) or 0)

    sort_column = SORT_COLUMNS[query.sort_by]
    order_clause = sort_column.asc() if query.order == "asc" else sort_column.desc()

    stmt: Select = (
        select(Transaction)
        .options(joinedload(Transaction.category))
        .where(*conditions)
        .order_by(order_clause, Transaction.id.desc())
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    )
    items = list(db.scalars(stmt).all())
    return items, total


def update(db: Session, tx: Transaction, values: dict) -> Transaction:
    for field, value in values.items():
        setattr(tx, field, value)
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def soft_delete(db: Session, tx: Transaction) -> None:
    tx.is_deleted = True
    db.add(tx)
    db.commit()


def summary(
    db: Session,
    *,
    user_id: int,
    query: Optional[TransactionQuery] = None,
) -> dict:
    """按筛选条件汇总收入 / 支出 / 结余。"""
    conditions = _base_conditions(user_id, query)

    income_sum = func.coalesce(
        func.sum(case((Transaction.type == TransactionType.INCOME, Transaction.amount), else_=0)),
        0,
    )
    expense_sum = func.coalesce(
        func.sum(case((Transaction.type == TransactionType.EXPENSE, Transaction.amount), else_=0)),
        0,
    )
    income_count = func.coalesce(
        func.sum(case((Transaction.type == TransactionType.INCOME, 1), else_=0)), 0
    )
    expense_count = func.coalesce(
        func.sum(case((Transaction.type == TransactionType.EXPENSE, 1), else_=0)), 0
    )

    row = db.execute(
        select(income_sum, expense_sum, income_count, expense_count).where(*conditions)
    ).one()

    income = Decimal(str(row[0] or 0))
    expense = Decimal(str(row[1] or 0))
    return {
        "total_income": f"{income:.2f}",
        "total_expense": f"{expense:.2f}",
        "balance": f"{income - expense:.2f}",
        "income_count": int(row[2] or 0),
        "expense_count": int(row[3] or 0),
        "start_date": query.start_date if query else None,
        "end_date": query.end_date if query else None,
    }
