# Usage Guide

This guide covers CLI commands, common workflows, automation, and troubleshooting.

## Command Reference

All commands are available via:

```bash
python -m src.main --help
```

### Global Options

| Option | Description |
|--------|-------------|
| `--config PATH` | Use a custom config file path |
| `--verbose`, `-v` | Enable verbose logging |
| `--dry-run` | Show actions without writing to Dropbox |

### Auth Commands

```bash
python -m src.main auth spotify
python -m src.main auth dropbox
python -m src.main auth status
```

- `auth spotify` opens the browser and stores tokens in `.spotify_token.json`.
- `auth dropbox` walks through OAuth and stores the refresh token in `config/config.yaml`.
- `auth status` shows token availability.

### Backup Commands

```bash
python -m src.main backup
python -m src.main backup --playlist "Chill Vibes"
```

- `backup` exports all playlists to CSV and uploads to Dropbox.
- `backup --playlist` targets a single playlist by name or id.

### Sync Commands

```bash
python -m src.main sync
```

- `sync` downloads existing CSVs, detects new tracks, and appends only new rows.

### Info Commands

```bash
python -m src.main list
python -m src.main list -v
python -m src.main status
```

- `list` shows playlists; `-v` adds track counts.
- `status` reports the latest Dropbox backup timestamp.

## Common Workflows

### First-Time Setup

```bash
python -m src.main auth spotify
python -m src.main auth dropbox
python -m src.main backup
```

### Weekly Sync

```bash
python -m src.main sync
```

### Safe Preview (Dry Run)

```bash
python -m src.main --dry-run backup
python -m src.main --dry-run sync
```

## Automation

### Linux/macOS (cron)

```cron
# Sync every Sunday at 02:30
30 2 * * 0 /path/to/repo/venv/bin/python -m src.main sync --config /path/to/config.yaml
```

### macOS (launchd)

Create `~/Library/LaunchAgents/com.spotify.backup.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>com.spotify.backup</string>
    <key>ProgramArguments</key>
    <array>
      <string>/path/to/repo/venv/bin/python</string>
      <string>-m</string>
      <string>src.main</string>
      <string>sync</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
      <key>Weekday</key>
      <integer>1</integer>
      <key>Hour</key>
      <integer>2</integer>
      <key>Minute</key>
      <integer>30</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/tmp/spotify-backup.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/spotify-backup.err</string>
  </dict>
</plist>
```

Load it:

```bash
launchctl load ~/Library/LaunchAgents/com.spotify.backup.plist
```

## Troubleshooting

**Spotify auth fails or redirect URI mismatch**
- Confirm the redirect URI matches `http://localhost:8888/callback` in the Spotify dashboard and config.

**Dropbox auth fails or token missing**
- Re-run `python -m src.main auth dropbox` and ensure the refresh token is saved.

**Rate limit errors**
- Re-run later; the Spotify/Dropbox clients retry automatically with backoff.

**Config file errors**
- Validate `config/config.yaml` matches `config/config.example.yaml`.

**Unexpected playlist duplicates**
- Use playlist IDs when `backup --playlist` reports multiple matches.
