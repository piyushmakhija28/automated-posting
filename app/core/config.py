"""Application settings and environment configuration."""

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import ApiConstants, PlatformConstants


class Settings(BaseSettings):
    """Runtime configuration parsed from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    # Server Configuration
    app_name: str = Field(default=ApiConstants.SERVICE_NAME, alias="APP_NAME")
    app_version: str = Field(default=ApiConstants.SERVICE_VERSION, alias="APP_VERSION")
    app_host: str = Field(default=ApiConstants.DEFAULT_HOST, alias="APP_HOST")
    app_port: int = Field(default=ApiConstants.DEFAULT_PORT, alias="APP_PORT")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Timeouts & Concurrency
    adapter_timeout_seconds: float = Field(
        default=PlatformConstants.DEFAULT_ADAPTER_TIMEOUT_SECONDS,
        alias="ADAPTER_TIMEOUT_SECONDS",
    )
    total_timeout_seconds: float = Field(
        default=PlatformConstants.DEFAULT_TOTAL_TIMEOUT_SECONDS,
        alias="TOTAL_TIMEOUT_SECONDS",
    )
    max_retries: int = Field(
        default=PlatformConstants.DEFAULT_MAX_RETRIES,
        alias="MAX_RETRIES",
    )

    # Platform Credentials (Optional for graceful degradation)
    linkedin_access_token: str | None = Field(default=None, alias="LINKEDIN_ACCESS_TOKEN")
    linkedin_person_urn: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LINKEDIN_PERSON_URN", "LINKEDIN_AUTHOR_URN"),
    )

    devto_api_key: str | None = Field(default=None, alias="DEVTO_API_KEY")

    hashnode_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("HASHNODE_API_KEY", "HASHNODE_ACCESS_TOKEN"),
    )
    hashnode_publication_id: str | None = Field(default=None, alias="HASHNODE_PUBLICATION_ID")

    mastodon_access_token: str | None = Field(default=None, alias="MASTODON_ACCESS_TOKEN")
    mastodon_base_url: str | None = Field(
        default="https://mastodon.social",
        alias="MASTODON_BASE_URL",
    )

    telegram_bot_token: str | None = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    telegram_channel_id: str | None = Field(default=None, alias="TELEGRAM_CHANNEL_ID")
