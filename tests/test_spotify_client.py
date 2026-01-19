"""Tests for Spotify client wrapper."""

from __future__ import annotations

from typing import Any, Dict, List

import pytest
from spotipy.exceptions import SpotifyException

from src.spotify.client import SpotifyClient


class FakeSpotify:
    def __init__(self) -> None:
        self.next_map: Dict[str, Dict[str, Any]] = {}
        self.playlist_pages: List[Dict[str, Any]] = []
        self.track_pages: Dict[str, List[Dict[str, Any]]] = {}

    def current_user_playlists(self, limit: int = 50) -> Dict[str, Any]:
        return self.playlist_pages[0]

    def playlist_items(self, playlist_id: str, limit: int = 100) -> Dict[str, Any]:
        return self.track_pages[playlist_id][0]

    def next(self, response: Dict[str, Any]) -> Dict[str, Any]:
        next_key = response.get("next")
        return self.next_map[next_key]

    def current_user(self) -> Dict[str, Any]:
        return {"id": "user-1"}


def _playlist_item(track_id: str, is_local: bool = False) -> Dict[str, Any]:
    return {
        "added_at": "2024-01-01T12:00:00Z",
        "added_by": {"id": "user-1"},
        "track": {
            "id": track_id,
            "name": f"Track {track_id}",
            "duration_ms": 1000,
            "is_local": is_local,
            "artists": [{"id": "artist-1", "name": "Artist"}],
            "album": {"id": "album-1", "name": "Album", "release_date": "2023-01-01"},
        },
    }


def test_get_playlist_tracks_paginates_and_skips_local() -> None:
    spotify = FakeSpotify()
    spotify.track_pages["playlist-1"] = [
        {
            "items": [_playlist_item("track-1"), _playlist_item("local", is_local=True)],
            "next": "tracks_page_2",
        },
        {"items": [_playlist_item("track-2")], "next": None},
    ]
    spotify.next_map["tracks_page_2"] = spotify.track_pages["playlist-1"][1]

    client = SpotifyClient(spotify)
    tracks = client.get_playlist_tracks("playlist-1")

    assert [track.id for track in tracks] == ["track-1", "track-2"]


def test_get_all_playlists_paginates() -> None:
    spotify = FakeSpotify()
    spotify.playlist_pages = [
        {
            "items": [
                {
                    "id": "playlist-1",
                    "name": "One",
                    "description": None,
                    "owner": {"display_name": "Owner"},
                    "snapshot_id": "snap-1",
                    "tracks": {"total": 1},
                }
            ],
            "next": "playlists_page_2",
        },
        {
            "items": [
                {
                    "id": "playlist-2",
                    "name": "Two",
                    "description": None,
                    "owner": {"display_name": "Owner"},
                    "snapshot_id": "snap-2",
                    "tracks": {"total": 1},
                }
            ],
            "next": None,
        },
    ]
    spotify.next_map["playlists_page_2"] = spotify.playlist_pages[1]
    spotify.track_pages["playlist-1"] = [{"items": [_playlist_item("track-1")], "next": None}]
    spotify.track_pages["playlist-2"] = [{"items": [_playlist_item("track-2")], "next": None}]

    client = SpotifyClient(spotify)
    playlists = client.get_all_playlists()

    assert [playlist.id for playlist in playlists] == ["playlist-1", "playlist-2"]
    assert playlists[0].tracks[0].id == "track-1"


def test_rate_limit_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    spotify = FakeSpotify()
    client = SpotifyClient(spotify, max_retries=2, backoff_factor=1.0)

    calls = {"count": 0}
    sleeps: List[float] = []

    def flaky_call() -> str:
        calls["count"] += 1
        if calls["count"] <= 2:
            raise SpotifyException(429, -1, "rate limited", headers={"Retry-After": "2"})
        return "ok"

    monkeypatch.setattr("time.sleep", lambda seconds: sleeps.append(seconds))

    result = client._request_with_retry(flaky_call)

    assert result == "ok"
    assert sleeps == [2.0, 2.0]
