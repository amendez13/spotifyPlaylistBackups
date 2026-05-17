# spotifyPlaylistBackups

![CI](https://github.com/amendez13/spotifyPlaylistBackups/workflows/CI/badge.svg)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Coverage](https://img.shields.io/badge/coverage-95%25-green.svg)

Backup and sync Spotify playlists to CSV files in Dropbox.

## Features

- Typer-based CLI with auth, backup, sync, list, and status commands
- YAML configuration with environment variable overrides
- Spotify and Dropbox OAuth helpers
- CSV exports with Excel-friendly BOM and safe filenames
- Sync workflow that appends only new tracks
- Dry-run support for planning changes without writes
- Strong test coverage and pre-commit enforcement

## Quick Start

### Prerequisites

- Python 3.10 or higher
- pip (Python package installer)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/amendez13/spotifyPlaylistBackups.git
cd spotifyPlaylistBackups
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate   # On Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure the application:
```bash
cp config/config.example.yaml config/config.yaml
# Edit config/config.yaml with your settings
```

5. Authenticate and run a backup:
```bash
python -m src.main auth spotify
python -m src.main auth dropbox
python -m src.main backup
```

## Usage

```bash
# Show available commands
python -m src.main --help

# Backup all playlists
python -m src.main backup

# Backup a single playlist by name or id
python -m src.main backup --playlist "Chill Vibes"

# Sync playlists (only new tracks)
python -m src.main sync

# List playlists (add -v for counts)
python -m src.main list -v

# Show backup status
python -m src.main status
```

### Output Example

```text
Backing up playlists:
[OK] Chill Vibes (45 tracks) -> /spotify-backups/Chill Vibes-abc123.csv
[OK] Workout Mix (78 tracks) -> /spotify-backups/Workout Mix-def456.csv
Backup complete: 2/2 successful
```

## Configuration

Configuration lives in `config/config.yaml` and can be overridden with env vars.
See `config/config.example.yaml` for the full schema and `docs/SETUP.md` for setup details.

## Documentation

- [Documentation Index](docs/INDEX.md)
- [Setup Guide](docs/SETUP.md)
- [Usage Guide](docs/USAGE.md)
- [Architecture](docs/ARCHITECTURE.md)

## Project Structure

```
spotifyPlaylistBackups/
├── .github/workflows/    # CI/CD configuration
├── config/               # Configuration files
├── docs/                 # Documentation
├── scripts/              # Helper scripts
├── src/                  # Source code
│   ├── backup/           # Backup and sync services
│   ├── config/           # Settings loading
│   ├── dropbox/          # Dropbox auth and client
│   └── spotify/          # Spotify auth, client, and models
├── tests/                # Test suite
├── CLAUDE.md             # AI assistant guidance
├── README.md             # This file
├── pyproject.toml        # Tool configuration
└── requirements.txt      # Dependencies
```

## Development

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run tests
pytest

# Run pre-commit checks
pre-commit run --all-files
```

## License

License not specified yet.
