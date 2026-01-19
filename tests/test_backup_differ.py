"""Tests for backup diff helpers."""

from __future__ import annotations

from datetime import datetime, timezone

from src.backup.differ import find_new_tracks, parse_csv_track_ids
from src.backup.exporter import CSV_BOM
from src.spotify.models import Album, Artist, Track


def _track(track_id: str) -> Track:
    return Track(
        id=track_id,
        name="Song",
        artists=[Artist(id="artist-1", name="Artist")],
        album=Album(id="album-1", name="Album", release_date="2024-01-01"),
        duration_ms=1000,
        added_at=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        added_by="user-1",
        is_local=False,
    )


def test_parse_csv_track_ids_handles_bom() -> None:
    csv_content = CSV_BOM + "track_id,track_name\n1,Song\n2,Song\n"
    assert parse_csv_track_ids(csv_content) == {"1", "2"}


def test_find_new_tracks_filters_existing() -> None:
    csv_content = "track_id,track_name\n1,Song\n"
    current = [_track("1"), _track("2")]
    new_tracks = find_new_tracks(current, csv_content)
    assert [track.id for track in new_tracks] == ["2"]
