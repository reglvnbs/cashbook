"""应用配置加载与校验。"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping


class ConfigError(ValueError):
    """配置内容无效。"""


@dataclass(frozen=True, slots=True)
class AppConfig:
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    database_path: str = "data/cashbook.db"
    log_level: str = "INFO"
    log_console: bool = True
    log_file: str = "data/logs/cashbook.log"
    log_max_bytes: int = 5 * 1024 * 1024
    transaction_page_size: int = 20
    deepseek_api_url: str = "https://api.deepseek.com/chat/completions"
    deepseek_model: str = "deepseek-chat"
    deepseek_timeout: int = 20
    secret_key: str | None = None
    deepseek_api_key: str | None = None
    cashbook_api_token: str | None = None
    testing: bool = False

    _SCHEMA = {
        "server": {"host": "str", "port": "int"},
        "database": {"path": "str"},
        "logging": {
            "level": "str",
            "console": "bool",
            "file": "str",
            "max_bytes": "int",
        },
        "transactions": {"page_size": "int"},
        "deepseek": {"api_url": "str", "model": "str", "timeout": "int"},
    }

    _FIELD_NAMES = {
        ("server", "host"): "server_host",
        ("server", "port"): "server_port",
        ("database", "path"): "database_path",
        ("logging", "level"): "log_level",
        ("logging", "console"): "log_console",
        ("logging", "file"): "log_file",
        ("logging", "max_bytes"): "log_max_bytes",
        ("transactions", "page_size"): "transaction_page_size",
        ("deepseek", "api_url"): "deepseek_api_url",
        ("deepseek", "model"): "deepseek_model",
        ("deepseek", "timeout"): "deepseek_timeout",
    }

    _ENV_FIELDS = {
        "CASHBOOK_SERVER_HOST": ("server_host", "str"),
        "CASHBOOK_SERVER_PORT": ("server_port", "int"),
        "CASHBOOK_DATABASE_PATH": ("database_path", "str"),
        "CASHBOOK_LOG_LEVEL": ("log_level", "str"),
        "CASHBOOK_LOG_CONSOLE": ("log_console", "bool"),
        "CASHBOOK_LOG_FILE": ("log_file", "str"),
        "CASHBOOK_LOG_MAX_BYTES": ("log_max_bytes", "int"),
        "CASHBOOK_PAGE_SIZE": ("transaction_page_size", "int"),
        "DEEPSEEK_API_URL": ("deepseek_api_url", "str"),
        "DEEPSEEK_MODEL": ("deepseek_model", "str"),
        "DEEPSEEK_TIMEOUT": ("deepseek_timeout", "int"),
        "SECRET_KEY": ("secret_key", "str"),
        "DEEPSEEK_API_KEY": ("deepseek_api_key", "str"),
        "CASHBOOK_API_TOKEN": ("cashbook_api_token", "str"),
    }

    @classmethod
    def from_file(
        cls,
        path: str | os.PathLike[str] = "config.json",
        *,
        environ: Mapping[str, str] | None = None,
        overrides: Mapping[str, Any] | None = None,
    ) -> "AppConfig":
        values: dict[str, Any] = {}
        config_path = Path(path)
        if config_path.exists():
            try:
                raw = json.loads(config_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ConfigError(f"无法读取配置文件: {exc}") from exc
            if not isinstance(raw, dict):
                raise ConfigError("配置文件根节点必须是对象")
            unknown_groups = set(raw) - set(cls._SCHEMA)
            if unknown_groups:
                raise ConfigError(f"未知配置分组: {', '.join(sorted(unknown_groups))}")
            for group, items in raw.items():
                if not isinstance(items, dict):
                    raise ConfigError(f"配置分组 {group} 必须是对象")
                unknown_items = set(items) - set(cls._SCHEMA[group])
                if unknown_items:
                    raise ConfigError(
                        f"未知配置项: {group}.{', '.join(sorted(unknown_items))}"
                    )
                for name, descriptor in items.items():
                    if not isinstance(descriptor, dict):
                        raise ConfigError(f"配置项 {group}.{name} 必须是对象")
                    expected_type = cls._SCHEMA[group][name]
                    if descriptor.get("type") != expected_type or "value" not in descriptor:
                        raise ConfigError(
                            f"配置项 {group}.{name} 必须包含 type={expected_type} 和 value"
                        )
                    values[cls._FIELD_NAMES[(group, name)]] = cls._convert(
                        descriptor["value"], expected_type, f"{group}.{name}"
                    )

        env = os.environ if environ is None else environ
        for env_name, (field, value_type) in cls._ENV_FIELDS.items():
            if env_name in env and env[env_name] != "":
                values[field] = cls._convert(env[env_name], value_type, env_name)

        if overrides:
            normalized = {key.lower(): value for key, value in overrides.items()}
            allowed = set(cls.__dataclass_fields__) - {"_SCHEMA", "_FIELD_NAMES", "_ENV_FIELDS"}
            unknown = set(normalized) - allowed
            if unknown:
                raise ConfigError(f"未知测试配置项: {', '.join(sorted(unknown))}")
            values.update(normalized)

        return cls(**values)._validated()

    @staticmethod
    def _convert(value: Any, value_type: str, name: str) -> Any:
        if value_type == "str":
            if not isinstance(value, str) or not value.strip():
                raise ConfigError(f"配置项 {name} 必须是非空字符串")
            return value.strip()
        if value_type == "int":
            if isinstance(value, bool):
                raise ConfigError(f"配置项 {name} 必须是整数")
            try:
                return int(value)
            except (TypeError, ValueError) as exc:
                raise ConfigError(f"配置项 {name} 必须是整数") from exc
        if value_type == "bool":
            if isinstance(value, bool):
                return value
            if isinstance(value, str) and value.lower() in {"true", "1", "yes"}:
                return True
            if isinstance(value, str) and value.lower() in {"false", "0", "no"}:
                return False
            raise ConfigError(f"配置项 {name} 必须是布尔值")
        raise ConfigError(f"不支持的配置类型: {value_type}")

    def _validated(self) -> "AppConfig":
        if not 1 <= self.server_port <= 65535:
            raise ConfigError("server.port 必须在 1 到 65535 之间")
        if self.log_level.upper() not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ConfigError("logging.level 无效")
        if self.log_max_bytes <= 0:
            raise ConfigError("logging.max_bytes 必须大于零")
        if not 1 <= self.transaction_page_size <= 100:
            raise ConfigError("transactions.page_size 必须在 1 到 100 之间")
        if self.deepseek_timeout <= 0:
            raise ConfigError("deepseek.timeout 必须大于零")
        if not self.secret_key:
            raise ConfigError("必须通过环境变量 SECRET_KEY 提供请求防护密钥")
        return replace(self, log_level=self.log_level.upper())

    def as_flask_config(self) -> dict[str, Any]:
        return {
            "APP_CONFIG": self,
            "SECRET_KEY": self.secret_key,
            "TESTING": self.testing,
            "JSON_AS_ASCII": False,
        }

    @classmethod
    def export_template(cls) -> dict[str, dict[str, dict[str, Any]]]:
        defaults = cls()
        descriptions = {
            ("server", "host"): "服务监听地址",
            ("server", "port"): "服务监听端口，范围 1-65535",
            ("database", "path"): "SQLite 数据库路径",
            ("logging", "level"): "日志级别",
            ("logging", "console"): "是否输出控制台日志",
            ("logging", "file"): "文件日志路径",
            ("logging", "max_bytes"): "单个日志文件轮转大小（字节）",
            ("transactions", "page_size"): "流水列表每页数量，范围 1-100",
            ("deepseek", "api_url"): "DeepSeek Chat Completions API 地址",
            ("deepseek", "model"): "DeepSeek 模型名称",
            ("deepseek", "timeout"): "DeepSeek 请求超时（秒）",
        }
        result: dict[str, dict[str, dict[str, Any]]] = {}
        for group, items in cls._SCHEMA.items():
            result[group] = {}
            for name, value_type in items.items():
                result[group][name] = {
                    "desc": descriptions[(group, name)],
                    "type": value_type,
                    "value": getattr(defaults, cls._FIELD_NAMES[(group, name)]),
                }
        return result
