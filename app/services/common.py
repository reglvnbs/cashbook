"""金额、日期和序列化的公共业务函数。"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from .errors import ValidationError

SHANGHAI = ZoneInfo("Asia/Shanghai")
AMOUNT_PATTERN = re.compile(r"^(?:0|[1-9]\d*)(?:\.\d{1,2})?$")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MONTH_PATTERN = re.compile(r"^\d{4}-\d{2}$")


def today() -> date:
    return datetime.now(SHANGHAI).date()


def now_iso() -> str:
    return datetime.now(SHANGHAI).isoformat(timespec="seconds")


def parse_amount(value: object, field: str = "amount") -> int:
    text = str(value).strip() if value is not None else ""
    if not AMOUNT_PATTERN.fullmatch(text):
        raise ValidationError({field: "金额必须大于零且最多两位小数"})
    try:
        amount = Decimal(text)
    except InvalidOperation as exc:
        raise ValidationError({field: "金额格式不正确"}) from exc
    if amount <= 0:
        raise ValidationError({field: "金额必须大于零"})
    cents = int(amount * 100)
    if cents > 9_000_000_000_000_000:
        raise ValidationError({field: "金额过大"})
    return cents


def format_amount(cents: int) -> str:
    return f"{cents / 100:.2f}"


def parse_date(value: object, field: str, *, allow_future: bool = False) -> date:
    text = str(value).strip() if value is not None else ""
    if not DATE_PATTERN.fullmatch(text):
        raise ValidationError({field: "日期格式必须为 YYYY-MM-DD"})
    try:
        result = date.fromisoformat(text)
    except ValueError as exc:
        raise ValidationError({field: "日期无效"}) from exc
    if not allow_future and result > today():
        raise ValidationError({field: "日期不能晚于今天"})
    return result


def parse_month(value: object) -> str:
    text = str(value).strip() if value is not None else ""
    if not MONTH_PATTERN.fullmatch(text):
        raise ValidationError({"month": "月份格式必须为 YYYY-MM"})
    try:
        date.fromisoformat(f"{text}-01")
    except ValueError as exc:
        raise ValidationError({"month": "月份无效"}) from exc
    return text


def category_dict(row) -> dict:
    return {
        "id": row["category_id"] if "category_id" in row.keys() else row["id"],
        "name": row["category_name"] if "category_name" in row.keys() else row["name"],
        "transaction_type": row["category_type"] if "category_type" in row.keys() else row["transaction_type"],
        "color": row["category_color"] if "category_color" in row.keys() else row["color"],
    }


def transaction_dict(row) -> dict:
    category = category_dict(row)
    category.pop("transaction_type", None)
    return {
        "id": row["id"],
        "transaction_type": row["transaction_type"],
        "amount": format_amount(row["amount_cents"]),
        "category": category,
        "occurred_on": row["occurred_on"],
        "note": row["note"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }

