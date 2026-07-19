"""账本 Flask 应用工厂。"""

from __future__ import annotations

import logging
import secrets
from logging.handlers import RotatingFileHandler
from pathlib import Path

from flask import Flask, jsonify, request, session

from .config import AppConfig
from .database import init_app as init_database
from .routes.api import api
from .routes.pages import pages
from .services.errors import AppError


class _RelativePathFilter(logging.Filter):
    def __init__(self, project_root: Path) -> None:
        super().__init__()
        self.project_root = project_root

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.source_path = str(Path(record.pathname).resolve().relative_to(self.project_root))
        except ValueError:
            record.source_path = record.filename
        return True


def _configure_logging(app: Flask, config: AppConfig) -> None:
    formatter = logging.Formatter(
        "[%(asctime)s][%(levelname)s][%(source_path)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    path_filter = _RelativePathFilter(Path(__file__).resolve().parent.parent)
    handlers: list[logging.Handler] = []
    if config.log_console:
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        console.addFilter(path_filter)
        handlers.append(console)
    if config.log_file:
        log_path = Path(config.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_path, maxBytes=config.log_max_bytes, backupCount=5, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        file_handler.addFilter(path_filter)
        handlers.append(file_handler)
    app.logger.handlers.clear()
    app.logger.setLevel(config.log_level)
    for handler in handlers:
        app.logger.addHandler(handler)


def create_app(test_config: dict | None = None) -> Flask:
    overrides = dict(test_config or {})
    config_path = overrides.pop("CONFIG_PATH", "config.json")
    config = AppConfig.from_file(config_path, overrides=overrides)
    app = Flask(__name__)
    app.config.from_mapping(config.as_flask_config())
    app.json.ensure_ascii = False
    _configure_logging(app, config)
    init_database(app)
    app.register_blueprint(pages)
    app.register_blueprint(api)

    @app.context_processor
    def inject_helpers():
        def csrf_token() -> str:
            if "csrf_token" not in session:
                session["csrf_token"] = secrets.token_urlsafe(32)
            return session["csrf_token"]

        return {"csrf_token": csrf_token}

    @app.errorhandler(AppError)
    def handle_app_error(error: AppError):
        payload = {"code": error.code, "message": error.message}
        if error.fields:
            payload["fields"] = error.fields
        return jsonify({"error": payload}), error.status_code

    @app.errorhandler(404)
    def handle_not_found(_error):
        if request.path.startswith("/api/"):
            return jsonify({"error": {"code": "NOT_FOUND", "message": "资源不存在"}}), 404
        return "页面不存在", 404

    @app.errorhandler(Exception)
    def handle_unexpected(error: Exception):
        app.logger.exception("未处理的服务端错误: %s", type(error).__name__)
        if request.path.startswith("/api/"):
            return jsonify(
                {"error": {"code": "INTERNAL_ERROR", "message": "服务暂时不可用"}}
            ), 500
        return "服务暂时不可用", 500

    app.logger.info("账本应用启动成功")
    return app
