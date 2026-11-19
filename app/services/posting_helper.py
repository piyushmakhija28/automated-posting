"""Service layer helper for DTO transformations, summary metrics, and status aggregation.

Enforces clean DTO/Form separation and isolates statistical calculations
from core coroutine bulkhead orchestration logic.
"""

from collections.abc import Sequence
from typing import Literal

from app.core.constants import PlatformConstants, ServiceMessageConstants
from app.models.dtos.platform_dto import PlatformResultDto
from app.models.dtos.posting_dto import (
    PostingResponseDto,
    PostingSummaryDto,
    TelemetryDto,
)


class PostingServiceHelper:
    """Helper utilities supporting PostingServiceImpl orchestration."""

    @staticmethod
    def compute_summary(results: Sequence[PlatformResultDto]) -> PostingSummaryDto:
        """Computes platform execution counts from a collection of platform results.

        Args:
            results: Sequence of individual platform execution outcome DTOs.

        Returns:
            PostingSummaryDto detailing total, successful, failed, and skipped tallies.
        """
        total = len(results)
        successful = sum(
            1 for r in results if r.status == PlatformConstants.STATUS_SUCCESS
        )
        failed = sum(
            1 for r in results if r.status == PlatformConstants.STATUS_FAILED
        )
        skipped = sum(
            1 for r in results if r.status == PlatformConstants.STATUS_SKIPPED
        )
        return PostingSummaryDto(
            total=total,
            successful=successful,
            failed=failed,
            skipped=skipped,
        )

    @staticmethod
    def determine_aggregate_status(
        summary: PostingSummaryDto,
    ) -> tuple[Literal["success", "partial_success", "failed"], str]:
        """Determines aggregate outcome status and human-readable lifecycle message.

        Args:
            summary: Aggregated platform execution count tallies.

        Returns:
            Tuple of (status_literal, descriptive_lifecycle_message).
        """
        if summary.total == 0 or (summary.successful == 0 and summary.failed == 0 and summary.skipped > 0):
            return "failed", ServiceMessageConstants.POST_NO_PLATFORMS
        if summary.successful == summary.total:
            return "success", ServiceMessageConstants.POST_SUCCESS_ALL
        if summary.successful > 0:
            return "partial_success", ServiceMessageConstants.POST_PARTIAL_SUCCESS
        return "failed", ServiceMessageConstants.POST_FAILED_ALL

    @classmethod
    def build_posting_response(
        cls,
        results: Sequence[PlatformResultDto],
        correlation_id: str,
        total_latency_ms: float,
    ) -> PostingResponseDto:
        """Constructs an immutable PostingResponseDto from execution outcomes.

        Args:
            results: Itemized results from all evaluated platform adapters.
            correlation_id: Unique request correlation tracking identifier.
            total_latency_ms: Wall-clock round-trip execution duration in milliseconds.

        Returns:
            Consolidated PostingResponseDto containing summary, results, and telemetry.
        """
        summary = cls.compute_summary(results)
        status, message = cls.determine_aggregate_status(summary)
        success = summary.successful > 0

        telemetry = TelemetryDto(
            total_latency_ms=round(total_latency_ms, 2),
            correlation_id=correlation_id,
        )

        return PostingResponseDto(
            success=success,
            status=status,
            message=message,
            total_platforms=summary.total,
            successful_posts=summary.successful,
            failed_posts=summary.failed,
            execution_time_seconds=round(total_latency_ms / 1000.0, 3),
            results=list(results),
            telemetry=telemetry,
        )
