"""Spotify authentication helpers."""

from __future__ import annotations

import webbrowser
from pathlib import Path
from typing import Optional, cast

import spotipy
from spotipy.cache_handler import CacheFileHandler
from spotipy.oauth2 import SpotifyOAuth

from src.config import Settings, load_settings

SPOTIFY_SCOPES = (
    "playlist-read-private",
    "playlist-read-collaborative",
    "user-library-read",
)
AUTH_PROMPT = "Paste the full redirect URL from Spotify: "


def _build_cache_handler(settings: Settings) -> CacheFileHandler:
    cache_path = Path(settings.token_storage_path)
    if cache_path.parent != Path("."):
        cache_path.parent.mkdir(parents=True, exist_ok=True)
    return CacheFileHandler(cache_path=str(cache_path))


def _build_oauth(settings: Settings) -> SpotifyOAuth:
    cache_handler = _build_cache_handler(settings)
    return SpotifyOAuth(
        client_id=settings.spotify_client_id,
        client_secret=settings.spotify_client_secret,
        redirect_uri=settings.spotify_redirect_uri,
        scope=" ".join(SPOTIFY_SCOPES),
        cache_handler=cache_handler,
        open_browser=False,
    )


def _request_user_token(oauth: SpotifyOAuth) -> dict[str, object]:
    auth_url = oauth.get_authorize_url()
    webbrowser.open(auth_url, new=2, autoraise=True)
    redirect_response = input(AUTH_PROMPT).strip()
    if not redirect_response:
        raise RuntimeError("Spotify authorization cancelled: no redirect URL provided.")

    code = oauth.parse_response_code(redirect_response)
    if not code:
        raise RuntimeError("Spotify authorization failed: unable to parse authorization code.")

    token_info = cast(Optional[dict[str, object]], oauth.get_access_token(code, as_dict=True, check_cache=False))
    if not token_info:
        raise RuntimeError("Spotify authorization failed: token response was empty.")
    return token_info


def is_authenticated(settings: Optional[Settings] = None) -> bool:
    """Check if a valid Spotify token is cached."""
    active_settings = settings or load_settings()
    oauth = _build_oauth(active_settings)
    token_info = oauth.get_cached_token()
    if not token_info:
        return False
    try:
        return oauth.validate_token(token_info) is not None
    except Exception:
        return False


def get_spotify_client(settings: Settings) -> spotipy.Spotify:
    """Get an authenticated Spotify client, prompting for auth if needed."""
    oauth = _build_oauth(settings)
    token_info = oauth.get_cached_token()
    if token_info:
        token_info = oauth.validate_token(token_info)
    if not token_info:
        token_info = _request_user_token(oauth)
    if not token_info:
        raise RuntimeError("Spotify authorization failed: no token available.")
    return spotipy.Spotify(auth_manager=oauth)
