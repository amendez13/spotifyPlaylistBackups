"""Tests for Dropbox client wrapper."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from dropbox.exceptions import ApiError, HttpError, RateLimitError
from src.config import Settings
from src.dropbox.client import DropboxClient, DropboxFileInfo, _is_conflict, _is_not_found, _normalize_path


class FakePathError:
    def __init__(self, not_found: bool = False, conflict: bool = False) -> None:
        self._not_found = not_found
        self._conflict = conflict

    def is_not_found(self) -> bool:
        return self._not_found

    def is_conflict(self) -> bool:
        return self._conflict


class FakeError:
    def __init__(self, path_error: FakePathError) -> None:
        self._path_error = path_error

    def is_path(self) -> bool:
        return True

    def get_path(self) -> FakePathError:
        return self._path_error


class FakeDropbox:
    def __init__(self) -> None:
        self.created_folders: List[str] = []
        self.uploaded: Dict[str, bytes] = {}
        self.list_pages: List[Any] = []
        self.continue_pages: Dict[str, Any] = {}

    def files_create_folder_v2(self, path: str) -> None:
        self.created_folders.append(path)

    def files_upload(self, data: bytes, path: str, mode: object) -> None:
        self.uploaded[path] = data

    def files_download(self, path: str) -> tuple[object, SimpleNamespace]:
        return object(), SimpleNamespace(content=b"hello")

    def files_get_metadata(self, path: str) -> object:
        return object()

    def files_list_folder(self, path: str) -> SimpleNamespace:
        return self.list_pages[0]

    def files_list_folder_continue(self, cursor: str) -> SimpleNamespace:
        return self.continue_pages[cursor]


def _api_error(not_found: bool = False, conflict: bool = False) -> ApiError:
    return ApiError("req", FakeError(FakePathError(not_found=not_found, conflict=conflict)), "msg", "en")


def test_upload_file_creates_folder_and_uploads() -> None:
    client = DropboxClient(FakeDropbox())
    client.upload_file("content", "folder/file.txt")
    assert "/folder" in client._client.created_folders
    assert client._client.uploaded["/folder/file.txt"] == b"content"


def test_download_file_returns_none_on_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeDropbox()

    def missing(_path: str) -> tuple[object, SimpleNamespace]:
        raise _api_error(not_found=True)

    fake.files_download = missing  # type: ignore[assignment]
    client = DropboxClient(fake)
    assert client.download_file("/missing.txt") is None


def test_file_exists_handles_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeDropbox()

    def missing(_path: str) -> object:
        raise _api_error(not_found=True)

    fake.files_get_metadata = missing  # type: ignore[assignment]
    client = DropboxClient(fake)
    assert client.file_exists("missing.txt") is False


def test_list_files_paginates() -> None:
    fake = FakeDropbox()
    page1 = SimpleNamespace(entries=[SimpleNamespace(path_display="/one.txt")], has_more=True, cursor="cursor-1")
    page2 = SimpleNamespace(entries=[SimpleNamespace(path_display="/two.txt")], has_more=False, cursor="cursor-2")
    fake.list_pages = [page1]
    fake.continue_pages["cursor-1"] = page2
    client = DropboxClient(fake)
    files = client.list_files("/folder")
    assert files == ["/one.txt", "/two.txt"]


def test_list_file_metadata_returns_files() -> None:
    fake = FakeDropbox()
    now = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    page1 = SimpleNamespace(
        entries=[SimpleNamespace(path_display="/one.csv", server_modified=now)],
        has_more=False,
        cursor="cursor-1",
    )
    fake.list_pages = [page1]
    client = DropboxClient(fake)
    files = client.list_file_metadata("/folder")
    assert files == [DropboxFileInfo(path="/one.csv", server_modified=now)]


def test_ensure_folder_exists_ignores_conflict(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeDropbox()

    def conflict(_path: str) -> None:
        raise _api_error(conflict=True)

    fake.files_create_folder_v2 = conflict  # type: ignore[assignment]
    client = DropboxClient(fake)
    client.ensure_folder_exists("/folder")


def test_request_with_retry_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DropboxClient(FakeDropbox(), max_retries=2, backoff_factor=1.0)
    sleeps: List[float] = []
    calls = {"count": 0}

    def flaky() -> str:
        calls["count"] += 1
        if calls["count"] <= 2:
            raise RateLimitError("req", backoff=2)
        return "ok"

    monkeypatch.setattr("time.sleep", lambda seconds: sleeps.append(seconds))
    result = client._request_with_retry(flaky)
    assert result == "ok"
    assert sleeps == [2.0, 2.0]


def test_request_with_retry_rate_limit_bad_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DropboxClient(FakeDropbox(), max_retries=1, backoff_factor=1.5)
    sleeps: List[float] = []
    calls = {"count": 0}

    def flaky() -> str:
        calls["count"] += 1
        if calls["count"] == 1:
            raise RateLimitError("req", backoff="oops")
        return "ok"

    monkeypatch.setattr("time.sleep", lambda seconds: sleeps.append(seconds))
    result = client._request_with_retry(flaky)
    assert result == "ok"
    assert sleeps == [1.5]


def test_request_with_retry_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DropboxClient(FakeDropbox(), max_retries=1, backoff_factor=2.0)
    sleeps: List[float] = []
    calls = {"count": 0}

    def flaky() -> str:
        calls["count"] += 1
        if calls["count"] == 1:
            raise HttpError("req", 500, "oops")
        return "ok"

    monkeypatch.setattr("time.sleep", lambda seconds: sleeps.append(seconds))
    result = client._request_with_retry(flaky)
    assert result == "ok"
    assert sleeps == [2.0]


def test_normalize_path_and_helpers() -> None:
    assert _normalize_path("") == ""
    assert _normalize_path("folder") == "/folder"
    assert _is_not_found(object()) is False
    assert _is_conflict(object()) is False


def test_from_settings_uses_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    client = "client"
    monkeypatch.setattr("src.dropbox.client.get_dropbox_client", lambda _settings: client)
    settings = Settings.model_validate(
        {
            "SPOTIFY_CLIENT_ID": "spotify-id",
            "SPOTIFY_CLIENT_SECRET": "spotify-secret",
            "DROPBOX_APP_KEY": "dropbox-key",
            "DROPBOX_APP_SECRET": "dropbox-secret",
            "DROPBOX_REFRESH_TOKEN": "refresh",
        }
    )
    wrapper = DropboxClient.from_settings(settings)
    assert wrapper._client == client


def test_download_file_raises_on_other_error() -> None:
    fake = FakeDropbox()

    def boom(_path: str) -> tuple[object, SimpleNamespace]:
        raise _api_error(not_found=False)

    fake.files_download = boom  # type: ignore[assignment]
    client = DropboxClient(fake)
    with pytest.raises(RuntimeError, match="Dropbox download failed"):
        client.download_file("/boom.txt")


def test_file_exists_raises_on_other_error() -> None:
    fake = FakeDropbox()

    def boom(_path: str) -> object:
        raise _api_error(not_found=False)

    fake.files_get_metadata = boom  # type: ignore[assignment]
    client = DropboxClient(fake)
    with pytest.raises(RuntimeError, match="Dropbox metadata lookup failed"):
        client.file_exists("/boom.txt")


def test_list_files_returns_empty_on_missing() -> None:
    fake = FakeDropbox()

    def missing(_path: str) -> SimpleNamespace:
        raise _api_error(not_found=True)

    fake.files_list_folder = missing  # type: ignore[assignment]
    client = DropboxClient(fake)
    assert client.list_files("/missing") == []


def test_list_file_metadata_returns_empty_on_missing() -> None:
    fake = FakeDropbox()

    def missing(_path: str) -> SimpleNamespace:
        raise _api_error(not_found=True)

    fake.files_list_folder = missing  # type: ignore[assignment]
    client = DropboxClient(fake)
    assert client.list_file_metadata("/missing") == []


def test_ensure_folder_exists_noop_on_empty() -> None:
    client = DropboxClient(FakeDropbox())
    client.ensure_folder_exists("")
