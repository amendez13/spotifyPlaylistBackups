"""Backup service orchestration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

from src.backup.exporter import CSVExporter
from src.config import Settings
from src.dropbox.client import DropboxClient
from src.spotify.client import SpotifyClient
from src.spotify.models import Playlist

logger = logging.getLogger(__name__)


@dataclass
class PlaylistBackupResult:
    playlist_name: str
    track_count: int
    file_path: str
    success: bool
    error: Optional[str]


@dataclass
class BackupResult:
    total_playlists: int
    successful: int
    failed: int
    playlist_results: List[PlaylistBackupResult]


class BackupService:
    def __init__(
        self,
        spotify_client: SpotifyClient,
        dropbox_client: DropboxClient,
        exporter: CSVExporter,
        settings: Settings,
    ) -> None:
        self._spotify = spotify_client
        self._dropbox = dropbox_client
        self._exporter = exporter
        self._settings = settings

    def backup_all_playlists(self) -> BackupResult:
        """Backup all user playlists to Dropbox."""
        playlists = self._spotify.get_all_playlists()
        total = len(playlists)
        results: List[PlaylistBackupResult] = []
        successful = 0
        failed = 0

        logger.info("Starting backup for %s playlists", total)
        for index, playlist in enumerate(playlists, start=1):
            logger.info("Backing up playlist %s/%s: %s", index, total, playlist.name)
            result = self._backup_playlist_data(playlist)
            results.append(result)
            if result.success:
                successful += 1
            else:
                failed += 1
                logger.error("Backup failed for %s: %s", playlist.name, result.error)

        return BackupResult(
            total_playlists=total,
            successful=successful,
            failed=failed,
            playlist_results=results,
        )

    def backup_playlist(self, playlist_id: str) -> PlaylistBackupResult:
        """Backup a single playlist."""
        playlists = self._spotify.get_all_playlists()
        target = next((playlist for playlist in playlists if playlist.id == playlist_id), None)
        if not target:
            return PlaylistBackupResult(
                playlist_name=playlist_id,
                track_count=0,
                file_path="",
                success=False,
                error=f"Playlist not found: {playlist_id}",
            )
        return self._backup_playlist_data(target)

    def _backup_playlist_data(self, playlist: Playlist) -> PlaylistBackupResult:
        file_name = self._exporter.generate_filename(playlist)
        file_path = self._build_backup_path(file_name)
        try:
            csv_content = self._exporter.playlist_to_csv(playlist)
            self._dropbox.upload_file(csv_content, file_path)
            return PlaylistBackupResult(
                playlist_name=playlist.name,
                track_count=len(playlist.tracks),
                file_path=file_path,
                success=True,
                error=None,
            )
        except Exception as exc:
            return PlaylistBackupResult(
                playlist_name=playlist.name,
                track_count=len(playlist.tracks),
                file_path=file_path,
                success=False,
                error=str(exc),
            )

    def _build_backup_path(self, filename: str) -> str:
        folder = (self._settings.backup_folder or "").strip()
        if not folder:
            return f"/{filename}"
        if not folder.startswith("/"):
            folder = f"/{folder}"
        folder = folder.rstrip("/")
        self._dropbox.ensure_folder_exists(folder)
        return f"{folder}/{filename}"
