"""Track diff helpers for CSV sync."""

from __future__ import annotations

import csv
import io
from typing import List, Set

from src.backup.exporter import CSV_BOM
from src.spotify.models import Track


def parse_csv_track_ids(csv_content: str) -> Set[str]:
    """Extract track IDs from existing CSV content."""
    content = csv_content.lstrip(CSV_BOM).strip()
    reader = csv.DictReader(io.StringIO(content))
    track_ids: Set[str] = set()
    for row in reader:
        track_id = row.get("track_id")
        if track_id:
            track_ids.add(track_id)
    return track_ids


def find_new_tracks(current_tracks: List[Track], existing_csv: str) -> List[Track]:
    """Compare current tracks with existing CSV and return new ones."""
    existing_ids = parse_csv_track_ids(existing_csv)
    return [track for track in current_tracks if track.id not in existing_ids]
