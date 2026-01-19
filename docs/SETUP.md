# Setup Guide

This guide walks you through setting up spotifyPlaylistBackups for development or usage.

## Prerequisites

- Python 3.10 or higher
- pip (Python package installer)
- git

### Optional

- [List optional dependencies]

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/amendez13/spotifyPlaylistBackups.git
cd spotifyPlaylistBackups
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate   # On Windows
```

### 3. Install Dependencies

```bash
# Install production dependencies
pip install -r requirements.txt

# Install development dependencies (optional)
pip install -r requirements-dev.txt
```

### 4. Configure the Application

```bash
# Copy example configuration
cp config/config.example.yaml config/config.yaml

# Edit configuration with your settings
# On macOS/Linux:
nano config/config.yaml
# Or use your preferred editor
```

### 5. Verify Installation

```bash
# Run tests to verify setup
pytest

# Or run the application
python -m src.main --help
```

## Configuration

### config/config.yaml

The main configuration file. See `config/config.example.yaml` for all available options.

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

### Environment Variables

You can also configure the application using environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `SPOTIFY_CLIENT_ID` | Spotify client ID | required |
| `SPOTIFY_CLIENT_SECRET` | Spotify client secret | required |
| `SPOTIFY_REDIRECT_URI` | Spotify redirect URI | `http://localhost:8888/callback` |
| `DROPBOX_APP_KEY` | Dropbox app key | required |
| `DROPBOX_APP_SECRET` | Dropbox app secret | required |
| `DROPBOX_REFRESH_TOKEN` | Dropbox refresh token | empty |
| `BACKUP_FOLDER` | Remote backup folder | `/spotify-backups` |
| `CSV_DELIMITER` | CSV delimiter | `,` |
| `TOKEN_STORAGE_PATH` | Token cache path | `.spotify_token.json` |
| `SPOTIFY_BACKUPS_CONFIG_PATH` | Path to config YAML | `config/config.yaml` |

### Spotify Authentication

On first use, the CLI will open a browser window for Spotify OAuth consent. After approving access, paste the redirect URL back into the prompt. Tokens are cached locally at `.spotify_token.json` (or the path in `TOKEN_STORAGE_PATH`).

### Dropbox Authentication

Run the Dropbox authorization helper to obtain a refresh token and store it in `config/config.yaml`:

```bash
python scripts/authorize_dropbox.py
```

See [DROPBOX_AUTH.md](DROPBOX_AUTH.md) for details.

## Development Setup

### Install Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install

# Verify hooks work
pre-commit run --all-files
```

### IDE Setup

#### VS Code

Recommended extensions:
- Python
- Pylance
- Black Formatter
- isort

Settings (`.vscode/settings.json`):
```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.formatting.provider": "black",
    "editor.formatOnSave": true,
    "[python]": {
        "editor.codeActionsOnSave": {
            "source.organizeImports": true
        }
    }
}
```

#### PyCharm

1. Set Python interpreter to `./venv/bin/python`
2. Enable Black formatter
3. Enable isort for imports

## Troubleshooting

### Common Issues

**Virtual environment not activated**
```bash
source venv/bin/activate
```

**Dependencies not installed**
```bash
pip install -r requirements.txt
```

**Pre-commit hooks not running**
```bash
pre-commit install
```

**Configuration file not found**
```bash
cp config/config.example.yaml config/config.yaml
```

### Getting Help

- Check the [Documentation Index](INDEX.md)
- Review [CI documentation](CI.md) for testing issues
- Open an issue on GitHub
