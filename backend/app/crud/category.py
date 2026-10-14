"""分类数据访问。"""

from __future__ import annotations

from typing import List, Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.enums import TransactionType
from app.models.transaction import Transaction


def list_categories(
    db: Session,
    user_id: int,
    tx_type: Optional[TransactionType] = None,
) -> List[Category]:
    """返回「系统预置 + 当前用户自定义」的分类。"""
    stmt = select(Category).where(
        (Category.user_id.is_(None)) | (Category.user_id == user_id)
    )
    if tx_type is not None:
        stmt = stmt.where(Category.type == tx_type)
    stmt = stmt.order_by(Category.type, Category.sort_order, Category.id)
    return list(db.scalars(stmt).all())


def get_accessible(db: Session, category_id: int, user_id: int) -> Optional[Category]:
    """取一个当前用户可用的分类（系统预置或自己的）。"""
    return db.scalar(
        select(Category).where(
            Category.id == category_id,
            (Category.user_id.is_(None)) | (Category.user_id == user_id),
        )
    )


def get_owned(db: Session, category_id: int, user_id: int) -> Optional[Category]:
    """只取当前用户自己创建的分类（用于修改/删除鉴权）。"""
    return db.scalar(
        select(Category).where(
            Category.id == category_id,
            Category.user_id == user_id,
        )
    )


def name_exists(
    db: Session,
    user_id: int,
    name: str,
    tx_type: TransactionType,
    exclude_id: Optional[int] = None,
) -> bool:
    stmt = select(Category.id).where(
        Category.user_id == user_id,
        Category.name == name,
        Category.type == tx_type,
    )
    if exclude_id is not None:
        stmt = stmt.where(Category.id != exclude_id)
    return db.scalar(stmt) is not None


def create(
    db: Session,
    *,
    user_id: int,
    name: str,
    tx_type: TransactionType,
    icon: Optional[str] = None,
    sort_order: int = 0,
) -> Category:
    category = Category(
        user_id=user_id, name=name, type=tx_type, icon=icon, sort_order=sort_order
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update(db: Session, category: Category, values: dict) -> Category:
    for field, value in values.items():
        setattr(category, field, value)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def delete(db: Session, category: Category) -> None:
    db.delete(category)
    db.commit()


def count_transactions(db: Session, category_id: int, include_deleted: bool = False) -> int:
    stmt = select(func.count(Transaction.id)).where(Transaction.category_id == category_id)
    if not include_deleted:
        stmt = stmt.where(Transaction.is_deleted.is_(False))
    return int(db.scalar(stmt) or 0)


def ensure_preset_exists(db: Session, presets: Sequence[dict]) -> int:
    """把预置分类写入数据库（幂等），返回新增数量。"""
    existing = {
        (row.name, row.type)
        for row in db.scalars(select(Category).where(Category.user_id.is_(None))).all()
    }
    created = 0
    for item in presets:
        if (item["name"], item["type"]) in existing:
            continue
        db.add(Category(user_id=None, **item))
        created += 1
    if created:
        db.commit()
    return created
