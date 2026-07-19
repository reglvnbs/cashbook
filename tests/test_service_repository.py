from __future__ import annotations

import sqlite3

import pytest

from app.database import get_db
from app.repositories.transaction_repository import TransactionRepository
from app.services.transaction_service import TransactionService


def test_service_validates_category_type_and_repository_queries(app, expense_payload):
    with app.app_context():
        service = TransactionService(get_db(), page_size=20)
        with pytest.raises(Exception) as error:
            service.create({**expense_payload, "category_id": 11})
        assert "分类与收支类型不一致" in str(error.value.fields)

        service.create(expense_payload)
        rows, total = TransactionRepository(get_db()).list(
            keyword="午饭",
            start_date="2026-01-01",
            end_date="2026-01-31",
            types=["expense"],
            category_ids=[1],
            page=1,
            page_size=20,
        )
        assert total == 1 and rows[0]["note"] == "午饭"


def test_database_trigger_rejects_category_type_mismatch(app):
    with app.app_context(), pytest.raises(sqlite3.IntegrityError):
        get_db().execute(
            """
            INSERT INTO transactions
              (transaction_type, amount_cents, category_id, occurred_on, note, created_at, updated_at)
            VALUES ('expense', 100, 11, '2026-01-01', '', '2026-01-01T00:00:00+08:00', '2026-01-01T00:00:00+08:00')
            """
        )

