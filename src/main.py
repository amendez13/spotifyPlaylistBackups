"""CLI entry point for spotifyPlaylistBackups."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Callable, List, NoReturn, Optional, TypeVar, cast

import typer

from src.backup.exporter import CSVExporter
from src.backup.service import BackupService, PlaylistBackupResult, PlaylistSyncResult
from src.config import Settings, load_settings
from src.config.settings import CONFIG_PATH_ENV
from src.dropbox import auth as dropbox_auth
from src.dropbox.client import DropboxClient
from src.spotify import auth as spotify_auth
from src.spotify.client import SpotifyClient
from src.spotify.models import Playlist

APP_HELP = "Backup and export Spotify playlists to CSV."

app = typer.Typer(help=APP_HELP, no_args_is_help=True)
auth_app = typer.Typer(help="Authentication helpers.")
app.add_typer(auth_app, name="auth", help="Authenticate with Spotify and Dropbox.")

CommandFunc = TypeVar("CommandFunc", bound=Callable[..., object])


def typer_callback(func: CommandFunc) -> CommandFunc:
    """Typed wrapper around the Typer callback decorator."""
    decorator: object = app.callback()
    return cast(Callable[[CommandFunc], CommandFunc], decorator)(func)


def typer_command(name: Optional[str] = None) -> Callable[[CommandFunc], CommandFunc]:
    """Typed wrapper around the Typer command decorator."""
    if name:
        decorator: object = app.command(name)
    else:
        decorator = app.command()
    return cast(Callable[[CommandFunc], CommandFunc], decorator)


def typer_auth_command(name: Optional[str] = None) -> Callable[[CommandFunc], CommandFunc]:
    """Typed wrapper around the auth subcommand decorator."""
    if name:
        decorator: object = auth_app.command(name)
    else:
        decorator = auth_app.command()
    return cast(Callable[[CommandFunc], CommandFunc], decorator)


@typer_callback
def cli(
    ctx: typer.Context,
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        help="Path to a custom config file.",
        dir_okay=False,
        readable=True,
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show planned actions without changes."),
) -> None:
    """Backup and export Spotify playlists to CSV."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["dry_run"] = dry_run
    if config:
        if not config.exists():
            raise typer.BadParameter(f"Config file not found: {config}")
        os.environ[CONFIG_PATH_ENV] = str(config)
        ctx.obj["config_path"] = config
    _configure_logging(verbose)


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


def _fail(message: str) -> NoReturn:
    typer.secho(message, fg=typer.colors.RED)
    raise typer.Exit(code=1)


def _load_settings() -> Settings:
    try:
        return load_settings()
    except Exception as exc:
        _fail(f"Failed to load settings: {exc}")


def _build_spotify_client(settings: Settings) -> SpotifyClient:
    return SpotifyClient.from_settings(settings)


def _build_dropbox_client(settings: Settings) -> DropboxClient:
    return DropboxClient.from_settings(settings)


class DryRunDropboxClient(DropboxClient):
    """Dropbox client wrapper that skips write operations."""

    def __init__(self, client: DropboxClient) -> None:
        super().__init__(client._client, client._max_retries, client._backoff_factor)

    def upload_file(self, content: str, path: str) -> None:
        logging.info("Dry run: skipping upload to %s", path)

    def ensure_folder_exists(self, path: str) -> None:
        logging.info("Dry run: skipping folder creation for %s", path)


def _build_backup_service(settings: Settings, dry_run: bool) -> BackupService:
    spotify = _build_spotify_client(settings)
    dropbox = _build_dropbox_client(settings)
    if dry_run:
        dropbox = DryRunDropboxClient(dropbox)
    return BackupService(spotify, dropbox, CSVExporter(), settings)


def _print_backup_result(result: PlaylistBackupResult) -> None:
    if result.success:
        typer.secho(
            f"[OK] {result.playlist_name} ({result.track_count} tracks) -> {result.file_path}",
            fg=typer.colors.GREEN,
        )
    else:
        typer.secho(
            f"[ERR] {result.playlist_name} - {result.error}",
            fg=typer.colors.RED,
        )


def _print_sync_result(result: PlaylistSyncResult) -> None:
    if result.updated:
        typer.secho(
            f"[OK] {result.playlist_name} (+{result.new_tracks} new, {result.total_tracks} total)",
            fg=typer.colors.GREEN,
        )
    else:
        typer.secho(
            f"[OK] {result.playlist_name} (no changes, {result.total_tracks} total)",
            fg=typer.colors.BLUE,
        )


def _select_playlist(playlists: List[Playlist], name_or_id: str) -> Playlist:
    matches = [playlist for playlist in playlists if playlist.id == name_or_id or playlist.name == name_or_id]
    if not matches:
        _fail(f"No playlist found matching '{name_or_id}'.")
    if len(matches) > 1:
        names = ", ".join(playlist.id for playlist in matches)
        _fail(f"Multiple playlists match '{name_or_id}'. IDs: {names}")
    return matches[0]


def _format_timestamp(value: datetime) -> str:
    return value.astimezone().isoformat(timespec="seconds")


@typer_auth_command()
def spotify(ctx: typer.Context) -> None:
    """Authenticate with Spotify."""
    settings = _load_settings()
    if ctx.obj.get("dry_run"):
        typer.secho("Dry run: skipping Spotify auth flow.", fg=typer.colors.YELLOW)
        return
    try:
        spotify_auth.get_spotify_client(settings)
    except Exception as exc:
        _fail(f"Spotify auth failed: {exc}")
    typer.secho("Spotify authentication complete.", fg=typer.colors.GREEN)


@typer_auth_command()
def dropbox(ctx: typer.Context) -> None:
    """Authenticate with Dropbox."""
    settings = _load_settings()
    if ctx.obj.get("dry_run"):
        typer.secho("Dry run: skipping Dropbox auth flow.", fg=typer.colors.YELLOW)
        return
    try:
        auth_url = dropbox_auth.start_auth_flow(settings)
        typer.secho("Open this URL to authorize Dropbox:", fg=typer.colors.CYAN)
        typer.echo(auth_url)
        auth_code = typer.prompt("Paste the authorization code")
        dropbox_auth.finish_auth_flow(auth_code, settings)
    except Exception as exc:
        _fail(f"Dropbox auth failed: {exc}")
    typer.secho("Dropbox authentication complete.", fg=typer.colors.GREEN)


@typer_auth_command("status")
def auth_status() -> None:
    """Show Spotify and Dropbox auth status."""
    settings = _load_settings()
    spotify_ok = spotify_auth.is_authenticated(settings)
    dropbox_ok = dropbox_auth.is_authenticated(settings)
    typer.secho(
        f"Spotify: {'authenticated' if spotify_ok else 'missing token'}",
        fg=typer.colors.GREEN if spotify_ok else typer.colors.RED,
    )
    typer.secho(
        f"Dropbox: {'authenticated' if dropbox_ok else 'missing token'}",
        fg=typer.colors.GREEN if dropbox_ok else typer.colors.RED,
    )


@typer_command()
def backup(
    ctx: typer.Context,
    playlist: Optional[str] = typer.Option(None, "--playlist", help="Backup a specific playlist by name or id."),
) -> None:
    """Backup playlists to Dropbox."""
    settings = _load_settings()
    dry_run = bool(ctx.obj.get("dry_run"))
    if dry_run:
        typer.secho("Dry run: no Dropbox changes will be made.", fg=typer.colors.YELLOW)
    service = _build_backup_service(settings, dry_run)

    if playlist:
        try:
            playlists = service._spotify.get_all_playlists()
            target = _select_playlist(playlists, playlist)
            playlist_result = service._backup_playlist_data(target)
        except Exception as exc:
            _fail(f"Backup failed: {exc}")
        _print_backup_result(playlist_result)
        return

    try:
        backup_result = service.backup_all_playlists()
    except Exception as exc:
        _fail(f"Backup failed: {exc}")

    typer.secho("Backing up playlists:", fg=typer.colors.CYAN)
    for item in backup_result.playlist_results:
        _print_backup_result(item)
    typer.secho(
        f"Backup complete: {backup_result.successful}/{backup_result.total_playlists} successful",
        fg=typer.colors.GREEN if backup_result.failed == 0 else typer.colors.YELLOW,
    )


@typer_command("sync")
def sync_playlists(ctx: typer.Context) -> None:
    """Sync playlists, updating backups with new tracks only."""
    settings = _load_settings()
    dry_run = bool(ctx.obj.get("dry_run"))
    if dry_run:
        typer.secho("Dry run: no Dropbox changes will be made.", fg=typer.colors.YELLOW)
    service = _build_backup_service(settings, dry_run)

    try:
        result = service.sync_all_playlists()
    except Exception as exc:
        _fail(f"Sync failed: {exc}")

    typer.secho("Sync results:", fg=typer.colors.CYAN)
    for item in result.results:
        _print_sync_result(item)
    typer.secho(
        f"Sync complete: {result.playlists_updated}/{result.playlists_checked} updated, "
        f"{result.total_new_tracks} new tracks",
        fg=typer.colors.GREEN,
    )


@typer_command("list")
def list_playlists(ctx: typer.Context) -> None:
    """List Spotify playlists."""
    settings = _load_settings()
    verbose = bool(ctx.obj.get("verbose"))
    spotify = _build_spotify_client(settings)
    try:
        playlists = spotify.get_all_playlists()
    except Exception as exc:
        _fail(f"Failed to list playlists: {exc}")
    if not playlists:
        typer.secho("No playlists found.", fg=typer.colors.YELLOW)
        return
    for playlist in playlists:
        if verbose:
            typer.echo(f"{playlist.name} ({playlist.total_tracks} tracks)")
        else:
            typer.echo(playlist.name)


@typer_command()
def status() -> None:
    """Show backup status and last update time."""
    settings = _load_settings()
    dropbox = _build_dropbox_client(settings)
    try:
        files = dropbox.list_file_metadata(settings.backup_folder)
    except Exception as exc:
        _fail(f"Failed to load backup status: {exc}")
    if not files:
        typer.secho("No backups found in Dropbox.", fg=typer.colors.YELLOW)
        return
    latest = max(files, key=lambda item: item.server_modified)
    typer.secho(f"Backups found: {len(files)}", fg=typer.colors.GREEN)
    typer.secho(f"Latest backup: {latest.path}", fg=typer.colors.GREEN)
    typer.echo(f"Last modified: {_format_timestamp(latest.server_modified)}")


def main() -> None:
    """Run the CLI."""
    app()


if __name__ == "__main__":
    main()
