"""Spotify integration package."""

from .auth import SPOTIFY_SCOPES, get_spotify_client, is_authenticated

__all__ = ["SPOTIFY_SCOPES", "get_spotify_client", "is_authenticated"]
