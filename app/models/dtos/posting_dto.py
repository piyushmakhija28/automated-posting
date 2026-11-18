"""Aggregate broadcast response and telemetry DTO models."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.dtos.platform_dto import PlatformResultDto


class TelemetryDto(BaseModel):
    """Execution telemetry and timing metrics for the broadcast request."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    total_latency_ms: float = Field(..., description="Wall-clock duration of concurrent broadcast.")
    correlation_id: str = Field(..., description="Unique request tracing correlation ID.")
    concurrency_engine: str = Field(default="asyncio.gather(return_exceptions=True)")
    completed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PostingSummaryDto(BaseModel):
    """Platform execution tallies and status breakdown."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    total: int = Field(..., description="Total target platforms evaluated.")
    successful: int = Field(..., description="Count of successfully published platforms.")
    failed: int = Field(..., description="Count of failed platform publications.")
    skipped: int = Field(default=0, description="Count of unconfigured or skipped platforms.")


class PostingResponseDto(BaseModel):
    """Aggregate response returned by the POST /posting endpoint."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    status: Literal["success", "partial_success", "failed"] = Field(
        ...,
        description="Aggregate broadcast outcome state.",
    )
    message: str = Field(..., description="Human-readable summary message.")
    total_platforms: int = Field(..., description="Total platforms attempted.")
    successful_posts: int = Field(..., description="Number of successful posts.")
    failed_posts: int = Field(..., description="Number of failed posts.")
    results: list[PlatformResultDto] = Field(..., description="Itemized outcome for each platform.")
    telemetry: TelemetryDto | None = Field(default=None, description="Request execution telemetry.")
