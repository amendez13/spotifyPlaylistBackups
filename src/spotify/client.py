"""Spotify API client wrapper."""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List, TypeVar

import spotipy
from spotipy.exceptions import SpotifyException

from src.config import Settings
from src.spotify.auth import get_spotify_client
from src.spotify.models import Playlist, Track

logger = logging.getLogger(__name__)

ResponseT = TypeVar("ResponseT")


class SpotifyClient:
    """Wrap spotipy with pagination and rate limit handling."""

    def __init__(
        self,
        spotify: spotipy.Spotify,
        max_retries: int = 3,
        backoff_factor: float = 1.0,
    ) -> None:
        self._spotify = spotify
        self._max_retries = max_retries
        self._backoff_factor = backoff_factor

    @classmethod
    def from_settings(cls, settings: Settings) -> "SpotifyClient":
        return cls(get_spotify_client(settings))

    def _request_with_retry(self, func: Callable[..., ResponseT], *args: Any, **kwargs: Any) -> ResponseT:
        delay = self._backoff_factor
        for attempt in range(self._max_retries + 1):
            try:
                return func(*args, **kwargs)
            except SpotifyException as exc:
                if exc.http_status != 429 or attempt >= self._max_retries:
                    raise
                retry_after = None
                if exc.headers:
                    retry_after = exc.headers.get("Retry-After")
                sleep_for = delay
                if retry_after:
                    try:
                        sleep_for = max(delay, float(retry_after))
                    except (TypeError, ValueError):
                        sleep_for = delay
                logger.warning("Spotify rate limited. Retrying in %s seconds.", sleep_for)
                time.sleep(sleep_for)
                delay *= 2
        raise RuntimeError("Spotify request failed after retries.")

    def _paginate(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        items = list(response.get("items", []))
        next_url = response.get("next")
        while next_url:
            response = self._request_with_retry(self._spotify.next, response)
            items.extend(response.get("items", []))
            next_url = response.get("next")
        return items

    def get_user_info(self) -> Dict[str, Any]:
        return self._request_with_retry(self._spotify.current_user)

    def get_playlist_tracks(self, playlist_id: str) -> List[Track]:
        response = self._request_with_retry(self._spotify.playlist_items, playlist_id, limit=100)
        items = self._paginate(response)
        tracks: List[Track] = []
        for item in items:
            track_data = item.get("track")
            if not track_data or track_data.get("is_local"):
                continue
            tracks.append(Track.from_api(item))
        return tracks

    def get_all_playlists(self) -> List[Playlist]:
        response = self._request_with_retry(self._spotify.current_user_playlists, limit=50)
        playlists_data = self._paginate(response)
        playlists: List[Playlist] = []
        for playlist in playlists_data:
            tracks = self.get_playlist_tracks(playlist["id"])
            playlists.append(Playlist.from_api(playlist, tracks))
        return playlists
