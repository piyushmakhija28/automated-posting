"""Health and readiness SRE probe response DTO models."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import ApiConstants


class HealthResponseDto(BaseModel):
    """Liveness probe response model indicating process responsiveness."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    status: str = Field(
        default="ok",
        description="Process liveness state.",
        examples=["ok"],
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="ISO-8601 UTC timestamp of the health check probe.",
    )
    version: str = Field(
        default=ApiConstants.SERVICE_VERSION,
        description="Semantic application version.",
        examples=["1.0.0"],
    )


class AdapterStatusDto(BaseModel):
    """Configuration availability flags for each target platform adapter."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    linkedin: bool = Field(default=False, description="LinkedIn credentials configuration status.")
    devto: bool = Field(default=False, description="Dev.to API key configuration status.")
    hashnode: bool = Field(default=False, description="Hashnode credentials configuration status.")
    mastodon: bool = Field(default=False, description="Mastodon instance configuration status.")
    telegram: bool = Field(default=False, description="Telegram bot and channel configuration status.")


class ReadinessResponseDto(BaseModel):
    """Readiness probe response model detailing platform readiness and connection state."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    status: str = Field(
        default="ready",
        description="Application readiness status.",
        examples=["ready"],
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="ISO-8601 UTC timestamp of the readiness probe.",
    )
    version: str = Field(
        default=ApiConstants.SERVICE_VERSION,
        description="Semantic application version.",
        examples=["1.0.0"],
    )
    platforms_configured: int = Field(
        default=0,
        description="Count of external platform adapters with valid credentials.",
        examples=[5],
    )
    adapters: AdapterStatusDto = Field(
        default_factory=AdapterStatusDto,
        description="Itemized configuration availability per platform adapter.",
    )
