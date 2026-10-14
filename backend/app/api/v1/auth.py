"""认证接口：注册 / 登录 / 当前用户。"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.exceptions import BizError
from app.core.security import create_access_token, verify_password
from app.core.validators import validate_password_strength, validate_username
from app.crud import user as user_crud
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import ApiResponse, success
from app.schemas.user import LoginRequest, LoginResponse, RegisterRequest, UserOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post(
    "/register",
    response_model=ApiResponse[UserOut],
    status_code=status.HTTP_201_CREATED,
    summary="用户注册",
    description=(
        "注册新用户。**密码策略由后端强制校验**：长度 8-20 位、必须同时包含字母和数字、"
        "不允许空格，不合规返回 400（即使绕过前端直接调用接口也一定被拦截）。"
        "用户名或邮箱重复返回 409。"
    ),
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> dict:
    # 业务层强制校验（400），不依赖任何前端校验
    validate_username(payload.username)
    validate_password_strength(payload.password)

    if user_crud.get_by_username(db, payload.username):
        raise BizError("用户名已存在，请更换后重试", status_code=409)
    if payload.email and user_crud.get_by_email(db, payload.email):
        raise BizError("邮箱已被注册，请更换后重试", status_code=409)

    try:
        user = user_crud.create(
            db,
            username=payload.username,
            password=payload.password,
            nickname=payload.nickname,
            email=payload.email,
        )
    except Exception:
        # 并发下的唯一索引冲突兜底：数据库层是最后一道防线
        db.rollback()
        logger.exception("注册失败：数据库写入异常")
        raise BizError("注册失败，用户名或邮箱可能已存在", status_code=409) from None

    logger.info("用户注册成功 | user_id=%s | username=%s", user.id, user.username)
    return success(UserOut.model_validate(user), message="注册成功", code=201)


@router.post(
    "/login",
    response_model=ApiResponse[LoginResponse],
    summary="用户登录",
    description=(
        "登录成功返回 JWT，后续请求在请求头带上 `Authorization: Bearer <access_token>`。"
        "用户名不存在与密码错误统一返回 401，避免账号枚举。"
    ),
)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> dict:
    user = user_crud.get_by_username(db, payload.username)
    if user is None or not verify_password(payload.password, user.password_hash):
        logger.warning("登录失败 | username=%s | 原因：用户名或密码错误", payload.username)
        raise BizError("用户名或密码错误", status_code=401)
    if not user.is_active:
        raise BizError("账号已被停用，请联系管理员", status_code=403)

    token, expires_in = create_access_token(user.id)
    logger.info("用户登录成功 | user_id=%s | username=%s", user.id, user.username)
    return success(
        LoginResponse(
            access_token=token,
            token_type="bearer",
            expires_in=expires_in,
            user=UserOut.model_validate(user),
        ),
        message="登录成功",
    )


@router.get(
    "/me",
    response_model=ApiResponse[UserOut],
    summary="获取当前登录用户",
    description="用于前端判断登录态；未携带或携带无效 Token 返回 401。",
)
def me(current_user: User = Depends(get_current_user)) -> dict:
    return success(UserOut.model_validate(current_user))
