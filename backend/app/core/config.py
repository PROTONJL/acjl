"""应用配置模块。

所有敏感配置（数据库密码、JWT 密钥等）统一从 ``backend/.env`` 读取，
代码中只保留可安全公开的默认值，严禁硬编码真实密码。
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ 目录（config.py -> core/ -> app/ -> backend/）
BASE_DIR: Path = Path(__file__).resolve().parents[2]
ENV_FILE: Path = BASE_DIR / ".env"


class Settings(BaseSettings):
    """从环境变量 / .env 文件加载的应用配置。"""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---------- 应用 ----------
    APP_NAME: str = "个人记账本"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # ---------- 数据库 ----------
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "ledger"
    DB_CHARSET: str = "utf8mb4"
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 3600

    # ---------- JWT ----------
    JWT_SECRET_KEY: str = "CHANGE_ME_IN_ENV_FILE"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 120

    # ---------- 密码策略（后端强制校验，前端只是体验层） ----------
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_MAX_LENGTH: int = 20

    # ---------- 日志 ----------
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = str(BASE_DIR / "logs")
    LOG_RETENTION_DAYS: int = 7

    # 启动时是否探测数据库连通性（自动化测试环境可关闭，避免噪音日志）
    STARTUP_DB_CHECK: bool = True

    # ---------- CORS ----------
    CORS_ORIGINS: str = "*"

    @property
    def database_url(self) -> str:
        """SQLAlchemy 连接串（含目标库）。"""
        return (
            f"mysql+pymysql://{self.DB_USER}:{quote_plus(self.DB_PASSWORD)}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset={self.DB_CHARSET}"
        )

    @property
    def server_url(self) -> str:
        """不指定数据库的连接串，用于 ``CREATE DATABASE``。"""
        return (
            f"mysql+pymysql://{self.DB_USER}:{quote_plus(self.DB_PASSWORD)}"
            f"@{self.DB_HOST}:{self.DB_PORT}/?charset={self.DB_CHARSET}"
        )

    @property
    def cors_origin_list(self) -> List[str]:
        raw = (self.CORS_ORIGINS or "").strip()
        if not raw or raw == "*":
            return ["*"]
        return [item.strip() for item in raw.split(",") if item.strip()]

    def startup_warnings(self) -> List[str]:
        """启动时的配置体检，返回需要提醒开发者的问题列表。"""
        warnings: List[str] = []
        if self.JWT_SECRET_KEY in {"", "CHANGE_ME_IN_ENV_FILE", "secret"}:
            warnings.append("JWT_SECRET_KEY 仍为默认值，请在 .env 中替换为随机长字符串")
        elif len(self.JWT_SECRET_KEY) < 32:
            warnings.append("JWT_SECRET_KEY 长度小于 32 位，建议使用更长的随机密钥")
        if not self.DB_PASSWORD:
            warnings.append("DB_PASSWORD 为空，请确认 MySQL 账号是否真的免密")
        return warnings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """单例配置对象（带缓存，避免重复解析 .env）。"""
    return Settings()


settings: Settings = get_settings()
