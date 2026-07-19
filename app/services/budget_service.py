from __future__ import annotations

import calendar
from datetime import date
from sqlite3 import Connection

from app.database import transaction
from app.repositories.budget_repository import BudgetRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.transaction_repository import TransactionRepository

from .common import category_dict, format_amount, now_iso, parse_amount, parse_month
from .errors import ValidationError


class BudgetService:
    def __init__(self, connection: Connection) -> None:
        self.connection = connection
        self.repository = BudgetRepository(connection)
        self.categories = CategoryRepository(connection)
        self.transactions = TransactionRepository(connection)

    @staticmethod
    def month_range(month: str) -> tuple[str, str]:
        year, month_number = map(int, month.split("-"))
        last_day = calendar.monthrange(year, month_number)[1]
        return f"{month}-01", date(year, month_number, last_day).isoformat()

    @staticmethod
    def _entry(amount: int | None, used: int) -> dict:
        remaining = amount - used if amount is not None else None
        usage = (
            100.0
            if amount == 0
            else round(used / amount * 100, 2)
            if amount is not None
            else None
        )
        return {
            "amount": format_amount(amount) if amount is not None else None,
            "used": format_amount(used),
            "remaining": format_amount(remaining) if remaining is not None else None,
            "usage_percent": usage,
        }

    @staticmethod
    def _parse_budget_amount(value: object, field: str) -> int | None:
        if value is None or value == "":
            return None
        if str(value).strip() in {"0", "0.0", "0.00"}:
            return 0
        return parse_amount(value, field)

    def get(self, month_value: object, *, used_range: tuple[str, str] | None = None) -> dict:
        month = parse_month(month_value)
        start_date, end_date = used_range or self.month_range(month)
        total_amount, amounts = self.repository.amounts(month)
        used_by_category = self.transactions.expense_used_by_category(start_date, end_date)
        total_used = sum(used_by_category.values())
        categories = []
        for row in self.categories.list("expense"):
            entry = self._entry(amounts.get(row["id"]), used_by_category.get(row["id"], 0))
            entry["category"] = category_dict(row)
            categories.append(entry)
        return {
            "month": month,
            "total_budget": self._entry(total_amount, total_used),
            "category_budgets": categories,
        }

    def save(self, month_value: object, payload: object) -> dict:
        month = parse_month(month_value)
        if not isinstance(payload, dict):
            raise ValidationError({"body": "请求内容必须是 JSON 对象"})
        missing = {"total_budget", "category_budgets"} - set(payload)
        if missing:
            raise ValidationError({name: "此字段必须提交" for name in sorted(missing)})
        total_raw = payload.get("total_budget")
        total_amount = self._parse_budget_amount(total_raw, "total_budget")
        items = payload.get("category_budgets")
        if not isinstance(items, list):
            raise ValidationError({"category_budgets": "必须提交全部分类预算"})
        expense_ids = [row["id"] for row in self.categories.list("expense")]
        values: dict[int, int | None] = {}
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                raise ValidationError({f"category_budgets.{index}": "分类预算无效"})
            try:
                category_id = int(item.get("category_id"))
            except (TypeError, ValueError) as exc:
                raise ValidationError({f"category_budgets.{index}.category_id": "分类无效"}) from exc
            if category_id in values:
                raise ValidationError({"category_budgets": "每个分类只能出现一次"})
            amount = item.get("amount")
            values[category_id] = self._parse_budget_amount(
                amount, f"category_budgets.{index}.amount"
            )
        if set(values) != set(expense_ids):
            raise ValidationError({"category_budgets": "必须包含全部支出分类"})
        with transaction(self.connection):
            self.repository.replace_month(month, total_amount, values, now_iso())
        return self.get(month)
