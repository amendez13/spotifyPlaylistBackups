"""Dropbox authentication helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional, cast

import yaml

import dropbox
from dropbox.oauth import DropboxOAuth2FlowNoRedirect
from src.config import Settings, load_settings
from src.config.settings import CONFIG_PATH_ENV, DEFAULT_CONFIG_PATH

DROPBOX_SCOPES = [
    "files.content.write",
    "files.content.read",
]


def _get_config_path() -> Path:
    return Path(os.getenv(CONFIG_PATH_ENV, str(DEFAULT_CONFIG_PATH)))


def _load_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    except yaml.YAMLError as exc:
        raise RuntimeError(f"Failed to parse configuration file: {path}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"Configuration file must contain a YAML mapping: {path}")
    return data


def _save_refresh_token(refresh_token: str, path: Path) -> None:
    config = _load_config(path)
    dropbox_config = config.get("dropbox")
    if not isinstance(dropbox_config, dict):
        dropbox_config = {}
        config["dropbox"] = dropbox_config
    dropbox_config["refresh_token"] = refresh_token
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(config, handle, sort_keys=False)


def _build_flow(settings: Settings) -> DropboxOAuth2FlowNoRedirect:
    return DropboxOAuth2FlowNoRedirect(
        consumer_key=settings.dropbox_app_key,
        consumer_secret=settings.dropbox_app_secret,
        token_access_type="offline",
        scope=DROPBOX_SCOPES,
        use_pkce=True,
    )


def start_auth_flow(settings: Settings) -> str:
    """Start OAuth flow and return the authorization URL."""
    flow = _build_flow(settings)
    return cast(str, flow.start())


def finish_auth_flow(auth_code: str, settings: Settings) -> None:
    """Complete OAuth flow, persist refresh token to config file."""
    if not auth_code.strip():
        raise RuntimeError("Dropbox authorization failed: no authorization code provided.")
    flow = _build_flow(settings)
    try:
        result = flow.finish(auth_code.strip())
    except Exception as exc:  # pragma: no cover - defensive guard
        raise RuntimeError("Dropbox authorization failed: unable to exchange code.") from exc
    refresh_token = getattr(result, "refresh_token", None)
    if not refresh_token:
        raise RuntimeError("Dropbox authorization failed: refresh token missing.")
    _save_refresh_token(refresh_token, _get_config_path())


def is_authenticated(settings: Optional[Settings] = None) -> bool:
    """Check if a refresh token is available."""
    active_settings = settings or load_settings()
    return bool(active_settings.dropbox_refresh_token)


def get_dropbox_client(settings: Settings) -> dropbox.Dropbox:
    """Get an authenticated Dropbox client, prompting for auth if needed."""
    if not settings.dropbox_refresh_token:
        raise RuntimeError("Dropbox refresh token missing. Run the Dropbox authorization flow first.")
    return dropbox.Dropbox(
        oauth2_refresh_token=settings.dropbox_refresh_token,
        app_key=settings.dropbox_app_key,
        app_secret=settings.dropbox_app_secret,
    )
