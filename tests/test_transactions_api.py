from __future__ import annotations


def test_browser_create_requires_csrf(client, expense_payload):
    response = client.post("/api/transactions", json=expense_payload)
    assert response.status_code == 403
    assert response.json["error"]["code"] == "CSRF_FAILED"


def test_transaction_crud_filter_and_pagination(client, csrf_headers, expense_payload):
    created = client.post("/api/transactions", json=expense_payload, headers=csrf_headers)
    assert created.status_code == 201
    item = created.json["data"]
    assert item["amount"] == "32.00"
    assert item["category"]["name"] == "餐饮"
    transaction_id = item["id"]

    listed = client.get("/api/transactions?keyword=午饭&types=expense&category_ids=1&page=1")
    assert listed.status_code == 200
    assert listed.json["data"]["pagination"]["total_items"] == 1

    updated_payload = {**expense_payload, "amount": "40.50", "note": "聚餐"}
    updated = client.put(
        f"/api/transactions/{transaction_id}", json=updated_payload, headers=csrf_headers
    )
    assert updated.json["data"]["amount"] == "40.50"
    assert updated.json["data"]["note"] == "聚餐"

    deleted = client.delete(f"/api/transactions/{transaction_id}", headers=csrf_headers)
    assert deleted.json == {"data": {"id": transaction_id}}
    assert client.get(f"/api/transactions/{transaction_id}").status_code == 404


def test_validation_and_batch_are_atomic(client, csrf_headers, expense_payload):
    invalid = {**expense_payload, "amount": "1.234"}
    response = client.post(
        "/api/transactions/batch",
        json={"transactions": [expense_payload, invalid]},
        headers=csrf_headers,
    )
    assert response.status_code == 400
    assert client.get("/api/transactions").json["data"]["pagination"]["total_items"] == 0


def test_put_requires_the_complete_transaction_shape(client, csrf_headers, expense_payload):
    created = client.post("/api/transactions", json=expense_payload, headers=csrf_headers)
    transaction_id = created.json["data"]["id"]
    incomplete = {key: value for key, value in expense_payload.items() if key != "note"}
    response = client.put(
        f"/api/transactions/{transaction_id}", json=incomplete, headers=csrf_headers
    )
    assert response.status_code == 400
    assert response.json["error"]["fields"]["note"] == "此字段必须提交"


def test_bearer_token_only_creates_single_transaction(client, expense_payload):
    invalid = client.post(
        "/api/transactions", json=expense_payload, headers={"Authorization": "Bearer wrong"}
    )
    assert invalid.status_code == 401
    created = client.post(
        "/api/transactions",
        json=expense_payload,
        headers={"Authorization": "Bearer automation-secret"},
    )
    assert created.status_code == 201
    assert created.json["data"]["note"] == "午饭"
