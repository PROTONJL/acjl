"""收支明细表模型。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Date, ForeignKey, Index, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import PK_TYPE, Base, TimestampMixin
from app.models.category import _enum_values
from app.models.enums import TransactionType

if TYPE_CHECKING:  # pragma: no cover
    from app.models.category import Category
    from app.models.user import User


class Transaction(Base, TimestampMixin):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("idx_tx_user_occurred", "user_id", "occurred_at"),
        Index("idx_tx_user_type", "user_id", "type"),
        Index("idx_tx_user_category", "user_id", "category_id"),
    )

    id: Mapped[int] = mapped_column(PK_TYPE, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        PK_TYPE, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[int] = mapped_column(
        PK_TYPE, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False
    )
    type: Mapped[TransactionType] = mapped_column(
        SAEnum(TransactionType, name="transaction_type", values_callable=_enum_values),
        nullable=False,
        comment="收入/支出",
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, comment="金额，恒为正数"
    )
    remark: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    occurred_at: Mapped[date] = mapped_column(Date, nullable=False, comment="记账日期")
    # 软删除：删掉后查询不到，但数据保留可追溯
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0", comment="软删除标记"
    )

    user: Mapped["User"] = relationship(back_populates="transactions")
    category: Mapped["Category"] = relationship(back_populates="transactions")

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return (
            f"<Transaction id={self.id} type={self.type} "
            f"amount={self.amount} occurred_at={self.occurred_at}>"
        )
