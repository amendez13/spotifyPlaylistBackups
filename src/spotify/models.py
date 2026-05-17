"""Spotify data models."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Artist(BaseModel):
    id: str
    name: str

    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "Artist":
        return cls(id=data["id"], name=data["name"])


class Album(BaseModel):
    id: str
    name: str
    release_date: Optional[str] = None

    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "Album":
        return cls(
            id=data["id"],
            name=data["name"],
            release_date=data.get("release_date"),
        )


class Track(BaseModel):
    id: str
    name: str
    artists: List[Artist]
    album: Album
    duration_ms: int
    added_at: datetime
    added_by: Optional[str]
    is_local: bool = False

    @classmethod
    def from_api(cls, item: Dict[str, Any]) -> "Track":
        track_data = item["track"]
        artists = [Artist.from_api(artist) for artist in track_data.get("artists", [])]
        added_by = None
        if item.get("added_by"):
            added_by = item["added_by"].get("id")
        return cls(
            id=track_data["id"],
            name=track_data["name"],
            artists=artists,
            album=Album.from_api(track_data["album"]),
            duration_ms=track_data["duration_ms"],
            added_at=item["added_at"],
            added_by=added_by,
            is_local=bool(track_data.get("is_local", False)),
        )


class Playlist(BaseModel):
    id: str
    name: str
    description: Optional[str]
    owner: str
    tracks: List[Track]
    snapshot_id: str
    total_tracks: int = Field(ge=0)

    @classmethod
    def from_api(cls, data: Dict[str, Any], tracks: List[Track]) -> "Playlist":
        owner_info = data.get("owner") or {}
        owner_name = owner_info.get("display_name") or owner_info.get("id") or "unknown"
        total_tracks = data.get("tracks", {}).get("total", len(tracks))
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description"),
            owner=owner_name,
            tracks=tracks,
            snapshot_id=data["snapshot_id"],
            total_tracks=total_tracks,
        )
