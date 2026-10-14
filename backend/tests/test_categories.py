"""分类用例：预置分类、自定义分类的增删改与权限。"""

from __future__ import annotations


def test_list_categories_contains_presets(client, category_ids):
    response = client.get("/api/v1/categories", headers=category_ids["headers"])
    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) >= 15
    assert all(item["is_system"] for item in items)


def test_create_and_update_and_delete_custom_category(client, category_ids):
    headers = category_ids["headers"]
    created = client.post(
        "/api/v1/categories",
        json={"name": "宠物", "type": "expense", "icon": "🐱"},
        headers=headers,
    )
    assert created.status_code == 201
    category = created.json()["data"]
    assert category["is_system"] is False

    updated = client.put(
        f"/api/v1/categories/{category['id']}",
        json={"name": "宠物用品", "sort_order": 5},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["name"] == "宠物用品"

    assert client.delete(f"/api/v1/categories/{category['id']}", headers=headers).status_code == 204
    assert client.delete(f"/api/v1/categories/{category['id']}", headers=headers).status_code == 404


def test_duplicate_custom_category_returns_409(client, category_ids):
    headers = category_ids["headers"]
    payload = {"name": "宠物", "type": "expense"}
    assert client.post("/api/v1/categories", json=payload, headers=headers).status_code == 201
    assert client.post("/api/v1/categories", json=payload, headers=headers).status_code == 409


def test_category_name_conflicts_with_preset_returns_409(client, category_ids):
    headers = category_ids["headers"]
    response = client.post(
        "/api/v1/categories", json={"name": "餐饮", "type": "expense"}, headers=headers
    )
    assert response.status_code == 409


def test_cannot_modify_or_delete_preset(client, category_ids):
    headers = category_ids["headers"]
    preset_id = category_ids["expense"]
    assert (
        client.put(
            f"/api/v1/categories/{preset_id}", json={"name": "改名"}, headers=headers
        ).status_code
        == 403
    )
    assert (
        client.delete(f"/api/v1/categories/{preset_id}", headers=headers).status_code == 403
    )


def test_delete_category_in_use_returns_400(client, category_ids):
    headers = category_ids["headers"]
    category_id = client.post(
        "/api/v1/categories", json={"name": "宠物", "type": "expense"}, headers=headers
    ).json()["data"]["id"]

    client.post(
        "/api/v1/transactions",
        json={
            "type": "expense",
            "amount": "10.00",
            "category_id": category_id,
            "occurred_at": "2026-10-14",
        },
        headers=headers,
    )

    response = client.delete(f"/api/v1/categories/{category_id}", headers=headers)
    assert response.status_code == 400
    assert "还有 1 条" in response.json()["message"]


def test_category_requires_auth(client):
    assert client.get("/api/v1/categories").status_code == 401


def test_invalid_category_type_returns_422(client, category_ids):
    response = client.post(
        "/api/v1/categories",
        json={"name": "宠物", "type": "transfer"},
        headers=category_ids["headers"],
    )
    assert response.status_code == 422
