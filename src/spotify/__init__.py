"""Spotify integration package."""

from .auth import SPOTIFY_SCOPES, get_spotify_client, is_authenticated
from .client import SpotifyClient
from .models import Album, Artist, Playlist, Track

__all__ = [
    "Album",
    "Artist",
    "Playlist",
    "SPOTIFY_SCOPES",
    "SpotifyClient",
    "Track",
    "get_spotify_client",
    "is_authenticated",
]
