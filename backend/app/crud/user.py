"""用户数据访问。"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User


def get_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.get(User, user_id)


def get_by_username(db: Session, username: str) -> Optional[User]:
    return db.scalar(select(User).where(User.username == username))


def get_by_email(db: Session, email: str) -> Optional[User]:
    return db.scalar(select(User).where(User.email == email))


def create(
    db: Session,
    *,
    username: str,
    password: str,
    nickname: Optional[str] = None,
    email: Optional[str] = None,
) -> User:
    """创建用户。密码只以 bcrypt 哈希形式落库。"""
    user = User(
        username=username,
        nickname=nickname,
        email=email,
        password_hash=hash_password(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
