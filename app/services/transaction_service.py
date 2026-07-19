from __future__ import annotations

import math
from sqlite3 import Connection

from app.database import transaction
from app.repositories.category_repository import CategoryRepository
from app.repositories.transaction_repository import TransactionRepository

from .common import now_iso, parse_amount, parse_date, transaction_dict
from .errors import AppError, ValidationError


class TransactionService:
    def __init__(self, connection: Connection, page_size: int) -> None:
        self.connection = connection
        self.repository = TransactionRepository(connection)
        self.categories = CategoryRepository(connection)
        self.page_size = page_size

    def _validate(self, payload: object, *, require_all: bool = False) -> dict:
        if not isinstance(payload, dict):
            raise ValidationError({"body": "请求内容必须是 JSON 对象"})
        fields: dict[str, str] = {}
        if require_all:
            required = {"transaction_type", "amount", "category_id", "occurred_on", "note"}
            for missing in sorted(required - set(payload)):
                fields[missing] = "此字段必须提交"
        transaction_type = payload.get("transaction_type")
        if transaction_type not in {"income", "expense"}:
            fields["transaction_type"] = "收支类型无效"
        try:
            amount_cents = parse_amount(payload.get("amount"))
        except ValidationError as exc:
            fields.update(exc.fields or {})
            amount_cents = 0
        try:
            category_id = int(payload.get("category_id"))
            category = self.categories.get(category_id)
            if category is None:
                fields["category_id"] = "分类不存在"
            elif transaction_type in {"income", "expense"} and category["transaction_type"] != transaction_type:
                fields["category_id"] = "分类与收支类型不一致"
        except (TypeError, ValueError):
            category_id = 0
            fields["category_id"] = "分类无效"
        try:
            occurred_on = parse_date(payload.get("occurred_on"), "occurred_on").isoformat()
        except ValidationError as exc:
            occurred_on = ""
            fields.update(exc.fields or {})
        note_value = payload.get("note", "")
        if not isinstance(note_value, str):
            fields["note"] = "备注必须是文字"
            note = ""
        else:
            note = note_value.strip()
            if len(note) > 200:
                fields["note"] = "备注最多 200 个字符"
        if fields:
            raise ValidationError(fields)
        return {
            "transaction_type": transaction_type,
            "amount_cents": amount_cents,
            "category_id": category_id,
            "occurred_on": occurred_on,
            "note": note,
        }

    def get(self, transaction_id: int) -> dict:
        row = self.repository.get(transaction_id)
        if row is None:
            raise AppError("NOT_FOUND", "流水不存在", 404)
        return transaction_dict(row)

    def list(self, query: dict[str, str]) -> dict:
        keyword = (query.get("keyword") or "").strip() or None
        types = [item for item in (query.get("types") or "").split(",") if item]
        if any(item not in {"income", "expense"} for item in types):
            raise ValidationError({"types": "收支类型筛选无效"})
        raw_ids = [item for item in (query.get("category_ids") or "").split(",") if item]
        try:
            category_ids = [int(item) for item in raw_ids]
            if any(item <= 0 for item in category_ids):
                raise ValueError
        except ValueError as exc:
            raise ValidationError({"category_ids": "分类筛选无效"}) from exc
        start_date = query.get("start_date") or None
        end_date = query.get("end_date") or None
        start = parse_date(start_date, "start_date") if start_date else None
        end = parse_date(end_date, "end_date") if end_date else None
        if start and end and start > end:
            raise ValidationError({"end_date": "结束日期不能早于开始日期"})
        try:
            page = int(query.get("page", "1"))
            if page < 1:
                raise ValueError
        except ValueError as exc:
            raise ValidationError({"page": "页码必须从 1 开始"}) from exc
        rows, total = self.repository.list(
            keyword=keyword,
            start_date=start.isoformat() if start else None,
            end_date=end.isoformat() if end else None,
            types=list(dict.fromkeys(types)),
            category_ids=list(dict.fromkeys(category_ids)),
            page=page,
            page_size=self.page_size,
        )
        return {
            "items": [transaction_dict(row) for row in rows],
            "pagination": {
                "page": page,
                "page_size": self.page_size,
                "total_items": total,
                "total_pages": math.ceil(total / self.page_size) if total else 0,
            },
        }

    def create(self, payload: object) -> dict:
        data = self._validate(payload)
        with transaction(self.connection):
            row = self.repository.create(data, now_iso())
        return transaction_dict(row)

    def create_batch(self, payload: object) -> list[dict]:
        if not isinstance(payload, dict) or not isinstance(payload.get("transactions"), list):
            raise ValidationError({"transactions": "必须提交流水数组"})
        items = payload["transactions"]
        if not 1 <= len(items) <= 20:
            raise ValidationError({"transactions": "一次只能保存 1 至 20 笔流水"})
        validated: list[dict] = []
        for index, item in enumerate(items):
            try:
                validated.append(self._validate(item))
            except ValidationError as exc:
                raise ValidationError(
                    {f"transactions.{index}.{key}": value for key, value in (exc.fields or {}).items()}
                ) from exc
        with transaction(self.connection):
            rows = self.repository.create_many(validated, now_iso())
        return [transaction_dict(row) for row in rows]

    def update(self, transaction_id: int, payload: object) -> dict:
        data = self._validate(payload, require_all=True)
        with transaction(self.connection):
            row = self.repository.update(transaction_id, data, now_iso())
            if row is None:
                raise AppError("NOT_FOUND", "流水不存在", 404)
        return transaction_dict(row)

    def delete(self, transaction_id: int) -> dict:
        with transaction(self.connection):
            if not self.repository.delete(transaction_id):
                raise AppError("NOT_FOUND", "流水不存在", 404)
        return {"id": transaction_id}
