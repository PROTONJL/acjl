"""收支明细用例：新增、校验、列表筛选、汇总、修改、删除、数据隔离。"""

from __future__ import annotations

import pytest


def _payload(category_ids, **overrides):
    data = {
        "type": "expense",
        "amount": "25.80",
        "category_id": category_ids["expense"],
        "occurred_at": "2026-10-14",
        "remark": "午餐",
    }
    data.update(overrides)
    return data


def test_create_requires_auth(client):
    response = client.post(
        "/api/v1/transactions",
        json={"type": "expense", "amount": "10.00", "category_id": 1, "occurred_at": "2026-10-14"},
    )
    assert response.status_code == 401


def test_create_success(client, category_ids):
    response = client.post(
        "/api/v1/transactions",
        json=_payload(category_ids),
        headers=category_ids["headers"],
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["amount"] == "25.80"
    assert data["type"] == "expense"
    assert data["category_name"]


@pytest.mark.parametrize(
    "amount,reason",
    [("0", "金额为 0"), ("-100", "金额为负"), ("-0.01", "金额为负"), ("0.00", "金额为 0")],
)
def test_non_positive_amount_returns_400(client, category_ids, amount, reason):
    response = client.post(
        "/api/v1/transactions",
        json=_payload(category_ids, amount=amount),
        headers=category_ids["headers"],
    )
    assert response.status_code == 400, reason
    assert response.json()["code"] == 400
    assert "金额" in response.json()["message"]


def test_amount_more_than_two_decimals_returns_400(client, category_ids):
    response = client.post(
        "/api/v1/transactions",
        json=_payload(category_ids, amount="10.999"),
        headers=category_ids["headers"],
    )
    assert response.status_code == 400
    assert "两位小数" in response.json()["message"]


@pytest.mark.parametrize("amount", ["abc", "10,5", "", True, {"x": 1}])
def test_amount_wrong_type_returns_422(client, category_ids, amount):
    """非法字符（如 "abc"）由 Pydantic 拦截，返回 422 并给出字段明细。"""
    response = client.post(
        "/api/v1/transactions",
        json=_payload(category_ids, amount=amount),
        headers=category_ids["headers"],
    )
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == 422
    assert any(item["field"] == "body.amount" for item in body["errors"])


def test_amount_overflow_returns_422(client, category_ids):
    """超过 DECIMAL(12,2) 上限属于结构问题，返回 422。"""
    response = client.post(
        "/api/v1/transactions",
        json=_payload(category_ids, amount="1234567890123"),
        headers=category_ids["headers"],
    )
    assert response.status_code == 422


def test_invalid_type_returns_422(client, category_ids):
    response = client.post(
        "/api/v1/transactions",
        json=_payload(category_ids, type="transfer"),
        headers=category_ids["headers"],
    )
    assert response.status_code == 422


def test_invalid_date_returns_422(client, category_ids):
    response = client.post(
        "/api/v1/transactions",
        json=_payload(category_ids, occurred_at="2026-13-45"),
        headers=category_ids["headers"],
    )
    assert response.status_code == 422


def test_category_not_exists_returns_400(client, category_ids):
    response = client.post(
        "/api/v1/transactions",
        json=_payload(category_ids, category_id=999999),
        headers=category_ids["headers"],
    )
    assert response.status_code == 400


def test_category_type_mismatch_returns_400(client, category_ids):
    response = client.post(
        "/api/v1/transactions",
        json=_payload(category_ids, type="income"),
        headers=category_ids["headers"],
    )
    assert response.status_code == 400
    assert "不一致" in response.json()["message"]


def test_list_pagination_and_filters(client, category_ids):
    headers = category_ids["headers"]
    client.post(
        "/api/v1/transactions",
        json=_payload(category_ids, amount="10.00", remark="早餐"),
        headers=headers,
    )
    client.post(
        "/api/v1/transactions",
        json=_payload(category_ids, amount="20.00", remark="午餐", occurred_at="2026-10-13"),
        headers=headers,
    )
    client.post(
        "/api/v1/transactions",
        json=_payload(
            category_ids, type="income", category_id=category_ids["income"], amount="5000.00"
        ),
        headers=headers,
    )

    all_page = client.get(
        "/api/v1/transactions", params={"page": 1, "page_size": 10}, headers=headers
    ).json()["data"]
    assert all_page["total"] == 3
    assert all_page["pages"] == 1

    filtered = client.get(
        "/api/v1/transactions",
        params={"type": "income", "page_size": 10},
        headers=headers,
    ).json()["data"]
    assert filtered["total"] == 1
    assert filtered["items"][0]["amount"] == "5000.00"

    by_keyword = client.get(
        "/api/v1/transactions", params={"keyword": "早餐"}, headers=headers
    ).json()["data"]
    assert by_keyword["total"] == 1

    by_date = client.get(
        "/api/v1/transactions",
        params={"start_date": "2026-10-14", "end_date": "2026-10-14"},
        headers=headers,
    ).json()["data"]
    assert by_date["total"] == 2

    paged = client.get(
        "/api/v1/transactions", params={"page": 2, "page_size": 2}, headers=headers
    ).json()["data"]
    assert paged["total"] == 3
    assert len(paged["items"]) == 1


def test_list_invalid_query_returns_422(client, category_ids):
    response = client.get(
        "/api/v1/transactions", params={"page": "abc"}, headers=category_ids["headers"]
    )
    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "query.page"


def test_list_date_range_order_returns_400(client, category_ids):
    response = client.get(
        "/api/v1/transactions",
        params={"start_date": "2026-10-20", "end_date": "2026-10-01"},
        headers=category_ids["headers"],
    )
    assert response.status_code == 400


def test_page_size_limit_returns_422(client, category_ids):
    response = client.get(
        "/api/v1/transactions", params={"page_size": 500}, headers=category_ids["headers"]
    )
    assert response.status_code == 422


def test_summary(client, category_ids):
    headers = category_ids["headers"]
    client.post(
        "/api/v1/transactions", json=_payload(category_ids, amount="30.00"), headers=headers
    )
    client.post(
        "/api/v1/transactions",
        json=_payload(
            category_ids, type="income", category_id=category_ids["income"], amount="1000.00"
        ),
        headers=headers,
    )
    data = client.get("/api/v1/transactions/summary", headers=headers).json()["data"]
    assert data["total_income"] == "1000.00"
    assert data["total_expense"] == "30.00"
    assert data["balance"] == "970.00"
    assert data["income_count"] == 1


def test_update_and_delete(client, category_ids):
    headers = category_ids["headers"]
    created = client.post(
        "/api/v1/transactions", json=_payload(category_ids), headers=headers
    ).json()["data"]
    tx_id = created["id"]

    updated = client.put(
        f"/api/v1/transactions/{tx_id}",
        json={"amount": "99.99", "remark": "改过了"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["amount"] == "99.99"
    assert updated.json()["data"]["remark"] == "改过了"

    assert client.delete(f"/api/v1/transactions/{tx_id}", headers=headers).status_code == 204
    assert client.get(f"/api/v1/transactions/{tx_id}", headers=headers).status_code == 404


def test_update_with_zero_amount_returns_400(client, category_ids):
    headers = category_ids["headers"]
    tx_id = client.post(
        "/api/v1/transactions", json=_payload(category_ids), headers=headers
    ).json()["data"]["id"]
    response = client.put(
        f"/api/v1/transactions/{tx_id}", json={"amount": "0"}, headers=headers
    )
    assert response.status_code == 400


def test_update_empty_body_returns_400(client, category_ids):
    headers = category_ids["headers"]
    tx_id = client.post(
        "/api/v1/transactions", json=_payload(category_ids), headers=headers
    ).json()["data"]["id"]
    response = client.put(f"/api/v1/transactions/{tx_id}", json={}, headers=headers)
    assert response.status_code == 400


def test_data_isolation_between_users(client, category_ids, auth_headers):
    """A 用户的记录，B 用户既查不到也改不了、删不了。"""
    headers_a = category_ids["headers"]
    tx_id = client.post(
        "/api/v1/transactions", json=_payload(category_ids), headers=headers_a
    ).json()["data"]["id"]

    headers_b = auth_headers("tester02")
    assert client.get(f"/api/v1/transactions/{tx_id}", headers=headers_b).status_code == 404
    assert (
        client.put(
            f"/api/v1/transactions/{tx_id}", json={"amount": "1.00"}, headers=headers_b
        ).status_code
        == 404
    )
    assert client.delete(f"/api/v1/transactions/{tx_id}", headers=headers_b).status_code == 404

    list_b = client.get("/api/v1/transactions", headers=headers_b).json()["data"]
    assert list_b["total"] == 0
