"""Configuration management for spotifyPlaylistBackups."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from pydantic import AliasChoices, AliasPath, Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict
from pydantic_settings.sources import YamlConfigSettingsSource

CONFIG_PATH_ENV = "SPOTIFY_BACKUPS_CONFIG_PATH"
DEFAULT_CONFIG_PATH = Path("config/config.yaml")

SettingsSource = PydanticBaseSettingsSource


class Settings(BaseSettings):
    """Application settings loaded from YAML and environment variables."""

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_prefix="",
    )

    spotify_client_id: str = Field(
        validation_alias=AliasChoices(
            "SPOTIFY_CLIENT_ID",
            AliasPath("spotify", "client_id"),
        )
    )
    spotify_client_secret: str = Field(
        validation_alias=AliasChoices(
            "SPOTIFY_CLIENT_SECRET",
            AliasPath("spotify", "client_secret"),
        )
    )
    spotify_redirect_uri: str = Field(
        default="http://localhost:8888/callback",
        validation_alias=AliasChoices(
            "SPOTIFY_REDIRECT_URI",
            AliasPath("spotify", "redirect_uri"),
        ),
    )

    dropbox_app_key: str = Field(
        validation_alias=AliasChoices(
            "DROPBOX_APP_KEY",
            AliasPath("dropbox", "app_key"),
        )
    )
    dropbox_app_secret: str = Field(
        validation_alias=AliasChoices(
            "DROPBOX_APP_SECRET",
            AliasPath("dropbox", "app_secret"),
        )
    )
    dropbox_refresh_token: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "DROPBOX_REFRESH_TOKEN",
            AliasPath("dropbox", "refresh_token"),
        ),
    )

    backup_folder: str = Field(
        default="/spotify-backups",
        validation_alias=AliasChoices(
            "BACKUP_FOLDER",
            AliasPath("backup", "folder"),
        ),
    )
    csv_delimiter: str = Field(
        default=",",
        validation_alias=AliasChoices(
            "CSV_DELIMITER",
            AliasPath("backup", "csv_delimiter"),
        ),
    )
    token_storage_path: str = Field(
        default=".spotify_token.json",
        validation_alias=AliasChoices(
            "TOKEN_STORAGE_PATH",
            AliasPath("tokens", "storage_path"),
        ),
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: SettingsSource,
        env_settings: SettingsSource,
        dotenv_settings: SettingsSource,
        file_secret_settings: SettingsSource,
    ) -> tuple[SettingsSource, ...]:
        config_path = Path(os.getenv(CONFIG_PATH_ENV, str(DEFAULT_CONFIG_PATH)))
        yaml_settings = YamlConfigSettingsSource(settings_cls, yaml_file=config_path)
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            yaml_settings,
            file_secret_settings,
        )


def load_settings() -> Settings:
    """Convenience wrapper for loading settings."""
    return Settings()  # type: ignore[call-arg]
