"""用户相关的请求 / 响应模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, StringConstraints

USERNAME_PATTERN = r"^[A-Za-z0-9_]{3,20}$"
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$"

# 用户名格式（长度 3-20 / 仅字母数字下划线）属于「结构 / 格式」校验，
# 由 Pydantic 拦截并返回 422；业务层另有一份兜底校验（见 validators.validate_username）。
UsernameField = Annotated[
    str,
    StringConstraints(strip_whitespace=True, pattern=USERNAME_PATTERN, max_length=20),
]

# 密码这里刻意不加长度约束：密码策略属于业务规则，
# 统一交给业务层校验并返回 400（详见 docs/VALIDATION-MATRIX.md）
PasswordField = str


class RegisterRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "username": "zhangsan",
                "password": "Abcd1234",
                "nickname": "张三",
                "email": "zhangsan@example.com",
            }
        },
    )

    username: UsernameField = ...
    password: PasswordField = ...
    nickname: Optional[Annotated[str, StringConstraints(strip_whitespace=True, max_length=50)]] = None
    email: Optional[
        Annotated[
            str,
            StringConstraints(strip_whitespace=True, pattern=EMAIL_PATTERN, max_length=100),
        ]
    ] = None


class LoginRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"example": {"username": "demo", "password": "Demo1234"}},
    )

    username: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    nickname: Optional[str] = None
    email: Optional[str] = None
    created_at: datetime


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 7200
    user: UserOut
