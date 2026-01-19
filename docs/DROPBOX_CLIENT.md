## Dropbox Client

The Dropbox client wrapper lives in `src/dropbox/client.py`. It wraps the Dropbox SDK to provide simple file operations with retry logic for transient errors.

### How It Works

- Uses `DropboxClient.from_settings()` to build a client from config settings.
- Retries transient API failures (rate limits and temporary HTTP errors) with exponential backoff.
- Normalizes Dropbox paths so both `/path` and `path` are accepted.
- Handles missing files gracefully (returns `None` or `False`).

### Supported Operations

- `upload_file(content: str, path: str) -> None`
  - Uploads or overwrites a file.
- `download_file(path: str) -> Optional[str]`
  - Downloads a file as UTF-8 text; returns `None` if missing.
- `file_exists(path: str) -> bool`
  - Returns `True` if the file exists.
- `list_files(folder: str) -> list[str]`
  - Lists files in a folder (non-recursive).
- `ensure_folder_exists(path: str) -> None`
  - Creates the folder if it doesn't exist.

### Usage Example

```python
from src.config import load_settings
from src.dropbox.client import DropboxClient

settings = load_settings()
client = DropboxClient.from_settings(settings)

client.ensure_folder_exists("/spotify-backups")
client.upload_file("hello", "/spotify-backups/example.txt")

content = client.download_file("/spotify-backups/example.txt")
print(content)
```

### Notes

- Requires a refresh token (see `docs/DROPBOX_AUTH.md`).
- Files are uploaded with overwrite mode to simplify backups.
