from __future__ import annotations

from datetime import date
from sqlite3 import Connection

from app.repositories.transaction_repository import TransactionRepository

from .budget_service import BudgetService
from .common import category_dict, format_amount, parse_date, today
from .errors import ValidationError


class OverviewService:
    def __init__(self, connection: Connection) -> None:
        self.transactions = TransactionRepository(connection)
        self.budgets = BudgetService(connection)

    def get(self, start_value: str | None, end_value: str | None) -> dict:
        if bool(start_value) != bool(end_value):
            raise ValidationError({"date_range": "开始日期和结束日期必须同时提供"})
        if start_value and end_value:
            start = parse_date(start_value, "start_date")
            end = parse_date(end_value, "end_date")
        else:
            end = today()
            start = date(end.year, end.month, 1)
        if start > end:
            raise ValidationError({"end_date": "结束日期不能早于开始日期"})
        summary = self.transactions.summary(start.isoformat(), end.isoformat())
        expense = summary["expense"]
        categories = []
        for row in self.transactions.expense_categories(start.isoformat(), end.isoformat()):
            category = category_dict(row)
            category.pop("transaction_type", None)
            categories.append(
                {
                    "category": category,
                    "amount": format_amount(row["amount_cents"]),
                    "percentage": round(row["amount_cents"] / expense * 100, 2),
                }
            )
        same_month = start.year == end.year and start.month == end.month
        budget = (
            self.budgets.get(start.strftime("%Y-%m"), used_range=(start.isoformat(), end.isoformat()))
            if same_month
            else None
        )
        return {
            "date_range": {"start_date": start.isoformat(), "end_date": end.isoformat()},
            "summary": {
                "income": format_amount(summary["income"]),
                "expense": format_amount(expense),
                "balance": format_amount(summary["income"] - expense),
            },
            "expense_categories": categories,
            "budget_summary": budget,
        }

