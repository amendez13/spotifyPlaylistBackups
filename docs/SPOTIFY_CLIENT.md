## Spotify Client and Models

The Spotify client wrapper and data models live in `src/spotify/client.py` and `src/spotify/models.py`. They provide typed, validated access to Spotify playlists and tracks with pagination and rate-limit handling.

### Data Models

Models are simple Pydantic classes with `from_api` constructors:

- `Artist`: `id`, `name`
- `Album`: `id`, `name`, `release_date`
- `Track`: `id`, `name`, `artists`, `album`, `duration_ms`, `added_at`, `added_by`, `is_local`
- `Playlist`: `id`, `name`, `description`, `owner`, `tracks`, `snapshot_id`, `total_tracks`

`Track.from_api()` parses Spotify playlist item payloads and converts timestamps to `datetime`.
`Playlist.from_api()` accepts the raw playlist data plus a list of `Track` objects.

### Client Wrapper

`SpotifyClient` wraps a Spotipy client and adds:

- Pagination for playlists and track items.
- Rate-limit retry with exponential backoff (honors `Retry-After`).
- Filtering of local tracks (`is_local == true`).

Key methods:

- `get_all_playlists() -> list[Playlist]`
- `get_playlist_tracks(playlist_id: str) -> list[Track]`
- `get_user_info() -> dict`

### Usage Example

```python
from src.config import load_settings
from src.spotify.client import SpotifyClient

settings = load_settings()
client = SpotifyClient.from_settings(settings)

playlists = client.get_all_playlists()
first = playlists[0]
print(first.name, first.total_tracks)

tracks = client.get_playlist_tracks(first.id)
print(tracks[0].name)
```

### Notes

- The client expects valid Spotify credentials and token cache (see `docs/SPOTIFY_AUTH.md`).
- Local tracks are skipped to avoid missing metadata in exports.
