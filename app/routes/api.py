from __future__ import annotations

import hmac
import sqlite3

from flask import Blueprint, current_app, jsonify, request, session

from app.database import get_db
from app.repositories.category_repository import CategoryRepository
from app.services.ai_service import AIService
from app.services.budget_service import BudgetService
from app.services.category_service import CategoryService
from app.services.errors import AppError
from app.services.health_service import HealthService
from app.services.overview_service import OverviewService
from app.services.transaction_service import TransactionService

api = Blueprint("api", __name__, url_prefix="/api")


def success(data, status: int = 200):
    return jsonify({"data": data}), status


def _transaction_service() -> TransactionService:
    config = current_app.config["APP_CONFIG"]
    return TransactionService(get_db(), config.transaction_page_size)


@api.before_request
def protect_write_requests():
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return None
    authorization = request.headers.get("Authorization", "")
    is_single_create = request.method == "POST" and request.path == "/api/transactions"
    if authorization and is_single_create:
        config = current_app.config["APP_CONFIG"]
        if not config.cashbook_api_token:
            raise AppError("AUTOMATION_DISABLED", "自动记账接口尚未配置", 503)
        scheme, separator, token = authorization.partition(" ")
        if separator != " " or scheme.lower() != "bearer" or not hmac.compare_digest(
            token, config.cashbook_api_token
        ):
            raise AppError("AUTH_FAILED", "Bearer Token 无效", 401)
        return None
    expected = session.get("csrf_token")
    received = request.headers.get("X-CSRF-Token")
    if not expected or not received or not hmac.compare_digest(expected, received):
        raise AppError("CSRF_FAILED", "请求校验失败，请刷新页面后重试", 403)
    return None


@api.get("/health")
def health():
    try:
        data = HealthService(get_db()).check()
    except sqlite3.Error:
        raise AppError("INTERNAL_ERROR", "数据库不可用", 503)
    return success(data)


@api.get("/categories")
def categories():
    service = CategoryService(CategoryRepository(get_db()))
    return success(service.list(request.args.get("transaction_type")))


@api.get("/overview")
def overview():
    data = OverviewService(get_db()).get(
        request.args.get("start_date"), request.args.get("end_date")
    )
    return success(data)


@api.get("/transactions")
def list_transactions():
    return success(_transaction_service().list(request.args.to_dict()))


@api.get("/transactions/<int:transaction_id>")
def get_transaction(transaction_id: int):
    return success(_transaction_service().get(transaction_id))


@api.post("/transactions")
def create_transaction():
    return success(_transaction_service().create(request.get_json(silent=True)), 201)


@api.put("/transactions/<int:transaction_id>")
def update_transaction(transaction_id: int):
    return success(
        _transaction_service().update(transaction_id, request.get_json(silent=True))
    )


@api.delete("/transactions/<int:transaction_id>")
def delete_transaction(transaction_id: int):
    return success(_transaction_service().delete(transaction_id))


@api.post("/transactions/batch")
def batch_transactions():
    return success(_transaction_service().create_batch(request.get_json(silent=True)), 201)


@api.post("/ai/parse")
def parse_ai():
    config = current_app.config["APP_CONFIG"]
    service = AIService(
        get_db(),
        api_key=config.deepseek_api_key,
        api_url=config.deepseek_api_url,
        model=config.deepseek_model,
        timeout=config.deepseek_timeout,
    )
    return success(service.parse(request.get_json(silent=True)))


@api.get("/budgets/<month>")
def get_budget(month: str):
    return success(BudgetService(get_db()).get(month))


@api.put("/budgets/<month>")
def save_budget(month: str):
    return success(BudgetService(get_db()).save(month, request.get_json(silent=True)))
