"""Dropbox API client wrapper."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, List, Optional, TypeVar, cast

import dropbox
from dropbox.exceptions import ApiError, HttpError, InternalServerError, RateLimitError
from dropbox.files import WriteMode
from src.config import Settings
from src.dropbox.auth import get_dropbox_client

logger = logging.getLogger(__name__)

ResponseT = TypeVar("ResponseT")


def _normalize_path(path: str) -> str:
    if not path:
        return ""
    return path if path.startswith("/") else f"/{path}"


def _is_not_found(error: object) -> bool:
    is_path = getattr(error, "is_path", None)
    get_path = getattr(error, "get_path", None)
    if callable(is_path) and is_path() and callable(get_path):
        path_error = get_path()
        is_not_found = getattr(path_error, "is_not_found", None)
        if callable(is_not_found):
            return bool(is_not_found())
    return False


def _is_conflict(error: object) -> bool:
    is_path = getattr(error, "is_path", None)
    get_path = getattr(error, "get_path", None)
    if callable(is_path) and is_path() and callable(get_path):
        path_error = get_path()
        is_conflict = getattr(path_error, "is_conflict", None)
        if callable(is_conflict):
            return bool(is_conflict())
    return False


class DropboxClient:
    """Wrap the Dropbox SDK with retries and convenience helpers."""

    def __init__(
        self,
        client: dropbox.Dropbox,
        max_retries: int = 3,
        backoff_factor: float = 1.0,
    ) -> None:
        self._client = client
        self._max_retries = max_retries
        self._backoff_factor = backoff_factor

    @classmethod
    def from_settings(cls, settings: Settings) -> "DropboxClient":
        return cls(get_dropbox_client(settings))

    def _request_with_retry(self, func: Callable[..., ResponseT], *args: Any, **kwargs: Any) -> ResponseT:
        delay = self._backoff_factor
        for attempt in range(self._max_retries + 1):
            try:
                return func(*args, **kwargs)
            except RateLimitError as exc:
                if attempt >= self._max_retries:
                    raise
                backoff = exc.backoff or delay
                try:
                    sleep_for = float(backoff)
                except (TypeError, ValueError):
                    sleep_for = delay
                logger.warning("Dropbox rate limited. Retrying in %s seconds.", sleep_for)
                time.sleep(sleep_for)
                delay *= 2
            except (InternalServerError, HttpError) as exc:
                if attempt >= self._max_retries:
                    raise
                logger.warning("Dropbox transient error: %s. Retrying in %s seconds.", exc, delay)
                time.sleep(delay)
                delay *= 2
        raise RuntimeError("Dropbox request failed after retries.")

    def upload_file(self, content: str, path: str) -> None:
        """Upload or overwrite a file."""
        dropbox_path = _normalize_path(path)
        folder = dropbox_path.rsplit("/", 1)[0]
        if folder:
            self.ensure_folder_exists(folder)
        data = content.encode("utf-8")
        self._request_with_retry(
            self._client.files_upload,
            data,
            dropbox_path,
            mode=WriteMode.overwrite,
        )

    def download_file(self, path: str) -> Optional[str]:
        """Download file content, returning None if not found."""
        dropbox_path = _normalize_path(path)
        try:
            metadata, response = self._request_with_retry(self._client.files_download, dropbox_path)
        except ApiError as exc:
            if _is_not_found(exc.error):
                return None
            raise RuntimeError(f"Dropbox download failed for {dropbox_path}") from exc
        content = cast(bytes, response.content)
        return content.decode("utf-8")

    def file_exists(self, path: str) -> bool:
        """Check if a file exists."""
        dropbox_path = _normalize_path(path)
        try:
            self._request_with_retry(self._client.files_get_metadata, dropbox_path)
            return True
        except ApiError as exc:
            if _is_not_found(exc.error):
                return False
            raise RuntimeError(f"Dropbox metadata lookup failed for {dropbox_path}") from exc

    def list_files(self, folder: str) -> List[str]:
        """List files in a folder."""
        dropbox_folder = _normalize_path(folder)
        try:
            result = self._request_with_retry(self._client.files_list_folder, dropbox_folder)
        except ApiError as exc:
            if _is_not_found(exc.error):
                return []
            raise RuntimeError(f"Dropbox list failed for {dropbox_folder}") from exc

        entries = list(result.entries)
        while result.has_more:
            result = self._request_with_retry(self._client.files_list_folder_continue, result.cursor)
            entries.extend(result.entries)

        files: List[str] = []
        for entry in entries:
            path_display = getattr(entry, "path_display", None)
            if path_display:
                files.append(path_display)
        return files

    def list_file_metadata(self, folder: str) -> List["DropboxFileInfo"]:
        """List file metadata in a folder."""
        dropbox_folder = _normalize_path(folder)
        try:
            result = self._request_with_retry(self._client.files_list_folder, dropbox_folder)
        except ApiError as exc:
            if _is_not_found(exc.error):
                return []
            raise RuntimeError(f"Dropbox list failed for {dropbox_folder}") from exc

        entries = list(result.entries)
        while result.has_more:
            result = self._request_with_retry(self._client.files_list_folder_continue, result.cursor)
            entries.extend(result.entries)

        files: List[DropboxFileInfo] = []
        for entry in entries:
            path_display = getattr(entry, "path_display", None)
            server_modified = getattr(entry, "server_modified", None)
            if path_display and isinstance(server_modified, datetime):
                files.append(DropboxFileInfo(path=path_display, server_modified=server_modified))
        return files

    def ensure_folder_exists(self, path: str) -> None:
        """Create folder if it doesn't exist."""
        dropbox_path = _normalize_path(path)
        if not dropbox_path:
            return
        try:
            self._request_with_retry(self._client.files_create_folder_v2, dropbox_path)
        except ApiError as exc:
            if _is_conflict(exc.error):
                return
            raise RuntimeError(f"Dropbox folder creation failed for {dropbox_path}") from exc


@dataclass(frozen=True)
class DropboxFileInfo:
    path: str
    server_modified: datetime
