"""Tests for the CLI entry point."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from src.backup.service import BackupResult, PlaylistBackupResult, PlaylistSyncResult, SyncResult
from src.config import Settings
from src.config.settings import CONFIG_PATH_ENV
from src.dropbox.client import DropboxClient, DropboxFileInfo
from src.main import (
    APP_HELP,
    DryRunDropboxClient,
    _build_backup_service,
    _build_dropbox_client,
    _build_spotify_client,
    _print_backup_result,
    _print_sync_result,
    _select_playlist,
    app,
    main,
)
from src.spotify.models import Album, Artist, Playlist, Track


def _settings() -> Settings:
    return Settings.model_construct(
        spotify_client_id="spotify-id",
        spotify_client_secret="spotify-secret",
        spotify_redirect_uri="http://localhost:8888/callback",
        dropbox_app_key="dropbox-key",
        dropbox_app_secret="dropbox-secret",
        dropbox_refresh_token="refresh",
        backup_folder="/backups",
        csv_delimiter=",",
        token_storage_path=".spotify_token.json",
    )


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


def _playlist(name: str, playlist_id: str, track_count: int = 1) -> Playlist:
    tracks = [_track("track-1")]
    return Playlist(
        id=playlist_id,
        name=name,
        description=None,
        owner="owner",
        tracks=tracks,
        snapshot_id="snap",
        total_tracks=track_count,
    )


class FakeSpotifyClient:
    def __init__(self, playlists: list[Playlist]) -> None:
        self._playlists = playlists

    def get_all_playlists(self) -> list[Playlist]:
        return self._playlists


class FakeBackupService:
    def __init__(
        self,
        playlists: list[Playlist],
        backup_result: BackupResult,
        sync_result: SyncResult,
        playlist_result: PlaylistBackupResult,
    ) -> None:
        self._spotify = FakeSpotifyClient(playlists)
        self._backup_result = backup_result
        self._sync_result = sync_result
        self._playlist_result = playlist_result

    def backup_all_playlists(self) -> BackupResult:
        return self._backup_result

    def sync_all_playlists(self) -> SyncResult:
        return self._sync_result

    def _backup_playlist_data(self, playlist: Playlist) -> PlaylistBackupResult:
        return self._playlist_result


class FakeDropboxClient:
    def __init__(self, files: list[DropboxFileInfo]) -> None:
        self._files = files

    def list_file_metadata(self, _folder: str) -> list[DropboxFileInfo]:
        return self._files


class ErrorSpotifyClient:
    def get_all_playlists(self) -> list[Playlist]:
        raise RuntimeError("spotify error")


class ErrorBackupService:
    def __init__(self, playlists: list[Playlist]) -> None:
        self._spotify = FakeSpotifyClient(playlists)

    def backup_all_playlists(self) -> BackupResult:
        raise RuntimeError("backup error")

    def sync_all_playlists(self) -> SyncResult:
        raise RuntimeError("sync error")

    def _backup_playlist_data(self, playlist: Playlist) -> PlaylistBackupResult:
        raise RuntimeError("backup error")


def test_cli_help_includes_description() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert APP_HELP in result.output


def test_cli_config_sets_env_and_handles_empty_list(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("backup:\n  folder: /backups\n")
    monkeypatch.delenv(CONFIG_PATH_ENV, raising=False)
    monkeypatch.setattr("src.main._load_settings", lambda: _settings())
    monkeypatch.setattr("src.main._build_spotify_client", lambda _settings: FakeSpotifyClient([]))

    runner = CliRunner()
    result = runner.invoke(app, ["--config", str(config_path), "list"])

    assert result.exit_code == 0
    assert "No playlists found." in result.output
    assert os.environ[CONFIG_PATH_ENV] == str(config_path)


def test_cli_config_missing_file_error() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--config", "missing.yaml", "list"])

    assert result.exit_code != 0
    assert "Config file not found" in result.output


def test_load_settings_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_error() -> Settings:
        raise RuntimeError("boom")

    monkeypatch.setattr("src.main.load_settings", raise_error)

    runner = CliRunner()
    result = runner.invoke(app, ["list"])

    assert result.exit_code == 1
    assert "Failed to load settings" in result.output


def test_auth_status_outputs_status(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.main._load_settings", lambda: _settings())
    monkeypatch.setattr("src.main.spotify_auth.is_authenticated", lambda _settings: True)
    monkeypatch.setattr("src.main.dropbox_auth.is_authenticated", lambda _settings: False)

    runner = CliRunner()
    result = runner.invoke(app, ["auth", "status"])

    assert result.exit_code == 0
    assert "Spotify: authenticated" in result.output
    assert "Dropbox: missing token" in result.output


def test_auth_spotify_dry_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.main._load_settings", lambda: _settings())

    runner = CliRunner()
    result = runner.invoke(app, ["--dry-run", "auth", "spotify"])

    assert result.exit_code == 0
    assert "Dry run: skipping Spotify auth flow." in result.output


def test_auth_spotify_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.main._load_settings", lambda: _settings())
    monkeypatch.setattr("src.main.spotify_auth.get_spotify_client", lambda _settings: object())

    runner = CliRunner()
    result = runner.invoke(app, ["auth", "spotify"])

    assert result.exit_code == 0
    assert "Spotify authentication complete." in result.output


def test_auth_spotify_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(_settings: Settings) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr("src.main._load_settings", lambda: _settings())
    monkeypatch.setattr("src.main.spotify_auth.get_spotify_client", fail)

    runner = CliRunner()
    result = runner.invoke(app, ["auth", "spotify"])

    assert result.exit_code == 1
    assert "Spotify auth failed" in result.output


def test_auth_dropbox_dry_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.main._load_settings", lambda: _settings())

    runner = CliRunner()
    result = runner.invoke(app, ["--dry-run", "auth", "dropbox"])

    assert result.exit_code == 0
    assert "Dry run: skipping Dropbox auth flow." in result.output


def test_auth_dropbox_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.main._load_settings", lambda: _settings())
    monkeypatch.setattr("src.main.dropbox_auth.start_auth_flow", lambda _settings: "http://example")
    monkeypatch.setattr("src.main.dropbox_auth.finish_auth_flow", lambda _code, _settings: None)
    monkeypatch.setattr("src.main.typer.prompt", lambda _prompt: "code")

    runner = CliRunner()
    result = runner.invoke(app, ["auth", "dropbox"])

    assert result.exit_code == 0
    assert "Dropbox authentication complete." in result.output


def test_auth_dropbox_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(_settings: Settings) -> str:
        raise RuntimeError("boom")

    monkeypatch.setattr("src.main._load_settings", lambda: _settings())
    monkeypatch.setattr("src.main.dropbox_auth.start_auth_flow", fail)

    runner = CliRunner()
    result = runner.invoke(app, ["auth", "dropbox"])

    assert result.exit_code == 1
    assert "Dropbox auth failed" in result.output


def test_list_playlists_verbose(monkeypatch: pytest.MonkeyPatch) -> None:
    playlists = [_playlist("Favorites", "one", track_count=2)]
    monkeypatch.setattr("src.main._load_settings", lambda: _settings())
    monkeypatch.setattr("src.main._build_spotify_client", lambda _settings: FakeSpotifyClient(playlists))

    runner = CliRunner()
    result = runner.invoke(app, ["--verbose", "list"])

    assert result.exit_code == 0
    assert "Favorites (2 tracks)" in result.output


def test_list_playlists_non_verbose(monkeypatch: pytest.MonkeyPatch) -> None:
    playlists = [_playlist("Favorites", "one", track_count=2)]
    monkeypatch.setattr("src.main._load_settings", lambda: _settings())
    monkeypatch.setattr("src.main._build_spotify_client", lambda _settings: FakeSpotifyClient(playlists))

    runner = CliRunner()
    result = runner.invoke(app, ["list"])

    assert result.exit_code == 0
    assert "Favorites" in result.output


def test_list_playlists_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.main._load_settings", lambda: _settings())
    monkeypatch.setattr("src.main._build_spotify_client", lambda _settings: ErrorSpotifyClient())

    runner = CliRunner()
    result = runner.invoke(app, ["list"])

    assert result.exit_code == 1
    assert "Failed to list playlists" in result.output


def test_backup_all_playlists(monkeypatch: pytest.MonkeyPatch) -> None:
    playlist_result = PlaylistBackupResult(
        playlist_name="Favorites",
        track_count=2,
        file_path="/backups/Favorites.csv",
        success=True,
        error=None,
    )
    backup_result = BackupResult(
        total_playlists=1,
        successful=1,
        failed=0,
        playlist_results=[playlist_result],
    )
    sync_result = SyncResult(playlists_checked=0, playlists_updated=0, total_new_tracks=0, results=[])
    service = FakeBackupService([_playlist("Favorites", "one")], backup_result, sync_result, playlist_result)

    monkeypatch.setattr("src.main._load_settings", lambda: _settings())
    monkeypatch.setattr("src.main._build_backup_service", lambda _settings, _dry_run: service)

    runner = CliRunner()
    result = runner.invoke(app, ["backup"])

    assert result.exit_code == 0
    assert "Backup complete: 1/1 successful" in result.output


def test_backup_all_playlists_error(monkeypatch: pytest.MonkeyPatch) -> None:
    playlist = _playlist("Favorites", "one")
    service = ErrorBackupService([playlist])

    monkeypatch.setattr("src.main._load_settings", lambda: _settings())
    monkeypatch.setattr("src.main._build_backup_service", lambda _settings, _dry_run: service)

    runner = CliRunner()
    result = runner.invoke(app, ["backup"])

    assert result.exit_code == 1
    assert "Backup failed" in result.output


def test_backup_playlist_by_name(monkeypatch: pytest.MonkeyPatch) -> None:
    playlist_result = PlaylistBackupResult(
        playlist_name="Focus",
        track_count=1,
        file_path="/backups/Focus.csv",
        success=True,
        error=None,
    )
    backup_result = BackupResult(
        total_playlists=1,
        successful=1,
        failed=0,
        playlist_results=[playlist_result],
    )
    sync_result = SyncResult(playlists_checked=0, playlists_updated=0, total_new_tracks=0, results=[])
    playlist = _playlist("Focus", "focus-id")
    service = FakeBackupService([playlist], backup_result, sync_result, playlist_result)

    monkeypatch.setattr("src.main._load_settings", lambda: _settings())
    monkeypatch.setattr("src.main._build_backup_service", lambda _settings, _dry_run: service)

    runner = CliRunner()
    result = runner.invoke(app, ["backup", "--playlist", "Focus"])

    assert result.exit_code == 0
    assert "Focus" in result.output


def test_backup_playlist_error(monkeypatch: pytest.MonkeyPatch) -> None:
    playlist = _playlist("Focus", "focus-id")
    service = ErrorBackupService([playlist])

    monkeypatch.setattr("src.main._load_settings", lambda: _settings())
    monkeypatch.setattr("src.main._build_backup_service", lambda _settings, _dry_run: service)

    runner = CliRunner()
    result = runner.invoke(app, ["backup", "--playlist", "Focus"])

    assert result.exit_code == 1
    assert "Backup failed" in result.output


def test_backup_dry_run_message(monkeypatch: pytest.MonkeyPatch) -> None:
    playlist_result = PlaylistBackupResult(
        playlist_name="Favorites",
        track_count=1,
        file_path="/backups/Favorites.csv",
        success=True,
        error=None,
    )
    backup_result = BackupResult(
        total_playlists=1,
        successful=1,
        failed=0,
        playlist_results=[playlist_result],
    )
    sync_result = SyncResult(playlists_checked=0, playlists_updated=0, total_new_tracks=0, results=[])
    service = FakeBackupService([_playlist("Favorites", "one")], backup_result, sync_result, playlist_result)

    monkeypatch.setattr("src.main._load_settings", lambda: _settings())
    monkeypatch.setattr("src.main._build_backup_service", lambda _settings, _dry_run: service)

    runner = CliRunner()
    result = runner.invoke(app, ["--dry-run", "backup"])

    assert result.exit_code == 0
    assert "Dry run: no Dropbox changes will be made." in result.output


def test_sync_command(monkeypatch: pytest.MonkeyPatch) -> None:
    playlist_result = PlaylistBackupResult(
        playlist_name="Focus",
        track_count=1,
        file_path="/backups/Focus.csv",
        success=True,
        error=None,
    )
    backup_result = BackupResult(
        total_playlists=0,
        successful=0,
        failed=0,
        playlist_results=[],
    )
    sync_item = PlaylistSyncResult(
        playlist_name="Focus",
        new_tracks=1,
        total_tracks=2,
        updated=True,
    )
    sync_result = SyncResult(playlists_checked=1, playlists_updated=1, total_new_tracks=1, results=[sync_item])
    service = FakeBackupService([_playlist("Focus", "focus-id")], backup_result, sync_result, playlist_result)

    monkeypatch.setattr("src.main._load_settings", lambda: _settings())
    monkeypatch.setattr("src.main._build_backup_service", lambda _settings, _dry_run: service)

    runner = CliRunner()
    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 0
    assert "Sync complete: 1/1 updated, 1 new tracks" in result.output


def test_sync_command_error(monkeypatch: pytest.MonkeyPatch) -> None:
    playlist = _playlist("Focus", "focus-id")
    service = ErrorBackupService([playlist])

    monkeypatch.setattr("src.main._load_settings", lambda: _settings())
    monkeypatch.setattr("src.main._build_backup_service", lambda _settings, _dry_run: service)

    runner = CliRunner()
    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 1
    assert "Sync failed" in result.output


def test_sync_dry_run_message(monkeypatch: pytest.MonkeyPatch) -> None:
    playlist_result = PlaylistBackupResult(
        playlist_name="Focus",
        track_count=1,
        file_path="/backups/Focus.csv",
        success=True,
        error=None,
    )
    backup_result = BackupResult(total_playlists=0, successful=0, failed=0, playlist_results=[])
    sync_item = PlaylistSyncResult(
        playlist_name="Focus",
        new_tracks=0,
        total_tracks=1,
        updated=False,
    )
    sync_result = SyncResult(playlists_checked=1, playlists_updated=0, total_new_tracks=0, results=[sync_item])
    service = FakeBackupService([_playlist("Focus", "focus-id")], backup_result, sync_result, playlist_result)

    monkeypatch.setattr("src.main._load_settings", lambda: _settings())
    monkeypatch.setattr("src.main._build_backup_service", lambda _settings, _dry_run: service)

    runner = CliRunner()
    result = runner.invoke(app, ["--dry-run", "sync"])

    assert result.exit_code == 0
    assert "Dry run: no Dropbox changes will be made." in result.output


def test_status_command(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime(2024, 1, 2, 10, 0, tzinfo=timezone.utc)
    files = [DropboxFileInfo(path="/backups/Focus.csv", server_modified=now)]
    fake_dropbox = FakeDropboxClient(files)

    monkeypatch.setattr("src.main._load_settings", lambda: _settings())
    monkeypatch.setattr("src.main._build_dropbox_client", lambda _settings: fake_dropbox)

    runner = CliRunner()
    result = runner.invoke(app, ["status"])

    assert result.exit_code == 0
    assert "Backups found: 1" in result.output
    assert "Latest backup: /backups/Focus.csv" in result.output


def test_status_command_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_dropbox = FakeDropboxClient([])

    monkeypatch.setattr("src.main._load_settings", lambda: _settings())
    monkeypatch.setattr("src.main._build_dropbox_client", lambda _settings: fake_dropbox)

    runner = CliRunner()
    result = runner.invoke(app, ["status"])

    assert result.exit_code == 0
    assert "No backups found in Dropbox." in result.output


def test_status_command_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class ErrorDropboxClient:
        def list_file_metadata(self, _folder: str) -> list[DropboxFileInfo]:
            raise RuntimeError("dropbox error")

    monkeypatch.setattr("src.main._load_settings", lambda: _settings())
    monkeypatch.setattr("src.main._build_dropbox_client", lambda _settings: ErrorDropboxClient())

    runner = CliRunner()
    result = runner.invoke(app, ["status"])

    assert result.exit_code == 1
    assert "Failed to load backup status" in result.output


def test_helpers_cover_select_and_prints() -> None:
    _print_backup_result(
        PlaylistBackupResult(
            playlist_name="Broken",
            track_count=0,
            file_path="",
            success=False,
            error="boom",
        )
    )
    _print_sync_result(
        PlaylistSyncResult(
            playlist_name="Focus",
            new_tracks=0,
            total_tracks=1,
            updated=False,
        )
    )

    with pytest.raises(typer.Exit):
        _select_playlist([], "missing")
    with pytest.raises(typer.Exit):
        _select_playlist([_playlist("Dup", "one"), _playlist("Dup", "two")], "Dup")


def test_build_client_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    spotify_client = object()
    dropbox_client = object()

    monkeypatch.setattr("src.main.SpotifyClient.from_settings", lambda _settings: spotify_client)
    monkeypatch.setattr("src.main.DropboxClient.from_settings", lambda _settings: dropbox_client)

    assert _build_spotify_client(_settings()) is spotify_client
    assert _build_dropbox_client(_settings()) is dropbox_client


def test_dry_run_dropbox_client_and_service(monkeypatch: pytest.MonkeyPatch) -> None:
    base = DropboxClient(object())
    dry_run = DryRunDropboxClient(base)
    dry_run.upload_file("content", "/path")
    dry_run.ensure_folder_exists("/path")

    monkeypatch.setattr("src.main._build_spotify_client", lambda _settings: object())
    monkeypatch.setattr("src.main._build_dropbox_client", lambda _settings: base)
    service = _build_backup_service(_settings(), dry_run=True)

    assert isinstance(service._dropbox, DryRunDropboxClient)


def test_main_runs_cli_help(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["main", "--help"])
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0
