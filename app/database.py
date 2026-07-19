"""SQLite 连接、初始化和事务管理。"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from flask import current_app, g


def connect_database(path: str) -> sqlite3.Connection:
    database_path = Path(path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path, timeout=10, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    return connection


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        config = current_app.config["APP_CONFIG"]
        g.db = connect_database(config.database_path)
    return g.db


def close_db(_error: BaseException | None = None) -> None:
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def init_database(connection: sqlite3.Connection) -> None:
    migrated = _migrate_zero_budget_support(connection)
    schema_path = Path(__file__).with_name("schema.sql")
    connection.executescript(schema_path.read_text(encoding="utf-8"))
    if migrated:
        current_app.logger.info("数据库结构升级完成: 支持零预算状态")


def _migrate_zero_budget_support(connection: sqlite3.Connection) -> bool:
    row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='budgets'"
    ).fetchone()
    if row is None or "amount_cents > 0" not in (row["sql"] or ""):
        return False
    with transaction(connection):
        connection.execute("DROP INDEX IF EXISTS ux_budgets_total_month")
        connection.execute("ALTER TABLE budgets RENAME TO budgets_before_zero_support")
        connection.execute(
            """
            CREATE TABLE budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month TEXT NOT NULL CHECK (month GLOB '????-??'),
                category_id INTEGER REFERENCES categories(id) ON DELETE RESTRICT,
                amount_cents INTEGER NOT NULL CHECK (amount_cents >= 0),
                updated_at TEXT NOT NULL,
                UNIQUE (month, category_id)
            )
            """
        )
        connection.execute(
            """
            INSERT INTO budgets (id, month, category_id, amount_cents, updated_at)
            SELECT id, month, category_id, amount_cents, updated_at
            FROM budgets_before_zero_support
            """
        )
        connection.execute("DROP TABLE budgets_before_zero_support")
    return True


@contextmanager
def transaction(connection: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    connection.execute("BEGIN IMMEDIATE")
    try:
        yield connection
    except Exception:
        connection.execute("ROLLBACK")
        raise
    else:
        connection.execute("COMMIT")


def init_app(app) -> None:
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_database(get_db())
