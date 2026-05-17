"""Tests for Dropbox authentication helpers."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from src.config.settings import Settings
from src.dropbox import auth as auth_module


class FakeFlow:
    def __init__(self, refresh_token: str | None = "refresh-token") -> None:
        self._refresh_token = refresh_token
        self.started = False

    def start(self) -> str:
        self.started = True
        return "https://dropbox.example/auth"

    def finish(self, _code: str) -> SimpleNamespace:
        return SimpleNamespace(refresh_token=self._refresh_token)


def _settings(refresh_token: str | None = "refresh-token") -> Settings:
    return Settings.model_validate(
        {
            "SPOTIFY_CLIENT_ID": "spotify-id",
            "SPOTIFY_CLIENT_SECRET": "spotify-secret",
            "DROPBOX_APP_KEY": "dropbox-key",
            "DROPBOX_APP_SECRET": "dropbox-secret",
            "DROPBOX_REFRESH_TOKEN": refresh_token,
        }
    )


def test_start_auth_flow_returns_url(monkeypatch: pytest.MonkeyPatch) -> None:
    flow = FakeFlow()
    monkeypatch.setattr(auth_module, "_build_flow", lambda _settings: flow)
    url = auth_module.start_auth_flow(_settings())
    assert url == "https://dropbox.example/auth"
    assert flow.started is True


def test_finish_auth_flow_saves_refresh_token(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "config.yaml"
    monkeypatch.setenv(auth_module.CONFIG_PATH_ENV, str(config_path))
    monkeypatch.setattr(auth_module, "_build_flow", lambda _settings: FakeFlow("saved-token"))

    auth_module.finish_auth_flow("auth-code", _settings())

    saved = yaml.safe_load(config_path.read_text())
    assert saved["dropbox"]["refresh_token"] == "saved-token"


def test_finish_auth_flow_requires_code() -> None:
    with pytest.raises(RuntimeError, match="no authorization code provided"):
        auth_module.finish_auth_flow("", _settings())


def test_finish_auth_flow_requires_refresh_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth_module, "_build_flow", lambda _settings: FakeFlow(None))
    with pytest.raises(RuntimeError, match="refresh token missing"):
        auth_module.finish_auth_flow("auth-code", _settings())


def test_get_dropbox_client_requires_token() -> None:
    with pytest.raises(RuntimeError, match="refresh token missing"):
        auth_module.get_dropbox_client(_settings(refresh_token=None))


def test_get_dropbox_client_uses_refresh_token(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    def fake_client(**kwargs: str) -> str:
        captured.update(kwargs)
        return "client"

    monkeypatch.setattr(auth_module.dropbox, "Dropbox", fake_client)
    client = auth_module.get_dropbox_client(_settings())
    assert client == "client"
    assert captured["oauth2_refresh_token"] == "refresh-token"
    assert captured["app_key"] == "dropbox-key"
    assert captured["app_secret"] == "dropbox-secret"


def test_is_authenticated_checks_refresh_token() -> None:
    assert auth_module.is_authenticated(_settings()) is True
    assert auth_module.is_authenticated(_settings(refresh_token=None)) is False


def test_load_config_reads_mapping(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("dropbox:\n  refresh_token: saved\n", encoding="utf-8")
    data = auth_module._load_config(config_path)
    assert data["dropbox"]["refresh_token"] == "saved"


def test_build_flow_returns_instance() -> None:
    flow = auth_module._build_flow(_settings())
    assert flow.consumer_key == "dropbox-key"
