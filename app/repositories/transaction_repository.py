"""流水及流水统计的数据访问。"""

from __future__ import annotations

import sqlite3
from typing import Iterable


TRANSACTION_SELECT = """
SELECT t.id, t.transaction_type, t.amount_cents, t.category_id,
       t.occurred_on, t.note, t.created_at, t.updated_at,
       c.name AS category_name, c.color AS category_color,
       c.transaction_type AS category_type
FROM transactions t
JOIN categories c ON c.id = t.category_id
"""


class TransactionRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def get(self, transaction_id: int):
        return self.connection.execute(
            TRANSACTION_SELECT + " WHERE t.id = ?", (transaction_id,)
        ).fetchone()

    def list(
        self,
        *,
        keyword: str | None,
        start_date: str | None,
        end_date: str | None,
        types: list[str],
        category_ids: list[int],
        page: int,
        page_size: int,
    ) -> tuple[list, int]:
        conditions: list[str] = []
        params: list[object] = []
        if keyword:
            conditions.append("(t.note LIKE ? COLLATE NOCASE OR c.name LIKE ? COLLATE NOCASE)")
            pattern = f"%{keyword}%"
            params.extend([pattern, pattern])
        if start_date:
            conditions.append("t.occurred_on >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("t.occurred_on <= ?")
            params.append(end_date)
        if types:
            conditions.append(f"t.transaction_type IN ({','.join('?' for _ in types)})")
            params.extend(types)
        if category_ids:
            conditions.append(f"t.category_id IN ({','.join('?' for _ in category_ids)})")
            params.extend(category_ids)
        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        total = self.connection.execute(
            "SELECT COUNT(*) FROM transactions t JOIN categories c ON c.id=t.category_id" + where,
            params,
        ).fetchone()[0]
        rows = self.connection.execute(
            TRANSACTION_SELECT
            + where
            + " ORDER BY t.occurred_on DESC, t.id DESC LIMIT ? OFFSET ?",
            [*params, page_size, (page - 1) * page_size],
        ).fetchall()
        return rows, total

    def create(self, data: dict, timestamp: str):
        cursor = self.connection.execute(
            """
            INSERT INTO transactions
                (transaction_type, amount_cents, category_id, occurred_on, note, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["transaction_type"],
                data["amount_cents"],
                data["category_id"],
                data["occurred_on"],
                data["note"],
                timestamp,
                timestamp,
            ),
        )
        return self.get(cursor.lastrowid)

    def create_many(self, items: Iterable[dict], timestamp: str):
        return [self.create(item, timestamp) for item in items]

    def update(self, transaction_id: int, data: dict, timestamp: str):
        cursor = self.connection.execute(
            """
            UPDATE transactions
            SET transaction_type=?, amount_cents=?, category_id=?, occurred_on=?, note=?, updated_at=?
            WHERE id=?
            """,
            (
                data["transaction_type"], data["amount_cents"], data["category_id"],
                data["occurred_on"], data["note"], timestamp, transaction_id,
            ),
        )
        return self.get(transaction_id) if cursor.rowcount else None

    def delete(self, transaction_id: int) -> bool:
        cursor = self.connection.execute("DELETE FROM transactions WHERE id=?", (transaction_id,))
        return cursor.rowcount > 0

    def summary(self, start_date: str, end_date: str):
        return self.connection.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN transaction_type='income' THEN amount_cents END), 0) AS income,
                COALESCE(SUM(CASE WHEN transaction_type='expense' THEN amount_cents END), 0) AS expense
            FROM transactions WHERE occurred_on BETWEEN ? AND ?
            """,
            (start_date, end_date),
        ).fetchone()

    def expense_categories(self, start_date: str, end_date: str):
        return self.connection.execute(
            """
            SELECT c.id AS category_id, c.name AS category_name, c.color AS category_color,
                   c.transaction_type AS category_type, SUM(t.amount_cents) AS amount_cents
            FROM transactions t JOIN categories c ON c.id=t.category_id
            WHERE t.transaction_type='expense' AND t.occurred_on BETWEEN ? AND ?
            GROUP BY c.id, c.name, c.color, c.transaction_type
            ORDER BY amount_cents DESC, c.id ASC
            """,
            (start_date, end_date),
        ).fetchall()

    def expense_used_by_category(self, start_date: str, end_date: str) -> dict[int, int]:
        rows = self.connection.execute(
            """
            SELECT category_id, SUM(amount_cents) AS used
            FROM transactions
            WHERE transaction_type='expense' AND occurred_on BETWEEN ? AND ?
            GROUP BY category_id
            """,
            (start_date, end_date),
        ).fetchall()
        return {row["category_id"]: row["used"] for row in rows}

