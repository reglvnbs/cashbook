"""预算的数据访问。"""

from __future__ import annotations

import sqlite3


class BudgetRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def amounts(self, month: str) -> tuple[int | None, dict[int, int]]:
        rows = self.connection.execute(
            "SELECT category_id, amount_cents FROM budgets WHERE month=?", (month,)
        ).fetchall()
        total = next((row["amount_cents"] for row in rows if row["category_id"] is None), None)
        categories = {
            row["category_id"]: row["amount_cents"]
            for row in rows
            if row["category_id"] is not None
        }
        return total, categories

    def replace_month(
        self,
        month: str,
        total_amount: int | None,
        category_amounts: dict[int, int | None],
        timestamp: str,
    ) -> None:
        self.connection.execute("DELETE FROM budgets WHERE month=?", (month,))
        if total_amount is not None:
            self.connection.execute(
                "INSERT INTO budgets(month, category_id, amount_cents, updated_at) VALUES (?, NULL, ?, ?)",
                (month, total_amount, timestamp),
            )
        self.connection.executemany(
            "INSERT INTO budgets(month, category_id, amount_cents, updated_at) VALUES (?, ?, ?, ?)",
            [
                (month, category_id, amount, timestamp)
                for category_id, amount in category_amounts.items()
                if amount is not None
            ],
        )

