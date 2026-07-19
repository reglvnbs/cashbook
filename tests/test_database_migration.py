from __future__ import annotations

import sqlite3

from app import create_app
from app.database import get_db


def test_existing_budget_table_is_migrated_for_zero_budget(tmp_path):
    database_path = tmp_path / "legacy.db"
    connection = sqlite3.connect(database_path)
    connection.executescript(
        """
        CREATE TABLE categories (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            transaction_type TEXT NOT NULL,
            color TEXT NOT NULL,
            UNIQUE (transaction_type, name)
        );
        CREATE TABLE budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month TEXT NOT NULL,
            category_id INTEGER REFERENCES categories(id),
            amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
            updated_at TEXT NOT NULL,
            UNIQUE (month, category_id)
        );
        INSERT INTO categories VALUES (1, '餐饮', 'expense', '#C77956');
        INSERT INTO budgets (month, category_id, amount_cents, updated_at)
        VALUES ('2026-01', 1, 10000, '2026-01-01T00:00:00+08:00');
        """
    )
    connection.close()

    app = create_app(
        {
            "CONFIG_PATH": str(tmp_path / "missing.json"),
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "DATABASE_PATH": str(database_path),
            "LOG_FILE": str(tmp_path / "migration.log"),
            "LOG_CONSOLE": False,
        }
    )
    with app.app_context():
        database = get_db()
        assert database.execute(
            "SELECT amount_cents FROM budgets WHERE month='2026-01'"
        ).fetchone()["amount_cents"] == 10000
        database.execute(
            "INSERT INTO budgets (month, category_id, amount_cents, updated_at) VALUES (?, NULL, 0, ?)",
            ("2026-02", "2026-01-01T00:00:00+08:00"),
        )
