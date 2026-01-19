# spotifyPlaylistBackups

![CI](https://github.com/amendez13/spotifyPlaylistBackups/workflows/CI/badge.svg)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Coverage](https://img.shields.io/badge/coverage-95%25-green.svg)

Backup and export Spotify playlists to JSON

## Features

- Typer-based CLI scaffold
- YAML configuration template for Spotify and Dropbox credentials
- Spotify OAuth client wrapper and playlist data models
- Dropbox OAuth helper for token persistence
- Dropbox client wrapper for file operations
- CSV export utilities for playlist backups
- Test and quality tooling wired into CI

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

2. Create and activate virtual environment:
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

### Usage

```bash
# Run the application
python -m src.main --help

# Placeholder command
python -m src.main info
```

On first Spotify-enabled command run, the app will open a browser for OAuth consent and cache tokens in `.spotify_token.json`.

## Configuration

Configuration is stored in `config/config.yaml`. See `config/config.example.yaml` for all available options.

```yaml
# Example configuration
app:
  debug: false
  log_level: INFO

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

## Project Structure

```
spotifyPlaylistBackups/
├── .github/workflows/    # CI/CD configuration
├── .claude/              # Claude Code configuration
├── config/               # Configuration files
├── docs/                 # Documentation
├── src/                  # Source code
│   ├── backup/           # Backup logic (placeholder)
│   ├── config/           # Settings and config helpers (placeholder)
│   ├── dropbox/          # Dropbox integration (placeholder)
│   └── spotify/          # Spotify integration (placeholder)
├── tests/                # Test files
├── CLAUDE.md             # AI assistant guidance
├── README.md             # This file
├── pyproject.toml        # Tool configuration
└── requirements.txt      # Dependencies
```

## Development

### Setup Development Environment

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=term-missing
```

### Code Quality

This project uses:
- **Black** for code formatting
- **isort** for import sorting
- **flake8** for linting
- **mypy** for type checking
- **bandit** for security scanning
- **pip-audit** for dependency vulnerability checking

All checks run automatically via pre-commit hooks and CI.

## CI/CD

GitHub Actions runs the following checks on every push and PR:

1. **Lint**: Black, isort, flake8, mypy
2. **Test**: pytest across Python 3.10, 3.11, 3.12
3. **Coverage**: 95% minimum coverage
4. **Security**: bandit and pip-audit

See [docs/CI.md](docs/CI.md) for details.

## Documentation

- [Documentation Index](docs/INDEX.md) - All documentation
- [Setup Guide](docs/SETUP.md) - Installation and configuration
- [CI Documentation](docs/CI.md) - CI/CD pipeline details

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting
5. Commit your changes (`git commit -m 'feat: add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

[Choose your license]

## Acknowledgments

- [Acknowledgment 1]
- [Acknowledgment 2]
