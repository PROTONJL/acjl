"""pytest 公共夹具。

说明：自测默认使用 SQLite 内存库，**不依赖外部 MySQL**，方便随时回归；
但业务代码本身完全跑在 MySQL 上（连接信息见 backend/.env）。
需要针对真实 MySQL 回归时，请启动服务后用 Apifox/Postman 按 docs/API.md 验证。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# 必须在导入 app 之前设置，避免测试误连业务库
os.environ.setdefault("DB_NAME", "ledger_test")
os.environ.setdefault("JWT_SECRET_KEY", "pytest-only-secret-key-0123456789abcdef")
# 自测时不探测真实数据库，避免噪音日志
os.environ.setdefault("STARTUP_DB_CHECK", "false")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, delete  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.api.deps import get_current_user  # noqa: E402,F401 (确保模块被加载)
from app.crud.category import ensure_preset_exists  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.seed_data import PRESET_CATEGORIES  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Category, Transaction, User  # noqa: E402,F401

TEST_DATABASE_URL = "sqlite+pysqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    bind=test_engine, autocommit=False, autoflush=False, expire_on_commit=False
)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def _prepare_database():
    Base.metadata.create_all(bind=test_engine)
    with TestingSessionLocal() as db:
        ensure_preset_exists(db, PRESET_CATEGORIES)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(autouse=True)
def _clean_data():
    """每个用例结束后清理业务数据，保留系统预置分类。"""
    yield
    with TestingSessionLocal() as db:
        db.execute(delete(Transaction))
        db.execute(delete(Category).where(Category.user_id.isnot(None)))
        db.execute(delete(User))
        db.commit()


@pytest.fixture()
def client():
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers(client):
    """注册并登录一个测试用户，返回可直接使用的认证请求头。"""

    def _make(username: str = "tester01", password: str = "Abcd1234") -> dict:
        client.post(
            "/api/v1/auth/register",
            json={"username": username, "password": password},
        )
        response = client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password},
        )
        token = response.json()["data"]["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _make


@pytest.fixture()
def category_ids(client, auth_headers):
    """取一个支出分类 id 与一个收入分类 id。"""
    headers = auth_headers()
    payload = client.get("/api/v1/categories", headers=headers).json()["data"]
    expense = next(item for item in payload if item["type"] == "expense")
    income = next(item for item in payload if item["type"] == "income")
    return {"expense": expense["id"], "income": income["id"], "headers": headers}
