"""Platform result DTO transfer model matching OpenAPI 3.1.0 specification."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PlatformResultDto(BaseModel):
    """Itemized outcome representation for a single social or developer platform."""

    model_config = ConfigDict(
        frozen=True,
        extra="ignore",
        populate_by_name=True,
    )

    platform: str = Field(..., description="Canonical platform identifier (e.g. LinkedIn, Dev.to).")
    status: Literal["success", "failed", "skipped"] = Field(..., description="Execution status.")
    posted_url: str | None = Field(
        default=None,
        description="Publicly accessible URL of the published post if successful.",
    )
    public_access: bool = Field(
        default=True,
        description="Indicates whether the content is accessible on the open web without authentication.",
    )
    date: str | None = Field(
        default=None,
        description="Execution date in ISO-8601 YYYY-MM-DD format (UTC).",
    )
    time: str | None = Field(
        default=None,
        description="Execution time in ISO-8601 HH:MM:SS format (UTC).",
    )
    post_id: str | None = Field(
        default=None,
        description="External identifier assigned by platform.",
    )
    error: str | None = Field(
        default=None,
        description="Sanitized human-readable error if failed; null if successful.",
    )
    latency_ms: float | None = Field(
        default=None,
        description="Upstream platform HTTP round-trip latency in milliseconds.",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC completion timestamp.",
    )

    @property
    def post_url(self) -> str | None:
        """Backward-compatible alias for posted_url."""
        return self.posted_url
