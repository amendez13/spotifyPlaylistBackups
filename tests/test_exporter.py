"""Tests for CSV export helpers."""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

from src.backup.exporter import CSV_FIELDS, generate_filename, playlist_to_csv, tracks_to_csv_rows
from src.spotify.models import Album, Artist, Playlist, Track


def _track(
    track_id: str,
    name: str = "Song",
    artists: list[Artist] | None = None,
) -> Track:
    return Track(
        id=track_id,
        name=name,
        artists=artists or [Artist(id="artist-1", name="Artist")],
        album=Album(id="album-1", name="Album", release_date="2024-01-01"),
        duration_ms=210000,
        added_at=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        added_by="user-1",
        is_local=False,
    )


def test_tracks_to_csv_rows_formats_artists() -> None:
    track = _track(
        "track-1",
        artists=[Artist(id="a1", name="Alpha"), Artist(id="a2", name="Beta")],
    )
    rows = tracks_to_csv_rows([track])

    assert rows[0]["track_id"] == "track-1"
    assert rows[0]["artists"] == "Alpha, Beta"


def test_playlist_to_csv_has_bom_and_header() -> None:
    playlist = Playlist(
        id="playlist-1",
        name="My Playlist",
        description=None,
        owner="owner-1",
        tracks=[_track("track-1")],
        snapshot_id="snap-1",
        total_tracks=1,
    )

    csv_text = playlist_to_csv(playlist)
    assert csv_text.startswith("\ufeff")

    reader = csv.reader(io.StringIO(csv_text.lstrip("\ufeff")))
    header = next(reader)
    assert header == CSV_FIELDS


def test_playlist_to_csv_escapes_special_characters() -> None:
    track = _track(
        "track-1",
        name='Hello, "World"',
        artists=[Artist(id="a1", name="AC/DC")],
    )
    playlist = Playlist(
        id="playlist-1",
        name="My Playlist",
        description=None,
        owner="owner-1",
        tracks=[track],
        snapshot_id="snap-1",
        total_tracks=1,
    )

    csv_text = playlist_to_csv(playlist)
    reader = csv.DictReader(io.StringIO(csv_text.lstrip("\ufeff")))
    row = next(reader)

    assert row["track_name"] == 'Hello, "World"'
    assert row["artists"] == "AC/DC"


def test_generate_filename_sanitizes_and_uniques() -> None:
    playlist = Playlist(
        id="abc123",
        name='My/Playlist: "Best"  ',
        description=None,
        owner="owner-1",
        tracks=[],
        snapshot_id="snap-1",
        total_tracks=0,
    )

    filename = generate_filename(playlist)
    assert filename.endswith("-abc123.csv")
    assert "/" not in filename
    assert ":" not in filename
    assert '"' not in filename
