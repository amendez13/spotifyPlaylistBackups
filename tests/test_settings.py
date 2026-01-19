"""Tests for configuration settings."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest
import yaml
from pydantic import ValidationError

from src.config.settings import CONFIG_PATH_ENV, Settings

ENV_KEYS = [
    "SPOTIFY_CLIENT_ID",
    "SPOTIFY_CLIENT_SECRET",
    "SPOTIFY_REDIRECT_URI",
    "DROPBOX_APP_KEY",
    "DROPBOX_APP_SECRET",
    "DROPBOX_REFRESH_TOKEN",
    "BACKUP_FOLDER",
    "CSV_DELIMITER",
    "TOKEN_STORAGE_PATH",
    CONFIG_PATH_ENV,
]


def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def _write_yaml(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


def test_settings_load_from_yaml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    config_path = tmp_path / "config.yaml"
    _write_yaml(
        config_path,
        {
            "spotify": {
                "client_id": "yaml-client-id",
                "client_secret": "yaml-client-secret",
            },
            "dropbox": {
                "app_key": "yaml-app-key",
                "app_secret": "yaml-app-secret",
            },
            "backup": {
                "folder": "/backups",
                "csv_delimiter": ";",
            },
            "tokens": {"storage_path": "config/token-cache.json"},
        },
    )

    monkeypatch.setenv(CONFIG_PATH_ENV, str(config_path))
    settings = Settings()

    assert settings.spotify_client_id == "yaml-client-id"
    assert settings.spotify_client_secret == "yaml-client-secret"
    assert settings.dropbox_app_key == "yaml-app-key"
    assert settings.dropbox_app_secret == "yaml-app-secret"
    assert settings.backup_folder == "/backups"
    assert settings.csv_delimiter == ";"
    assert settings.token_storage_path == "config/token-cache.json"


def test_env_overrides_yaml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    config_path = tmp_path / "config.yaml"
    _write_yaml(
        config_path,
        {
            "spotify": {
                "client_id": "yaml-client-id",
                "client_secret": "yaml-client-secret",
            },
            "dropbox": {
                "app_key": "yaml-app-key",
                "app_secret": "yaml-app-secret",
            },
        },
    )

    monkeypatch.setenv(CONFIG_PATH_ENV, str(config_path))
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "env-client-id")
    monkeypatch.setenv("DROPBOX_APP_SECRET", "env-app-secret")

    settings = Settings()

    assert settings.spotify_client_id == "env-client-id"
    assert settings.dropbox_app_secret == "env-app-secret"
    assert settings.spotify_client_secret == "yaml-client-secret"
    assert settings.dropbox_app_key == "yaml-app-key"


def test_missing_required_fields_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    config_path = tmp_path / "config.yaml"
    _write_yaml(config_path, {})

    monkeypatch.setenv(CONFIG_PATH_ENV, str(config_path))

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    message = str(exc_info.value)
    assert "SPOTIFY_CLIENT_ID" in message
    assert "DROPBOX_APP_KEY" in message
