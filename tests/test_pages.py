from __future__ import annotations


def test_all_pages_have_required_structure(client):
    overview = client.get("/")
    transactions = client.get("/transactions")
    budget = client.get("/budget")
    assert overview.status_code == transactions.status_code == budget.status_code == 200
    assert 'class="sidebar"' in overview.text
    assert 'class="mobile-nav"' in overview.text
    assert "AI 记账" in overview.text and "记一笔" in overview.text
    assert "transaction-filters" in transactions.text
    assert "budget-content" in budget.text


def test_health_and_categories(client):
    assert client.get("/api/health").json == {"data": {"status": "ok", "database": "ok"}}
    categories = client.get("/api/categories?transaction_type=expense").json["data"]
    assert len(categories) == 10
    assert categories[0] == {
        "id": 1,
        "name": "餐饮",
        "transaction_type": "expense",
        "color": "#C77956",
    }

