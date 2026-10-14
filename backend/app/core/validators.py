"""业务层校验器。

**校验责任划分（重要）**：``schemas`` 里的 Pydantic 只负责「类型 / 必填 / 结构 /
枚举取值 / 字符串格式」，这类问题 FastAPI 原生返回 **422**；
而密码策略、金额范围这类业务规则统一在业务层校验并返回 **400**，
以保证「绕过前端直接调接口」时 DTO 层的防御依然生效。
详见 ``docs/VALIDATION-MATRIX.md``。
"""

from __future__ import annotations

import re
from decimal import Decimal

from app.core.config import settings
from app.core.exceptions import BizError

# DECIMAL(12,2) 能表示的最大值
MAX_AMOUNT = Decimal("9999999999.99")

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,20}$")
USERNAME_RULE = "用户名必须为 3-20 位，仅允许字母、数字和下划线"

_HAS_LETTER = re.compile(r"[A-Za-z]")
_HAS_DIGIT = re.compile(r"\d")


def password_rule_text() -> str:
    return (
        f"密码必须为 {settings.PASSWORD_MIN_LENGTH}-{settings.PASSWORD_MAX_LENGTH} 位，"
        "且同时包含字母和数字"
    )


def validate_password_strength(password: str) -> None:
    """强制密码策略，不合规一律抛出 400。

    该校验与前端无关：即使请求由 Postman/curl 直接发出，也必须被拦截。
    """
    if not password:
        raise BizError("密码不能为空", status_code=400)

    length = len(password)
    if length < settings.PASSWORD_MIN_LENGTH or length > settings.PASSWORD_MAX_LENGTH:
        raise BizError(
            f"密码长度必须为 {settings.PASSWORD_MIN_LENGTH}-{settings.PASSWORD_MAX_LENGTH} 位",
            status_code=400,
        )
    if any(ch.isspace() for ch in password):
        raise BizError("密码不能包含空格", status_code=400)
    if not _HAS_LETTER.search(password) or not _HAS_DIGIT.search(password):
        raise BizError("密码必须同时包含字母和数字", status_code=400)


def validate_username(username: str) -> None:
    """用户名业务规则（注册二次兜底，防止绕过前端）。"""
    if not username:
        raise BizError("用户名不能为空", status_code=400)
    if not USERNAME_PATTERN.match(username):
        raise BizError(USERNAME_RULE, status_code=400)


def validate_amount(amount: Decimal) -> None:
    """金额业务规则：必须为正数，且最多两位小数、不超过字段上限。"""
    if amount is None:
        raise BizError("金额不能为空", status_code=400)
    if not amount.is_finite():
        raise BizError("金额格式非法", status_code=400)
    if amount <= 0:
        raise BizError("金额必须大于 0", status_code=400)
    if amount > MAX_AMOUNT:
        raise BizError(f"金额超出上限（最大 {MAX_AMOUNT}）", status_code=400)
    if -amount.as_tuple().exponent > 2:
        raise BizError("金额最多保留两位小数", status_code=400)
