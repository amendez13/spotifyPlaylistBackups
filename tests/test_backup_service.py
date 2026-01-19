"""Tests for backup service."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from src.backup.exporter import CSVExporter
from src.backup.service import BackupService
from src.config import Settings
from src.spotify.models import Album, Artist, Playlist, Track


class FakeSpotifyClient:
    def __init__(self, playlists: List[Playlist]) -> None:
        self._playlists = playlists

    def get_all_playlists(self) -> List[Playlist]:
        return self._playlists


class FakeDropboxClient:
    def __init__(self, fail_on: str | None = None) -> None:
        self.uploaded: List[str] = []
        self.folders: List[str] = []
        self.fail_on = fail_on

    def upload_file(self, content: str, path: str) -> None:
        if self.fail_on and self.fail_on in path:
            raise RuntimeError("upload failed")
        self.uploaded.append(path)

    def ensure_folder_exists(self, path: str) -> None:
        self.folders.append(path)


def _settings() -> Settings:
    return Settings.model_validate(
        {
            "SPOTIFY_CLIENT_ID": "spotify-id",
            "SPOTIFY_CLIENT_SECRET": "spotify-secret",
            "DROPBOX_APP_KEY": "dropbox-key",
            "DROPBOX_APP_SECRET": "dropbox-secret",
            "DROPBOX_REFRESH_TOKEN": "refresh",
            "BACKUP_FOLDER": "/backups",
        }
    )


def _playlist(playlist_id: str, name: str) -> Playlist:
    track = Track(
        id="track-1",
        name="Song",
        artists=[Artist(id="artist-1", name="Artist")],
        album=Album(id="album-1", name="Album", release_date="2024-01-01"),
        duration_ms=1000,
        added_at=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        added_by="user-1",
        is_local=False,
    )
    return Playlist(
        id=playlist_id,
        name=name,
        description=None,
        owner="owner",
        tracks=[track],
        snapshot_id="snap",
        total_tracks=1,
    )


def test_backup_all_playlists_success() -> None:
    playlists = [_playlist("one", "First"), _playlist("two", "Second")]
    spotify = FakeSpotifyClient(playlists)
    dropbox = FakeDropboxClient()
    service = BackupService(spotify, dropbox, CSVExporter(), _settings())

    result = service.backup_all_playlists()

    assert result.total_playlists == 2
    assert result.successful == 2
    assert result.failed == 0
    assert dropbox.uploaded == [
        "/backups/First-one.csv",
        "/backups/Second-two.csv",
    ]


def test_backup_all_playlists_partial_failure() -> None:
    playlists = [_playlist("one", "First"), _playlist("two", "Second")]
    spotify = FakeSpotifyClient(playlists)
    dropbox = FakeDropboxClient(fail_on="Second-two.csv")
    service = BackupService(spotify, dropbox, CSVExporter(), _settings())

    result = service.backup_all_playlists()

    assert result.successful == 1
    assert result.failed == 1
    assert any(not item.success for item in result.playlist_results)


def test_backup_playlist_not_found() -> None:
    spotify = FakeSpotifyClient([_playlist("one", "First")])
    dropbox = FakeDropboxClient()
    service = BackupService(spotify, dropbox, CSVExporter(), _settings())

    result = service.backup_playlist("missing")

    assert result.success is False
    assert "not found" in result.error.lower()


def test_backup_playlist_success() -> None:
    spotify = FakeSpotifyClient([_playlist("one", "First")])
    dropbox = FakeDropboxClient()
    service = BackupService(spotify, dropbox, CSVExporter(), _settings())

    result = service.backup_playlist("one")

    assert result.success is True
    assert result.file_path.endswith("First-one.csv")
