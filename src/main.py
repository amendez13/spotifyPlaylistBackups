"""CLI entry point for spotifyPlaylistBackups."""

from __future__ import annotations

from typing import Callable, TypeVar, cast

import typer

APP_HELP = "Backup and export Spotify playlists to JSON."

app = typer.Typer(help=APP_HELP)

CommandFunc = TypeVar("CommandFunc", bound=Callable[..., object])


def typer_callback(func: CommandFunc) -> CommandFunc:
    """Typed wrapper around the Typer callback decorator."""
    return cast(Callable[[CommandFunc], CommandFunc], app.callback())(func)


def typer_command(func: CommandFunc) -> CommandFunc:
    """Typed wrapper around the Typer command decorator."""
    return cast(Callable[[CommandFunc], CommandFunc], app.command())(func)


@typer_callback
def cli() -> None:
    """Backup and export Spotify playlists to JSON."""
    return None


@typer_command
def info() -> None:
    """Display a placeholder message for the CLI."""
    typer.echo("spotifyPlaylistBackups CLI is under construction.")


def main() -> None:
    """Run the CLI."""
    app()


if __name__ == "__main__":
    main()
