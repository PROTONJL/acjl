"""安全相关工具：bcrypt 密码哈希、JWT 签发与校验。

密码存储策略（**后端强制，绝不信任前端**）：
  1. 明文密码只在校验瞬间存在于内存，绝不落库、绝不写日志；
  2. 使用 bcrypt 随机盐哈希（cost=12），同一密码每次哈希结果都不同；
  3. 校验使用 ``bcrypt.checkpw``，恒定时间比较，避免时序攻击。
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import bcrypt
import jwt

from app.core.config import settings
from app.core.exceptions import BizError

logger = logging.getLogger(__name__)

BCRYPT_ROUNDS = 12
# bcrypt 算法本身只接受前 72 字节，超长输入必须显式拒绝而不是静默截断
BCRYPT_MAX_BYTES = 72


def hash_password(plain_password: str) -> str:
    """使用 bcrypt 加盐哈希密码。"""
    raw = plain_password.encode("utf-8")
    if len(raw) > BCRYPT_MAX_BYTES:
        raise BizError(f"密码长度超出安全上限（最多 {BCRYPT_MAX_BYTES} 字节）", status_code=400)
    return bcrypt.hashpw(raw, bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """校验明文密码与哈希是否匹配，任何异常都视为校验失败。"""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(
    subject: str | int,
    expires_minutes: Optional[int] = None,
) -> Tuple[str, int]:
    """签发 JWT，返回 ``(token, 有效期秒数)``。"""
    minutes = expires_minutes or settings.JWT_EXPIRE_MINUTES
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=minutes)
    payload: Dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, minutes * 60


def decode_access_token(token: str) -> Dict[str, Any]:
    """解析 JWT，失败时抛出 401 业务异常。"""
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise BizError("登录状态已过期，请重新登录", status_code=401) from exc
    except jwt.InvalidTokenError as exc:
        raise BizError("无效的访问令牌", status_code=401) from exc
