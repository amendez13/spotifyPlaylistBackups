"""CSV export helpers for playlist backups."""

from __future__ import annotations

import csv
import io
import re
from typing import Dict, List

from src.spotify.models import Playlist, Track

CSV_FIELDS = [
    "track_id",
    "track_name",
    "artists",
    "album",
    "album_release_date",
    "added_at",
    "added_by",
    "duration_ms",
    "is_local",
]

CSV_BOM = "\ufeff"

_INVALID_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|]+')
_WHITESPACE = re.compile(r"\s+")


def tracks_to_csv_rows(tracks: List[Track]) -> List[Dict[str, object]]:
    """Convert tracks into CSV row dictionaries."""
    rows: List[Dict[str, object]] = []
    for track in tracks:
        artists = ", ".join(artist.name for artist in track.artists)
        rows.append(
            {
                "track_id": track.id,
                "track_name": track.name,
                "artists": artists,
                "album": track.album.name,
                "album_release_date": track.album.release_date,
                "added_at": track.added_at.isoformat().replace("+00:00", "Z"),
                "added_by": track.added_by,
                "duration_ms": track.duration_ms,
                "is_local": track.is_local,
            }
        )
    return rows


def playlist_to_csv(playlist: Playlist) -> str:
    """Convert playlist tracks into a CSV string with UTF-8 BOM."""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_FIELDS, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
    writer.writeheader()
    writer.writerows(tracks_to_csv_rows(playlist.tracks))
    # Prepend BOM for Excel compatibility.
    return CSV_BOM + buffer.getvalue()


def generate_filename(playlist: Playlist) -> str:
    """Generate a filesystem-safe filename using the playlist name and id."""
    name = playlist.name.strip() or "playlist"
    name = _INVALID_FILENAME_CHARS.sub("-", name)
    name = _WHITESPACE.sub(" ", name).strip(" .")
    if not name:
        name = "playlist"
    return f"{name}-{playlist.id}.csv"


class CSVExporter:
    """Thin wrapper to expose CSV export helpers."""

    def playlist_to_csv(self, playlist: Playlist) -> str:
        return playlist_to_csv(playlist)

    def tracks_to_csv_rows(self, tracks: List[Track]) -> List[Dict[str, object]]:
        return tracks_to_csv_rows(tracks)

    def generate_filename(self, playlist: Playlist) -> str:
        return generate_filename(playlist)
