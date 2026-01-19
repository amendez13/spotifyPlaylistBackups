"""CLI entry point for spotifyPlaylistBackups."""

from __future__ import annotations

import typer

APP_HELP = "Backup and export Spotify playlists to JSON."

app = typer.Typer(help=APP_HELP)


# Typer decorators are untyped; ignore misc to keep strict mypy on.
@app.callback()  # type: ignore[misc]
def cli() -> None:
    """Backup and export Spotify playlists to JSON."""
    return None


# Typer decorators are untyped; ignore misc to keep strict mypy on.
@app.command()  # type: ignore[misc]
def info() -> None:
    """Display a placeholder message for the CLI."""
    typer.echo("spotifyPlaylistBackups CLI is under construction.")


def main() -> None:
    """Run the CLI."""
    app()


if __name__ == "__main__":
    main()
