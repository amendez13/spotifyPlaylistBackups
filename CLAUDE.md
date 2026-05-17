# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Backup and sync Spotify playlists to CSV files stored in Dropbox.

**Core workflow**:
1. Load settings from `config/config.yaml` (or env overrides).
2. Authenticate with Spotify and Dropbox.
3. Fetch playlists and tracks from Spotify.
4. Export tracks to CSV (with BOM for Excel compatibility).
5. Upload CSVs to Dropbox (backup) or append new tracks (sync).

## Constraints and Best Practices

- This project is documentation-driven. Before starting work, read:
  - `README.md`
  - `docs/INDEX.md`
- After finishing any task, update relevant documentation given changes in codebase.
- Pre-commit checks must pass before committing. If pre-commit doesn't run, investigate and fix.
- `pyproject.toml`, `.github/workflows/ci.yml`, and `.pre-commit-config.yaml` should stay aligned.
- Any code quality exceptions must be properly documented with a comment in code.
- Branch naming: `feature/description`, `fix/description`, `docs/description`
- Commit messages: Use conventional commits (feat:, fix:, docs:, refactor:, test:, chore:)

## Architecture

### Technology Stack
- **Python**: 3.10+
- **Typer**: CLI framework
- **Spotipy**: Spotify API wrapper
- **Dropbox SDK**: Dropbox API access
- **Pydantic**: Settings validation

### Key Components
1. **CLI (`src/main.py`)**:
   - Parses global options and dispatches commands.
   - Handles auth, backup, sync, list, and status.
2. **Backup Service (`src/backup/service.py`)**:
   - Orchestrates backups and syncs.
   - Generates filenames and calls Dropbox client.
3. **Export Helpers (`src/backup/exporter.py`)**:
   - CSV formatting and BOM handling.
4. **Spotify Client (`src/spotify/client.py`)**:
   - Playlist/track retrieval with pagination and backoff.
5. **Dropbox Client (`src/dropbox/client.py`)**:
   - Upload, download, list metadata, and retries.

### Processing Strategy
- Full backups export all tracks per playlist into CSV files.
- Sync compares current Spotify tracks to existing CSV track IDs and appends new tracks only.
- Logging is configured by the CLI (`--verbose`).

## Development Commands

### Initial Setup

```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate  # Windows

pip install -r requirements.txt
pip install -r requirements-dev.txt
pre-commit install

cp config/config.example.yaml config/config.yaml
# Edit config/config.yaml with your settings
```

### Running Tests

```bash
pytest
pytest --cov=src --cov-report=term-missing
pytest tests/test_main.py
```

### Code Quality

```bash
pre-commit run --all-files
```

### Running the Application

```bash
python -m src.main --help
python -m src.main auth spotify
python -m src.main auth dropbox
python -m src.main backup
python -m src.main sync
```
