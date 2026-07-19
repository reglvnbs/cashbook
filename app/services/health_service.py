from __future__ import annotations

from sqlite3 import Connection

from app.repositories.health_repository import HealthRepository

from .errors import AppError


class HealthService:
    def __init__(self, connection: Connection) -> None:
        self.repository = HealthRepository(connection)

    def check(self) -> dict[str, str]:
        if not self.repository.check():
            raise AppError("INTERNAL_ERROR", "数据库不可用", 503)
        return {"status": "ok", "database": "ok"}

