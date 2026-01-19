"""Tests for Spotify data models."""

from __future__ import annotations

from datetime import datetime, timezone

from src.spotify.models import Album, Artist, Playlist, Track


def test_track_from_api_parses_fields() -> None:
    item = {
        "added_at": "2024-01-01T12:00:00Z",
        "added_by": {"id": "user-123"},
        "track": {
            "id": "track-1",
            "name": "Song",
            "duration_ms": 210000,
            "is_local": False,
            "artists": [{"id": "artist-1", "name": "Artist"}],
            "album": {"id": "album-1", "name": "Album", "release_date": "2023-01-01"},
        },
    }

    track = Track.from_api(item)

    assert track.id == "track-1"
    assert track.name == "Song"
    assert track.duration_ms == 210000
    assert track.added_by == "user-123"
    assert track.is_local is False
    assert track.album == Album(id="album-1", name="Album", release_date="2023-01-01")
    assert track.artists == [Artist(id="artist-1", name="Artist")]
    assert track.added_at == datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)


def test_playlist_from_api_defaults_total() -> None:
    track = Track(
        id="track-1",
        name="Song",
        artists=[Artist(id="artist-1", name="Artist")],
        album=Album(id="album-1", name="Album", release_date=None),
        duration_ms=210000,
        added_at=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        added_by=None,
        is_local=False,
    )
    playlist_data = {
        "id": "playlist-1",
        "name": "Playlist",
        "description": None,
        "owner": {"display_name": "Owner Name", "id": "owner-id"},
        "snapshot_id": "snapshot-1",
        "tracks": {"total": 5},
    }

    playlist = Playlist.from_api(playlist_data, [track])

    assert playlist.id == "playlist-1"
    assert playlist.owner == "Owner Name"
    assert playlist.total_tracks == 5
