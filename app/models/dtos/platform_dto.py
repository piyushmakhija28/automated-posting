"""Platform result DTO transfer model."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PlatformResultDto(BaseModel):
    """Itemized outcome representation for a single social or developer platform."""

    model_config = ConfigDict(
        frozen=True,
        extra="ignore",
    )

    platform: str = Field(..., description="Unique platform identifier (e.g. linkedin, devto).")
    status: Literal["success", "failed", "skipped"] = Field(..., description="Execution status.")
    post_id: str | None = Field(
        default=None, description="External identifier assigned by platform."
    )
    post_url: str | None = Field(
        default=None, description="Direct URL to published post if available."
    )
    error: str | None = Field(default=None, description="Sanitized human-readable error if failed.")
    latency_ms: float | None = Field(
        default=None, description="Execution duration in milliseconds."
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC completion timestamp.",
    )
