## Configuration Management

The configuration module lives in `src/config/settings.py` and uses `pydantic-settings` to load values from YAML and environment variables.

### How It Works

- The default config file path is `config/config.yaml`.
- You can override the path with `SPOTIFY_BACKUPS_CONFIG_PATH`.
- Environment variables take precedence over YAML values.
- Required fields are validated at load time by Pydantic.

### Expected YAML Structure

```yaml
spotify:
  client_id: REPLACE_WITH_SPOTIFY_CLIENT_ID
  client_secret: REPLACE_WITH_SPOTIFY_CLIENT_SECRET
  redirect_uri: http://localhost:8888/callback

dropbox:
  app_key: REPLACE_WITH_DROPBOX_APP_KEY
  app_secret: REPLACE_WITH_DROPBOX_APP_SECRET
  # refresh_token: REPLACE_WITH_DROPBOX_REFRESH_TOKEN

backup:
  folder: /spotify-backups
  csv_delimiter: ","

tokens:
  storage_path: .spotify_token.json
```

### Environment Overrides

Each setting can be overridden via env vars:

- `SPOTIFY_CLIENT_ID`
- `SPOTIFY_CLIENT_SECRET`
- `SPOTIFY_REDIRECT_URI`
- `DROPBOX_APP_KEY`
- `DROPBOX_APP_SECRET`
- `DROPBOX_REFRESH_TOKEN`
- `BACKUP_FOLDER`
- `CSV_DELIMITER`
- `TOKEN_STORAGE_PATH`
- `SPOTIFY_BACKUPS_CONFIG_PATH`

### Usage Example

```python
from src.config import load_settings

settings = load_settings()
print(settings.spotify_client_id)
```

### Error Handling

Missing required fields raise a `ValidationError` with details about which config keys are missing.
