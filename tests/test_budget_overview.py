from __future__ import annotations


def _all_category_budgets(first_amount="100.00"):
    return [
        {"category_id": category_id, "amount": first_amount if category_id == 1 else None}
        for category_id in range(1, 11)
    ]


def test_budget_whole_page_save_and_overview(client, csrf_headers, expense_payload):
    client.post("/api/transactions", json=expense_payload, headers=csrf_headers)
    saved = client.put(
        "/api/budgets/2026-01",
        json={"total_budget": "200.00", "category_budgets": _all_category_budgets()},
        headers=csrf_headers,
    )
    assert saved.status_code == 200
    budget = saved.json["data"]
    assert budget["total_budget"] == {
        "amount": "200.00",
        "used": "32.00",
        "remaining": "168.00",
        "usage_percent": 16.0,
    }
    assert budget["category_budgets"][0]["used"] == "32.00"

    overview = client.get("/api/overview?start_date=2026-01-01&end_date=2026-01-31")
    assert overview.status_code == 200
    data = overview.json["data"]
    assert data["summary"]["expense"] == "32.00"
    assert data["expense_categories"][0]["percentage"] == 100.0
    assert data["budget_summary"]["total_budget"]["used"] == "32.00"


def test_budget_rejects_incomplete_category_set(client, csrf_headers):
    response = client.put(
        "/api/budgets/2026-01",
        json={"total_budget": None, "category_budgets": []},
        headers=csrf_headers,
    )
    assert response.status_code == 400
    assert response.json["error"]["code"] == "VALIDATION_ERROR"

