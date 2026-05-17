#!/usr/bin/env python3
"""Authorize Dropbox and store refresh token in config."""

from __future__ import annotations

import sys
import webbrowser

from pydantic import ValidationError

from src.config import load_settings
from src.config.settings import CONFIG_PATH_ENV, DEFAULT_CONFIG_PATH
from src.dropbox.auth import finish_auth_flow, start_auth_flow


def main() -> None:
    print("=" * 72)
    print("Dropbox Authorization")
    print("=" * 72)
    try:
        settings = load_settings()
    except ValidationError as exc:
        config_path = DEFAULT_CONFIG_PATH
        print("Configuration error while loading settings.")
        print(f"Expected config at {config_path} (or set {CONFIG_PATH_ENV}).")
        print(str(exc))
        sys.exit(1)

    auth_url = start_auth_flow(settings)
    print("\nOpen this URL in your browser and authorize the app:")
    print(f"\n{auth_url}\n")
    try:
        webbrowser.open(auth_url, new=2, autoraise=True)
    except Exception:
        pass
    auth_code = input("Paste the authorization code from Dropbox: ").strip()
    try:
        finish_auth_flow(auth_code, settings)
    except RuntimeError as exc:
        print(f"\nError: {exc}")
        sys.exit(1)

    print("\nRefresh token saved to config. Dropbox auth is ready.")


if __name__ == "__main__":
    main()
