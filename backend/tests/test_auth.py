"""认证接口用例：注册、登录、鉴权与密码策略（后端强制校验）。"""

from __future__ import annotations

import pytest

WEAK_PASSWORDS = [
    ("123456", "长度不足"),
    ("abcdefgh", "缺少数字"),
    ("12345678", "缺少字母"),
    ("Abcd 1234", "包含空格"),
    ("Ab1", "长度不足"),
    ("Abcdefg12345678901234", "长度超限"),
]


def test_register_success(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "zhangsan", "password": "Abcd1234", "nickname": "张三"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["code"] == 201
    assert body["data"]["username"] == "zhangsan"
    # 响应体绝不能泄漏密码或哈希
    assert "password" not in body["data"]
    assert "password_hash" not in body["data"]


@pytest.mark.parametrize("password,reason", WEAK_PASSWORDS)
def test_weak_password_rejected_with_400(client, password, reason):
    """绕过前端直接调接口时，弱密码必须被后端拦截（400）。"""
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "weakuser", "password": password},
    )
    assert response.status_code == 400, reason
    assert response.json()["code"] == 400
    assert response.json()["data"] is None


def test_invalid_username_returns_422(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "ab", "password": "Abcd1234"},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["errors"][0]["field"] == "body.username"


def test_missing_field_returns_422(client):
    response = client.post("/api/v1/auth/register", json={"username": "zhangsan"})
    assert response.status_code == 422
    assert any(item["field"] == "body.password" for item in response.json()["errors"])


def test_unknown_field_returns_422(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "zhangsan", "password": "Abcd1234", "is_admin": True},
    )
    assert response.status_code == 422


def test_password_wrong_type_returns_422(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "zhangsan", "password": 12345678},
    )
    assert response.status_code == 422


def test_duplicate_username_returns_409(client):
    payload = {"username": "zhangsan", "password": "Abcd1234"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409


def test_login_success_and_me(client):
    client.post(
        "/api/v1/auth/register",
        json={"username": "lisi", "password": "Abcd1234"},
    )
    response = client.post(
        "/api/v1/auth/login", json={"username": "lisi", "password": "Abcd1234"}
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0

    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["data"]["username"] == "lisi"


def test_login_wrong_password_returns_401(client):
    client.post(
        "/api/v1/auth/register",
        json={"username": "lisi", "password": "Abcd1234"},
    )
    response = client.post(
        "/api/v1/auth/login", json={"username": "lisi", "password": "Wrong1234"}
    )
    assert response.status_code == 401


def test_login_unknown_user_returns_401_with_same_message(client):
    """避免账号枚举：用户不存在与密码错误的提示必须一致。"""
    client.post(
        "/api/v1/auth/register",
        json={"username": "lisi", "password": "Abcd1234"},
    )
    unknown = client.post(
        "/api/v1/auth/login", json={"username": "nobody", "password": "Abcd1234"}
    )
    wrong = client.post(
        "/api/v1/auth/login", json={"username": "lisi", "password": "Wrong1234"}
    )
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["message"] == wrong.json()["message"]


def test_me_without_token_returns_401(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_with_invalid_token_returns_401(client):
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


def test_password_hash_is_bcrypt(client):
    """落库的必须是 bcrypt 哈希，不是明文。"""
    from sqlalchemy import select

    from app.models import User
    from tests.conftest import TestingSessionLocal

    client.post(
        "/api/v1/auth/register",
        json={"username": "hashcheck", "password": "Abcd1234"},
    )
    with TestingSessionLocal() as db:
        user = db.execute(
            select(User).where(User.username == "hashcheck")
        ).scalar_one()
        assert user.password_hash != "Abcd1234"
        assert user.password_hash.startswith("$2")
