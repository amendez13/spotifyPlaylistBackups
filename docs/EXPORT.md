## CSV Export

The CSV export helpers live in `src/backup/exporter.py` and are designed to produce spreadsheet-friendly output.

### CSV Schema

Exports use a fixed column order:

```
track_id,track_name,artists,album,album_release_date,added_at,added_by,duration_ms,is_local
```

### How Rows Are Built

- `artists` is a comma-separated list of artist names in the order returned by Spotify.
- `added_at` is serialized as ISO 8601 with `Z` for UTC (e.g., `2024-01-01T12:00:00Z`).
- `album_release_date` is passed through as provided by the API (string or empty).
- `is_local` is taken from the Track model (local files are typically filtered earlier by the client).

### Encoding and Escaping

- The CSV string is prefixed with a UTF-8 BOM (`\ufeff`) so Excel opens it correctly.
- Fields are escaped via Python's `csv.DictWriter`, which safely quotes commas, quotes, and newlines.

### Filename Generation

`generate_filename()` creates a safe filename by:

- Removing invalid filesystem characters (`\\ / : * ? " < > |`).
- Collapsing repeated whitespace.
- Appending the playlist id to avoid collisions.

Example output: `My Playlist-abc123.csv`.

### Usage

```python
from src.backup.exporter import generate_filename, playlist_to_csv
from src.spotify.client import SpotifyClient
from src.config import load_settings

settings = load_settings()
client = SpotifyClient.from_settings(settings)

playlists = client.get_all_playlists()
playlist = playlists[0]

csv_text = playlist_to_csv(playlist)
filename = generate_filename(playlist)

with open(filename, "w", encoding="utf-8") as handle:
    handle.write(csv_text)
```
