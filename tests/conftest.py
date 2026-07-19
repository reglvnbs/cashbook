from __future__ import annotations

import pytest

from app import create_app


@pytest.fixture()
def app(tmp_path):
    return create_app(
        {
            "CONFIG_PATH": str(tmp_path / "missing-config.json"),
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "DATABASE_PATH": str(tmp_path / "cashbook.db"),
            "LOG_FILE": str(tmp_path / "cashbook.log"),
            "LOG_CONSOLE": False,
            "CASHBOOK_API_TOKEN": "automation-secret",
            "DEEPSEEK_API_KEY": "deepseek-test-key",
        }
    )


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def csrf_headers(client):
    client.get("/")
    with client.session_transaction() as session:
        token = session["csrf_token"]
    return {"X-CSRF-Token": token}


@pytest.fixture()
def expense_payload():
    return {
        "transaction_type": "expense",
        "amount": "32.00",
        "category_id": 1,
        "occurred_on": "2026-01-15",
        "note": "午饭",
    }

