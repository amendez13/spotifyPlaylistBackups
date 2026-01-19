"""Tests for Spotify authentication helpers."""

from __future__ import annotations

import builtins
from pathlib import Path
from typing import Optional

import pytest

from src.config.settings import Settings
from src.spotify import auth as auth_module


class FakeOAuth:
    """Simple OAuth test double."""

    def __init__(
        self,
        cached_token: Optional[dict[str, object]] = None,
        validated_token: Optional[dict[str, object]] = None,
        access_token: Optional[dict[str, object]] = None,
        parsed_code: Optional[str] = "auth-code",
    ) -> None:
        self._cached_token = cached_token
        self._validated_token = validated_token
        self._access_token = access_token
        self._parsed_code = parsed_code
        self.authorize_called = False
        self.access_called = False
        self.parse_called_with: Optional[str] = None

    def get_cached_token(self) -> Optional[dict[str, object]]:
        return self._cached_token

    def validate_token(self, token_info: dict[str, object]) -> Optional[dict[str, object]]:
        return self._validated_token

    def get_authorize_url(self) -> str:
        self.authorize_called = True
        return "https://example.com/auth"

    def parse_response_code(self, url: str) -> Optional[str]:
        self.parse_called_with = url
        return self._parsed_code

    def get_access_token(
        self,
        code: Optional[str] = None,
        as_dict: bool = True,
        check_cache: bool = True,
    ) -> Optional[dict[str, object]]:
        self.access_called = True
        return self._access_token


class DummySpotify:
    """Minimal Spotify client stub."""

    def __init__(self, auth_manager: object) -> None:
        self.auth_manager = auth_manager


def _settings() -> Settings:
    return Settings.model_validate(
        {
            "SPOTIFY_CLIENT_ID": "client-id",
            "SPOTIFY_CLIENT_SECRET": "client-secret",
            "SPOTIFY_REDIRECT_URI": "http://localhost:8888/callback",
            "DROPBOX_APP_KEY": "dropbox-key",
            "DROPBOX_APP_SECRET": "dropbox-secret",
            "TOKEN_STORAGE_PATH": ".spotify_token.json",
        }
    )


def test_is_authenticated_false_when_no_token(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeOAuth(cached_token=None)
    monkeypatch.setattr(auth_module, "_build_oauth", lambda _: fake)
    assert auth_module.is_authenticated(_settings()) is False


def test_is_authenticated_true_with_valid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    token = {"access_token": "token"}
    fake = FakeOAuth(cached_token=token, validated_token=token)
    monkeypatch.setattr(auth_module, "_build_oauth", lambda _: fake)
    assert auth_module.is_authenticated(_settings()) is True


def test_get_spotify_client_uses_cached_token(monkeypatch: pytest.MonkeyPatch) -> None:
    token = {"access_token": "token"}
    fake = FakeOAuth(cached_token=token, validated_token=token)
    monkeypatch.setattr(auth_module, "_build_oauth", lambda _: fake)
    monkeypatch.setattr(auth_module.spotipy, "Spotify", DummySpotify)

    def fail_open(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("browser should not open for cached token")

    monkeypatch.setattr(auth_module.webbrowser, "open", fail_open)

    client = auth_module.get_spotify_client(_settings())
    assert isinstance(client, DummySpotify)
    assert client.auth_manager is fake


def test_get_spotify_client_prompts_for_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeOAuth(cached_token=None, access_token={"access_token": "new-token"})
    monkeypatch.setattr(auth_module, "_build_oauth", lambda _: fake)
    monkeypatch.setattr(auth_module.spotipy, "Spotify", DummySpotify)

    opened: dict[str, str] = {}

    def record_open(url: str, **_kwargs: object) -> None:
        opened["url"] = url

    monkeypatch.setattr(auth_module.webbrowser, "open", record_open)
    monkeypatch.setattr(builtins, "input", lambda _prompt: "http://localhost/callback?code=auth-code")

    client = auth_module.get_spotify_client(_settings())
    assert isinstance(client, DummySpotify)
    assert fake.authorize_called is True
    assert fake.access_called is True
    assert opened["url"] == "https://example.com/auth"


def test_get_spotify_client_missing_redirect_url(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeOAuth(cached_token=None, access_token={"access_token": "new-token"})
    monkeypatch.setattr(auth_module, "_build_oauth", lambda _: fake)
    monkeypatch.setattr(builtins, "input", lambda _prompt: "")
    monkeypatch.setattr(auth_module.webbrowser, "open", lambda *_args, **_kwargs: None)

    with pytest.raises(RuntimeError, match="no redirect URL provided"):
        auth_module.get_spotify_client(_settings())


def test_get_spotify_client_invalid_code(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeOAuth(cached_token=None, parsed_code=None)
    monkeypatch.setattr(auth_module, "_build_oauth", lambda _: fake)
    monkeypatch.setattr(builtins, "input", lambda _prompt: "http://localhost/callback?error=invalid")
    monkeypatch.setattr(auth_module.webbrowser, "open", lambda *_args, **_kwargs: None)

    with pytest.raises(RuntimeError, match="unable to parse authorization code"):
        auth_module.get_spotify_client(_settings())


def test_request_user_token_empty_response(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeOAuth(cached_token=None, access_token=None)
    monkeypatch.setattr(auth_module.webbrowser, "open", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(builtins, "input", lambda _prompt: "http://localhost/callback?code=auth-code")

    with pytest.raises(RuntimeError, match="token response was empty"):
        auth_module._request_user_token(fake)


def test_get_spotify_client_handles_empty_token(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeOAuth(cached_token=None)
    monkeypatch.setattr(auth_module, "_build_oauth", lambda _: fake)
    monkeypatch.setattr(auth_module, "_request_user_token", lambda _oauth: None)

    with pytest.raises(RuntimeError, match="no token available"):
        auth_module.get_spotify_client(_settings())


def test_is_authenticated_handles_validation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class ExplodingOAuth(FakeOAuth):
        def validate_token(self, token_info: dict[str, object]) -> Optional[dict[str, object]]:
            raise RuntimeError("boom")

    token = {"access_token": "token"}
    fake = ExplodingOAuth(cached_token=token)
    monkeypatch.setattr(auth_module, "_build_oauth", lambda _: fake)
    assert auth_module.is_authenticated(_settings()) is False


def test_build_cache_handler_creates_parent(tmp_path: Path) -> None:
    settings = Settings.model_validate(
        {
            "SPOTIFY_CLIENT_ID": "client-id",
            "SPOTIFY_CLIENT_SECRET": "client-secret",
            "DROPBOX_APP_KEY": "dropbox-key",
            "DROPBOX_APP_SECRET": "dropbox-secret",
            "TOKEN_STORAGE_PATH": str(tmp_path / "nested" / "token.json"),
        }
    )
    cache_handler = auth_module._build_cache_handler(settings)
    assert (tmp_path / "nested").exists()
    assert str(cache_handler.cache_path).endswith("token.json")


def test_build_oauth_returns_instance() -> None:
    oauth = auth_module._build_oauth(_settings())
    assert oauth.client_id == "client-id"
