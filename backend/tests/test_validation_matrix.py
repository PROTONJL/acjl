"""校验责任矩阵的回归用例。

这些用例专门覆盖「绕过前端直接调接口」的场景，用来证明后端防御有效，
与 docs/VALIDATION-MATRIX.md 中的每一行一一对应。
"""

from __future__ import annotations

import pytest


def _payload(category_ids, **overrides):
    data = {
        "type": "expense",
        "amount": "10.00",
        "category_id": category_ids["expense"],
        "occurred_at": "2026-10-14",
    }
    data.update(overrides)
    return data


# ---------------------------------------------------------------- 请求体结构


def test_empty_body_returns_422(client):
    response = client.post("/api/v1/auth/register", json={})
    assert response.status_code == 422
    fields = {item["field"] for item in response.json()["errors"]}
    assert fields == {"body.username", "body.password"}


def test_non_json_body_returns_422(client):
    response = client.post(
        "/api/v1/auth/register",
        content="username=zhangsan",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert response.json()["errors"][0]["type"] == "json_invalid"


def test_confirm_password_is_not_part_of_api(client):
    """前端做的「两次密码一致」校验没有对应后端字段，多传会直接 422。"""
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "zhangsan", "password": "Abcd1234", "confirm_password": "Abcd1234"},
    )
    assert response.status_code == 422
    assert response.json()["errors"][0]["type"] == "extra_forbidden"


def test_missing_token_before_any_business_logic(client):
    """鉴权先于业务校验：未登录时即使参数也非法，也应先返回 401。"""
    response = client.post("/api/v1/transactions", json={})
    assert response.status_code == 401


# ---------------------------------------------------------------- 金额边界


@pytest.mark.parametrize(
    "amount,expected_status,keyword",
    [
        ("0", 400, "金额必须大于 0"),
        ("-0.01", 400, "金额必须大于 0"),
        ("-100", 400, "金额必须大于 0"),
        ("0.001", 400, "两位小数"),
        ("10.999", 400, "两位小数"),
        ("abc", 422, "请求参数校验失败"),
        ("10,5", 422, "请求参数校验失败"),
        ("", 422, "请求参数校验失败"),
        (None, 422, "请求参数校验失败"),
        (True, 422, "请求参数校验失败"),
        ("1234567890123", 422, "请求参数校验失败"),
        ("9999999999.999", 422, "请求参数校验失败"),
    ],
)
def test_amount_boundary_matrix(client, category_ids, amount, expected_status, keyword):
    response = client.post(
        "/api/v1/transactions",
        json=_payload(category_ids, amount=amount),
        headers=category_ids["headers"],
    )
    assert response.status_code == expected_status
    assert keyword in response.json()["message"]


def test_amount_max_value_is_accepted(client, category_ids):
    """DECIMAL(12,2) 的边界值应当被接受。"""
    response = client.post(
        "/api/v1/transactions",
        json=_payload(category_ids, amount="9999999999.99"),
        headers=category_ids["headers"],
    )
    assert response.status_code == 201
    assert response.json()["data"]["amount"] == "9999999999.99"


def test_amount_two_decimals_is_preserved(client, category_ids):
    """前端限制两位小数，后端也要正确归一化（10 与 10.5 都存成两位）。"""
    for raw, expected in [("10", "10.00"), (10.5, "10.50"), ("0.01", "0.01")]:
        response = client.post(
            "/api/v1/transactions",
            json=_payload(category_ids, amount=raw),
            headers=category_ids["headers"],
        )
        assert response.status_code == 201
        assert response.json()["data"]["amount"] == expected


# ---------------------------------------------------------------- 文本长度


def test_remark_too_long_returns_422(client, category_ids):
    response = client.post(
        "/api/v1/transactions",
        json=_payload(category_ids, remark="备" * 256),
        headers=category_ids["headers"],
    )
    assert response.status_code == 422
    assert response.json()["errors"][0]["type"] == "string_too_long"


def test_remark_is_trimmed(client, category_ids):
    response = client.post(
        "/api/v1/transactions",
        json=_payload(category_ids, remark="  午餐  "),
        headers=category_ids["headers"],
    )
    assert response.json()["data"]["remark"] == "午餐"


# ---------------------------------------------------------------- 路径与查询参数


def test_non_numeric_path_param_returns_422(client, category_ids):
    response = client.get("/api/v1/transactions/abc", headers=category_ids["headers"])
    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "path.transaction_id"


@pytest.mark.parametrize(
    "params,field",
    [
        ({"page": "abc"}, "query.page"),
        ({"page": 0}, "query.page"),
        ({"page_size": 0}, "query.page_size"),
        ({"page_size": 101}, "query.page_size"),
        ({"page_size": "big"}, "query.page_size"),
        ({"sort_by": "remark"}, "query.sort_by"),
        ({"order": "up"}, "query.order"),
        ({"type": "transfer"}, "query.type"),
        ({"start_date": "2026-13-01"}, "query.start_date"),
        ({"category_id": "abc"}, "query.category_id"),
        ({"keyword": "к" * 51}, "query.keyword"),
    ],
)
def test_query_param_matrix(client, category_ids, params, field):
    response = client.get("/api/v1/transactions", params=params, headers=category_ids["headers"])
    assert response.status_code == 422
    assert field in {item["field"] for item in response.json()["errors"]}


# ---------------------------------------------------------------- 业务规则


def test_soft_deleted_record_stays_in_database(client, category_ids):
    """软删除必须在库里可追溯（is_deleted=1），而不是物理删除。"""
    from sqlalchemy import select

    from app.models import Transaction
    from tests.conftest import TestingSessionLocal

    headers = category_ids["headers"]
    tx_id = client.post(
        "/api/v1/transactions", json=_payload(category_ids), headers=headers
    ).json()["data"]["id"]
    assert client.delete(f"/api/v1/transactions/{tx_id}", headers=headers).status_code == 204

    with TestingSessionLocal() as db:
        row = db.execute(select(Transaction).where(Transaction.id == tx_id)).scalar_one()
        assert row.is_deleted is True


def test_summary_excludes_deleted_records(client, category_ids):
    headers = category_ids["headers"]
    tx_id = client.post(
        "/api/v1/transactions", json=_payload(category_ids, amount="100.00"), headers=headers
    ).json()["data"]["id"]
    assert client.get("/api/v1/transactions/summary", headers=headers).json()["data"][
        "total_expense"
    ] == "100.00"

    client.delete(f"/api/v1/transactions/{tx_id}", headers=headers)
    data = client.get("/api/v1/transactions/summary", headers=headers).json()["data"]
    assert data["total_expense"] == "0.00"
    assert data["balance"] == "0.00"
