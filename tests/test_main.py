"""Tests for the CLI entry point."""

import sys

import pytest
from typer.testing import CliRunner

from src.main import APP_HELP, app, main


class TestCli:
    """Tests for the Typer CLI."""

    def test_cli_help_includes_description(self) -> None:
        """Ensure the CLI help text shows the app description."""
        runner = CliRunner()
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert APP_HELP in result.output

    def test_info_command_output(self) -> None:
        """Ensure the info command outputs the placeholder message."""
        runner = CliRunner()
        result = runner.invoke(app, ["info"])
        assert result.exit_code == 0
        assert "under construction" in result.output


class TestMain:
    """Tests for the module entry point."""

    def test_main_runs_cli_help(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Ensure main() forwards to the CLI."""
        monkeypatch.setattr(sys, "argv", ["main", "--help"])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
