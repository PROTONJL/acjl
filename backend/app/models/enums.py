"""业务枚举。"""

from __future__ import annotations

import enum


class TransactionType(str, enum.Enum):
    """收支类型。"""

    INCOME = "income"
    EXPENSE = "expense"
