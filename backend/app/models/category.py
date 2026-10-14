"""收支分类表模型。"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import PK_TYPE, Base, TimestampMixin
from app.models.enums import TransactionType

if TYPE_CHECKING:  # pragma: no cover
    from app.models.transaction import Transaction
    from app.models.user import User


def _enum_values(enum_cls) -> List[str]:
    """让数据库存 income/expense 而不是枚举成员名 INCOME/EXPENSE。"""
    return [member.value for member in enum_cls]


class Category(Base, TimestampMixin):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(PK_TYPE, primary_key=True, autoincrement=True)
    # user_id 为 NULL 表示系统预置分类
    user_id: Mapped[Optional[int]] = mapped_column(
        PK_TYPE, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, comment="NULL=系统预置"
    )
    name: Mapped[str] = mapped_column(String(30), nullable=False)
    type: Mapped[TransactionType] = mapped_column(
        SAEnum(TransactionType, name="transaction_type", values_callable=_enum_values),
        nullable=False,
        comment="收入/支出",
    )
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    user: Mapped[Optional["User"]] = relationship(back_populates="categories")
    transactions: Mapped[List["Transaction"]] = relationship(back_populates="category")

    @property
    def is_system(self) -> bool:
        """是否为系统预置分类（user_id 为空即预置，不可删改）。"""
        return self.user_id is None

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return f"<Category id={self.id} name={self.name!r} type={self.type}>"
