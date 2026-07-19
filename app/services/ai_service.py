"""DeepSeek 自然语言记账解析。"""

from __future__ import annotations

import json
from sqlite3 import Connection
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.repositories.category_repository import CategoryRepository

from .common import format_amount, today
from .errors import AppError, ValidationError
from .transaction_service import TransactionService


class AIService:
    def __init__(
        self,
        connection: Connection,
        *,
        api_key: str | None,
        api_url: str,
        model: str,
        timeout: int,
    ) -> None:
        self.connection = connection
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.timeout = timeout

    def parse(self, payload: object) -> dict:
        if not isinstance(payload, dict) or not isinstance(payload.get("text"), str):
            raise ValidationError({"text": "请输入要识别的记账内容"})
        text = payload["text"].strip()
        if not 1 <= len(text) <= 1000:
            raise ValidationError({"text": "内容长度必须在 1 至 1000 个字符之间"})
        if not self.api_key:
            raise AppError("AI_NOT_CONFIGURED", "AI 记账尚未配置", 503)

        categories = CategoryRepository(self.connection).list()
        category_lines = "\n".join(
            f"- {row['id']}: {row['name']} ({row['transaction_type']})" for row in categories
        )
        prompt = f"""你是账本流水解析器。今天是 {today().isoformat()}（Asia/Shanghai）。
固定分类如下：
{category_lines}

把用户文字解析为 1 至 20 笔流水。未说明日期时使用今天；相对日期以今天为基准。
只返回 JSON，不要 Markdown、解释或额外字段，格式严格为：
{{"transactions":[{{"transaction_type":"expense","amount":"32.00","category_id":1,"occurred_on":"{today().isoformat()}","note":"午饭"}}]}}
用户文字：{text}"""
        body = json.dumps(
            {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "response_format": {"type": "json_object"},
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request = Request(
            self.api_url,
            data=body,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                response_data = json.loads(response.read().decode("utf-8"))
            content = response_data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
        except (HTTPError, URLError, TimeoutError) as exc:
            raise AppError("AI_SERVICE_ERROR", "AI 服务暂时不可用", 503) from exc
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise AppError("AI_INVALID_RESPONSE", "AI 返回了无法使用的结果", 503) from exc

        if not isinstance(parsed, dict) or set(parsed) != {"transactions"}:
            raise AppError("AI_INVALID_RESPONSE", "AI 返回了无法使用的结果", 503)
        items = parsed["transactions"]
        if not isinstance(items, list) or not 1 <= len(items) <= 20:
            raise AppError("AI_INVALID_RESPONSE", "AI 返回的流水数量无效", 503)
        validator = TransactionService(self.connection, page_size=20)
        drafts = []
        try:
            for item in items:
                if not isinstance(item, dict) or set(item) != {
                    "transaction_type", "amount", "category_id", "occurred_on", "note"
                }:
                    raise ValidationError({"transactions": "字段不完整"})
                valid = validator._validate(item)
                drafts.append(
                    {
                        "transaction_type": valid["transaction_type"],
                        "amount": format_amount(valid["amount_cents"]),
                        "category_id": valid["category_id"],
                        "occurred_on": valid["occurred_on"],
                        "note": valid["note"],
                    }
                )
        except ValidationError as exc:
            raise AppError("AI_INVALID_RESPONSE", "AI 返回了无效的流水内容", 503) from exc
        return {"drafts": drafts}

