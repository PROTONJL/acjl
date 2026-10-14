"""FastAPI 依赖：数据库会话、当前登录用户。"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import BizError
from app.core.security import decode_access_token
from app.crud import user as user_crud
from app.db.session import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

# auto_error=False：缺少/格式错误的 Authorization 头由我们自己抛 401，
# 保证错误响应体与全局约定一致
bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="BearerToken",
    description="登录接口返回的 access_token，格式：Bearer <token>",
)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """解析 Bearer Token 并返回当前用户；失败一律 401。"""
    if credentials is None or not credentials.credentials:
        raise BizError("缺少访问令牌，请先登录", status_code=401)

    payload = decode_access_token(credentials.credentials)
    subject = payload.get("sub")
    try:
        user_id = int(subject)
    except (TypeError, ValueError) as exc:
        raise BizError("无效的访问令牌", status_code=401) from exc

    user = user_crud.get_by_id(db, user_id)
    if user is None:
        raise BizError("用户不存在或已被删除", status_code=401)
    if not user.is_active:
        raise BizError("账号已被停用，请联系管理员", status_code=403)
    return user
