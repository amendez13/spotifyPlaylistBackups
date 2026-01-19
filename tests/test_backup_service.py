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
        self.files: dict[str, str] = {}
        self.fail_on = fail_on

    def upload_file(self, content: str, path: str) -> None:
        if self.fail_on and self.fail_on in path:
            raise RuntimeError("upload failed")
        self.uploaded.append(path)
        self.files[path] = content

    def download_file(self, path: str) -> str | None:
        return self.files.get(path)

    def ensure_folder_exists(self, path: str) -> None:
        self.folders.append(path)


def _settings() -> Settings:
    return _settings_with_folder("/backups")


def _settings_with_folder(folder: str) -> Settings:
    return Settings.model_validate(
        {
            "SPOTIFY_CLIENT_ID": "spotify-id",
            "SPOTIFY_CLIENT_SECRET": "spotify-secret",
            "DROPBOX_APP_KEY": "dropbox-key",
            "DROPBOX_APP_SECRET": "dropbox-secret",
            "DROPBOX_REFRESH_TOKEN": "refresh",
            "BACKUP_FOLDER": folder,
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


def test_backup_folder_without_leading_slash() -> None:
    spotify = FakeSpotifyClient([_playlist("one", "First")])
    dropbox = FakeDropboxClient()
    service = BackupService(spotify, dropbox, CSVExporter(), _settings_with_folder("backups"))

    result = service.backup_playlist("one")

    assert result.file_path.startswith("/backups/")
    assert dropbox.folders == ["/backups"]


def test_sync_playlist_no_changes() -> None:
    spotify = FakeSpotifyClient([_playlist("one", "First")])
    dropbox = FakeDropboxClient()
    exporter = CSVExporter()
    service = BackupService(spotify, dropbox, exporter, _settings())

    existing_csv = exporter.playlist_to_csv(_playlist("one", "First"))
    dropbox.upload_file(existing_csv, "/backups/First-one.csv")

    result = service.sync_playlist("one")

    assert result.updated is False
    assert result.new_tracks == 0


def test_sync_playlist_updates_with_new_tracks() -> None:
    playlist = _playlist("one", "First")
    spotify = FakeSpotifyClient([playlist])
    dropbox = FakeDropboxClient()
    exporter = CSVExporter()
    service = BackupService(spotify, dropbox, exporter, _settings())

    existing_track = playlist.tracks[0]
    existing_csv = exporter.playlist_to_csv(
        Playlist(
            id="one",
            name="First",
            description=None,
            owner="owner",
            tracks=[existing_track],
            snapshot_id="snap",
            total_tracks=1,
        )
    )
    dropbox.upload_file(existing_csv, "/backups/First-one.csv")

    new_track = _playlist("one", "First").tracks[0]
    new_track.id = "track-2"
    playlist.tracks.append(new_track)

    result = service.sync_playlist("one")

    assert result.updated is True
    assert result.new_tracks == 1


def test_sync_playlist_creates_full_backup_when_missing() -> None:
    playlist = _playlist("one", "First")
    spotify = FakeSpotifyClient([playlist])
    dropbox = FakeDropboxClient()
    service = BackupService(spotify, dropbox, CSVExporter(), _settings())

    result = service.sync_playlist("one")

    assert result.updated is True
    assert result.new_tracks == 1


def test_sync_playlist_not_found() -> None:
    spotify = FakeSpotifyClient([_playlist("one", "First")])
    dropbox = FakeDropboxClient()
    service = BackupService(spotify, dropbox, CSVExporter(), _settings())

    result = service.sync_playlist("missing")

    assert result.updated is False
    assert result.total_tracks == 0
    assert result.playlist_name == "missing"


def test_sync_all_playlists_updates_counts() -> None:
    first = _playlist("one", "First")
    second = _playlist("two", "Second")
    spotify = FakeSpotifyClient([first, second])
    dropbox = FakeDropboxClient()
    exporter = CSVExporter()
    service = BackupService(spotify, dropbox, exporter, _settings())

    dropbox.upload_file(exporter.playlist_to_csv(first), "/backups/First-one.csv")
    dropbox.upload_file(exporter.playlist_to_csv(second), "/backups/Second-two.csv")

    new_track = _playlist("two", "Second").tracks[0]
    new_track.id = "track-2"
    second.tracks.append(new_track)

    result = service.sync_all_playlists()

    assert result.playlists_checked == 2
    assert result.playlists_updated == 1
    assert result.total_new_tracks == 1
    updated = next(item for item in result.results if item.playlist_name == "Second")
    assert updated.updated is True
