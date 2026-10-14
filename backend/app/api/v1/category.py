"""分类接口。"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.exceptions import BizError
from app.crud import category as category_crud
from app.db.session import get_db
from app.models.enums import TransactionType
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate
from app.schemas.common import ApiResponse, success

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/categories", tags=["分类"])


@router.get(
    "",
    response_model=ApiResponse[List[CategoryOut]],
    summary="分类列表",
    description="返回「系统预置分类 + 当前用户自定义分类」，可按收支类型过滤。",
)
def list_categories(
    type: Optional[TransactionType] = Query(None, description="income / expense"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    categories = category_crud.list_categories(db, current_user.id, type)
    return success([CategoryOut.model_validate(item) for item in categories])


@router.post(
    "",
    response_model=ApiResponse[CategoryOut],
    status_code=status.HTTP_201_CREATED,
    summary="新建自定义分类",
    description="同名（同类型）自定义分类返回 409；与系统预置分类重名同样返回 409。",
)
def create_category(
    payload: CategoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if category_crud.name_exists(db, current_user.id, payload.name, payload.type):
        raise BizError("分类名称已存在", status_code=409)
    visible = category_crud.list_categories(db, current_user.id, payload.type)
    if any(item.user_id is None and item.name == payload.name for item in visible):
        raise BizError("分类名称与系统预置分类重复，请换一个名称", status_code=409)

    category = category_crud.create(
        db,
        user_id=current_user.id,
        name=payload.name,
        tx_type=payload.type,
        icon=payload.icon,
        sort_order=payload.sort_order,
    )
    logger.info("新建分类 | user_id=%s | category_id=%s", current_user.id, category.id)
    return success(CategoryOut.model_validate(category), message="创建成功", code=201)


@router.put(
    "/{category_id}",
    response_model=ApiResponse[CategoryOut],
    summary="修改自定义分类",
    description="只能修改自己创建的分类：系统预置分类返回 403，别人的分类返回 404。不支持修改 type。",
)
def update_category(
    category_id: int,
    payload: CategoryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    accessible = category_crud.get_accessible(db, category_id, current_user.id)
    if accessible is None:
        raise BizError("分类不存在", status_code=404)
    if accessible.user_id is None:
        raise BizError("系统预置分类不允许修改", status_code=403)

    values = payload.model_dump(exclude_unset=True, exclude_none=True)
    if not values:
        raise BizError("没有需要更新的字段", status_code=400)
    if "name" in values and category_crud.name_exists(
        db, current_user.id, values["name"], accessible.type, exclude_id=category_id
    ):
        raise BizError("分类名称已存在", status_code=409)

    category = category_crud.update(db, accessible, values)
    logger.info("修改分类 | user_id=%s | category_id=%s", current_user.id, category_id)
    return success(CategoryOut.model_validate(category), message="更新成功")


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="删除自定义分类",
    description="系统预置分类返回 403；分类下仍有未删除的记账记录时返回 400。",
)
def delete_category(
    category_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    accessible = category_crud.get_accessible(db, category_id, current_user.id)
    if accessible is None:
        raise BizError("分类不存在", status_code=404)
    if accessible.user_id is None:
        raise BizError("系统预置分类不允许删除", status_code=403)

    used = category_crud.count_transactions(db, category_id)
    if used:
        raise BizError(f"该分类下还有 {used} 条记账记录，请先删除或调整这些记录", status_code=400)

    category_crud.delete(db, accessible)
    logger.info("删除分类 | user_id=%s | category_id=%s", current_user.id, category_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
