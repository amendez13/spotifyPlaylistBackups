## Spotify Authentication

The Spotify authentication module lives in `src/spotify/auth.py`. It uses Spotipy's OAuth helper to manage browser-based login and token caching.

### How It Works

1. The module builds a `SpotifyOAuth` instance with the required scopes:
   - `playlist-read-private`
   - `playlist-read-collaborative`
   - `user-library-read`
2. Tokens are cached locally using the path from `TOKEN_STORAGE_PATH` (defaults to `.spotify_token.json`).
3. If a cached token exists, it is validated and refreshed automatically via `validate_token`.
4. If no valid token is available, the module opens a browser URL and prompts for the redirect URL.

### Key Functions

- `get_spotify_client(settings: Settings) -> spotipy.Spotify`
  - Returns an authenticated Spotipy client.
  - Reuses cached tokens when possible.
  - Prompts for browser auth when needed.
- `is_authenticated(settings: Optional[Settings] = None) -> bool`
  - Returns `True` when a valid cached token exists.

### Configuration Inputs

The module expects these settings (via YAML or env vars):

- `SPOTIFY_CLIENT_ID`
- `SPOTIFY_CLIENT_SECRET`
- `SPOTIFY_REDIRECT_URI` (default: `http://localhost:8888/callback`)
- `TOKEN_STORAGE_PATH` (default: `.spotify_token.json`)

### Usage Example

```python
from src.config import load_settings
from src.spotify.auth import get_spotify_client, is_authenticated

settings = load_settings()

if not is_authenticated(settings):
    print("Spotify auth required; browser window will open.")

client = get_spotify_client(settings)
profile = client.current_user()
print(profile["id"])
```

### Error Handling

Authentication errors raise `RuntimeError` with a clear message, for example:

- Missing redirect URL
- Unable to parse authorization code
- Empty token response
