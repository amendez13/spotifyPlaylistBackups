## Dropbox Authentication

The Dropbox authentication module lives in `src/dropbox/auth.py`. It uses the Dropbox SDK OAuth2 flow to obtain a refresh token and then relies on automatic token refresh for API calls.

### How It Works

1. `start_auth_flow()` creates a Dropbox OAuth URL with the required scopes:
   - `files.content.write`
   - `files.content.read`
2. The user authorizes the app and receives a short authorization code.
3. `finish_auth_flow()` exchanges the code for a refresh token.
4. The refresh token is stored in `config/config.yaml` (or the path in `SPOTIFY_BACKUPS_CONFIG_PATH`).
5. `get_dropbox_client()` uses the refresh token to create a Dropbox client that auto-refreshes access tokens.

### Authorization Script

Run the helper script to complete the flow:

```bash
python scripts/authorize_dropbox.py
```

This will open a browser window, prompt for the authorization code, and save the refresh token into your config file.

### Usage Example

```python
from src.config import load_settings
from src.dropbox.auth import get_dropbox_client, is_authenticated

settings = load_settings()

if not is_authenticated(settings):
    raise RuntimeError("Dropbox refresh token missing; run scripts/authorize_dropbox.py")

client = get_dropbox_client(settings)
account = client.users_get_current_account()
print(account.name.display_name)
```

### Error Handling

Authentication failures raise `RuntimeError` with clear messages (missing code, missing refresh token, or exchange failures).
