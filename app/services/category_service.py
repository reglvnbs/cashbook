from __future__ import annotations

from app.repositories.category_repository import CategoryRepository

from .common import category_dict
from .errors import ValidationError


class CategoryService:
    def __init__(self, repository: CategoryRepository) -> None:
        self.repository = repository

    def list(self, transaction_type: str | None = None) -> list[dict]:
        if transaction_type not in {None, "income", "expense"}:
            raise ValidationError({"transaction_type": "收支类型无效"})
        return [category_dict(row) for row in self.repository.list(transaction_type)]

