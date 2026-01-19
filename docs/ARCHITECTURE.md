# Architecture Documentation

This document describes the technical architecture of spotifyPlaylistBackups.

## Overview

spotifyPlaylistBackups fetches Spotify playlists, converts them to CSV, and uploads the results to Dropbox. The system is split into configuration management, API clients, and a backup orchestration layer.

## System Components

### Component Diagram

```
┌──────────────────┐
│  CLI (Typer)     │
└────────┬─────────┘
         ▼
┌────────────────────┐     ┌──────────────────────┐
│  Config Settings   │────▶│    Backup Service    │
└────────────────────┘     └──────────┬───────────┘
                                     │
                     ┌───────────────┴───────────────┐
                     ▼                               ▼
           ┌──────────────────┐            ┌──────────────────┐
           │ Spotify Client   │            │ Dropbox Client   │
           └──────────────────┘            └──────────────────┘
                     │                               │
                     ▼                               ▼
           ┌──────────────────┐            ┌──────────────────┐
           │ CSV Exporter     │            │ Dropbox Storage  │
           └──────────────────┘            └──────────────────┘
```

### Config Settings

**Purpose**: Load settings from YAML and environment variables.

**Responsibilities**:
- Provide Spotify and Dropbox credentials
- Provide backup folder and CSV delimiter configuration

**Key Files**:
- `src/config/settings.py`

### Spotify Integration

**Purpose**: Authenticate and fetch playlist data.

**Responsibilities**:
- OAuth token handling (`src/spotify/auth.py`)
- Playlist and track retrieval (`src/spotify/client.py`)
- Data modeling (`src/spotify/models.py`)

### Dropbox Integration

**Purpose**: Authenticate and store backup artifacts.

**Responsibilities**:
- OAuth token handling (`src/dropbox/auth.py`)
- File upload and folder management (`src/dropbox/client.py`)

### Backup Service

**Purpose**: Orchestrate full playlist backups.

**Responsibilities**:
- Iterate over playlists
- Convert tracks to CSV (`src/backup/exporter.py`)
- Upload files to Dropbox (`src/dropbox/client.py`)

**Key Files**:
- `src/backup/service.py`

### CLI Entry Point

**Purpose**: Provide the user-facing command interface.

**Responsibilities**:
- Parse global flags like `--config`, `--verbose`, and `--dry-run`
- Load settings and configure logging
- Trigger OAuth flows for Spotify and Dropbox
- Dispatch backup, sync, list, and status commands

**Key Files**:
- `src/main.py`

## Data Flow

1. CLI command resolves settings and logging configuration.
2. Load settings via `load_settings()`.
3. Create `SpotifyClient` and `DropboxClient`.
4. `BackupService` fetches playlists and tracks.
5. `CSVExporter` generates per-playlist CSV output.
6. Dropbox client uploads the CSV into the backup folder.

### CLI Workflow

1. CLI parses command-line arguments and options.
2. `--config` overrides the YAML path via `SPOTIFY_BACKUPS_CONFIG_PATH`.
3. The CLI constructs clients and `BackupService`.
4. Commands emit colored status output and handle errors.

### Sync Workflow

1. Fetch current playlist data from Spotify.
2. Download existing CSV from Dropbox (if present).
3. Parse existing track ids and detect new tracks.
4. Append new rows and upload the updated CSV.

### Usage Example

```python
from src.backup.exporter import CSVExporter
from src.backup.service import BackupService
from src.config import load_settings
from src.dropbox.client import DropboxClient
from src.spotify.client import SpotifyClient

settings = load_settings()
spotify_client = SpotifyClient.from_settings(settings)
dropbox_client = DropboxClient.from_settings(settings)
exporter = CSVExporter()

service = BackupService(spotify_client, dropbox_client, exporter, settings)
result = service.backup_all_playlists()
print(result.successful, result.failed)

sync_result = service.sync_all_playlists()
print(sync_result.playlists_updated, sync_result.total_new_tracks)
```

### CLI Example

```bash
spotify-backup auth spotify
spotify-backup auth dropbox
spotify-backup backup
spotify-backup sync
```

## Design Decisions

### Decision 1: OAuth with refresh tokens

**Context**: Long-lived automation requires stable authentication.

**Decision**: Use refresh-token based OAuth flows for Spotify and Dropbox.

**Consequences**:
- Pro: Automatic token refresh without user re-authentication.
- Con: Requires storing refresh tokens securely.

### Decision 2: CSV export with BOM

**Context**: Backups should be easily opened in spreadsheets.

**Decision**: Prefix CSV output with a UTF-8 BOM.

**Consequences**:
- Pro: Excel opens files without encoding issues.
- Con: Adds extra bytes for non-spreadsheet consumers.

## Performance Considerations

- Pagination is handled by the Spotify and Dropbox clients to avoid large payloads.
- Rate limiting is retried with exponential backoff.

## Security Considerations

- Refresh tokens are stored in `config/config.yaml` (gitignored).
- OAuth flows use PKCE where supported.

## Future Enhancements

- [ ] Incremental backups based on playlist snapshot IDs
- [ ] Parallel exports for large libraries
