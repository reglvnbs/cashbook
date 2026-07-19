"""固定分类的数据访问。"""

from __future__ import annotations

import sqlite3


class CategoryRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def list(self, transaction_type: str | None = None):
        sql = "SELECT id, name, transaction_type, color FROM categories"
        params: list[object] = []
        if transaction_type:
            sql += " WHERE transaction_type = ?"
            params.append(transaction_type)
        return self.connection.execute(sql + " ORDER BY id", params).fetchall()

    def get(self, category_id: int):
        return self.connection.execute(
            "SELECT id, name, transaction_type, color FROM categories WHERE id = ?",
            (category_id,),
        ).fetchone()

