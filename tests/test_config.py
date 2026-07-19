from __future__ import annotations

import json

import pytest

from app.config import AppConfig, ConfigError


def test_config_template_and_environment_priority(tmp_path):
    path = tmp_path / "config.json"
    template = AppConfig.export_template()
    template["server"]["port"]["value"] = 8100
    path.write_text(json.dumps(template), encoding="utf-8")
    config = AppConfig.from_file(
        path,
        environ={"CASHBOOK_SERVER_PORT": "8200", "SECRET_KEY": "env-secret"},
        overrides={"SERVER_PORT": 8300},
    )
    assert isinstance(config, AppConfig)
    assert config.server_port == 8300
    assert config.secret_key == "env-secret"


def test_unknown_config_fails_at_startup(tmp_path):
    path = tmp_path / "config.json"
    path.write_text('{"unknown": {}}', encoding="utf-8")
    with pytest.raises(ConfigError, match="未知配置分组"):
        AppConfig.from_file(path, environ={})


def test_secret_key_must_come_from_runtime_environment(tmp_path):
    with pytest.raises(ConfigError, match="SECRET_KEY"):
        AppConfig.from_file(tmp_path / "missing.json", environ={})
