"""数据库初始化脚本。

用法（在 ``backend/`` 目录下执行）::

    python -m app.db.init_db              # 建库 + 建表 + 灌预置分类
    python -m app.db.init_db --with-demo  # 额外创建演示账号 demo / Demo1234

脚本是幂等的，可以重复执行。
"""

from __future__ import annotations

import argparse
import logging
import re
import sys

import pymysql
from sqlalchemy import select

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.security import hash_password
from app.db.base import Base
from app.db.seed_data import (
    DEMO_NICKNAME,
    DEMO_PASSWORD,
    DEMO_USERNAME,
    PRESET_CATEGORIES,
)
from app.db.session import SessionLocal, engine

# 导入模型以注册到 Base.metadata
from app.models import Category, Transaction, User  # noqa: F401

logger = logging.getLogger(__name__)

SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9_]+$")


def ensure_database_exists() -> None:
    """连接 MySQL 服务器（不指定库）并创建目标数据库。"""
    db_name = settings.DB_NAME
    if not SAFE_IDENTIFIER.match(db_name):
        raise ValueError(f"非法的数据库名：{db_name}")

    connection = pymysql.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        charset=settings.DB_CHARSET,
        autocommit=True,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        logger.info("数据库已就绪：%s", db_name)
    finally:
        connection.close()


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
    logger.info("数据表已就绪：%s", ", ".join(sorted(Base.metadata.tables)))


def seed_categories() -> int:
    """灌入系统预置分类（幂等：已存在则跳过）。"""
    created = 0
    with SessionLocal() as db:
        existing = {
            (row.name, row.type)
            for row in db.scalars(
                select(Category).where(Category.user_id.is_(None))
            ).all()
        }
        for item in PRESET_CATEGORIES:
            key = (item["name"], item["type"])
            if key in existing:
                continue
            db.add(Category(user_id=None, **item))
            created += 1
        db.commit()
    logger.info("预置分类：新增 %s 条，已跳过 %s 条", created, len(PRESET_CATEGORIES) - created)
    return created


def create_demo_user() -> bool:
    """创建演示账号（已存在则跳过）。"""
    with SessionLocal() as db:
        exists = db.scalar(select(User).where(User.username == DEMO_USERNAME))
        if exists:
            logger.info("演示账号已存在：%s", DEMO_USERNAME)
            return False
        db.add(
            User(
                username=DEMO_USERNAME,
                nickname=DEMO_NICKNAME,
                email=None,
                password_hash=hash_password(DEMO_PASSWORD),
            )
        )
        db.commit()
    logger.info("演示账号已创建：%s / %s", DEMO_USERNAME, DEMO_PASSWORD)
    return True


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    parser = argparse.ArgumentParser(description="初始化个人记账本数据库")
    parser.add_argument("--with-demo", action="store_true", help="创建演示账号 demo/Demo1234")
    parser.add_argument("--skip-create-db", action="store_true", help="跳过建库步骤")
    args = parser.parse_args(argv)

    for warning in settings.startup_warnings():
        logger.warning("配置提醒：%s", warning)

    try:
        if not args.skip_create_db:
            ensure_database_exists()
        create_tables()
        seed_categories()
        if args.with_demo:
            create_demo_user()
    except Exception:
        logger.exception("数据库初始化失败")
        return 1
    logger.info("数据库初始化完成 ✔")
    return 0


if __name__ == "__main__":
    sys.exit(main())
