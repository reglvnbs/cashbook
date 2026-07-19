from __future__ import annotations

import sqlite3


class HealthRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def check(self) -> bool:
        row = self.connection.execute("SELECT 1 AS healthy").fetchone()
        return bool(row and row["healthy"] == 1)

