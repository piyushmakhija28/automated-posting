"""Triad unit test suite for PostingService, PostingServiceImpl, and PostingServiceHelper."""

import asyncio
from time import perf_counter

import httpx
import pytest

from app.core.config import Settings
from app.core.constants import PlatformConstants, ServiceMessageConstants
from app.models.dtos.platform_dto import PlatformResultDto
from app.models.forms.posting_form import PostingForm
from app.platforms.base import BasePlatformAdapter
from app.services.posting_helper import PostingServiceHelper
from app.services.posting_service import PostingServiceImpl


class DummyAdapter(BasePlatformAdapter):
    """Mock platform adapter for service orchestration testing."""

    def __init__(
        self,
        name: str,
        configured: bool = True,
        delay_seconds: float = 0.0,
        should_fail: bool = False,
        should_raise: Exception | None = None,
    ) -> None:
        """Initializes mock adapter with configurable behavior."""
        super().__init__(
            name=name,
            client=httpx.AsyncClient(),
            settings=Settings(),
        )
        self._configured = configured
        self._delay_seconds = delay_seconds
        self._should_fail = should_fail
        self._should_raise = should_raise

    def is_configured(self) -> bool:
        """Returns configured flag."""
        return self._configured

    async def post(self, message: str, cta_url: str) -> PlatformResultDto:
        """Simulates asynchronous post execution with optional delay and failures."""
        if self._should_raise:
            raise self._should_raise

        if self._delay_seconds > 0:
            await asyncio.sleep(self._delay_seconds)

        if self._should_fail:
            return self._create_failure_result(
                error=f"Platform {self.name} simulated failure.",
                latency_ms=round(self._delay_seconds * 1000.0, 2),
            )

        return self._create_success_result(
            posted_url=f"https://{self.name}.example.com/post/123",
            post_id=f"{self.name}-123",
            public_access=True,
            latency_ms=round(self._delay_seconds * 1000.0, 2),
        )


class TestPostingServicePositive:
    """Positive test scenarios for concurrent broadcast and helper DTO synthesis."""

    @pytest.mark.asyncio
    async def test_broadcast_all_platforms_succeed(self) -> None:
        """Verifies full broadcast success across all 5 platforms."""
        adapters = [
            DummyAdapter(name="linkedin"),
            DummyAdapter(name="devto"),
            DummyAdapter(name="hashnode"),
            DummyAdapter(name="mastodon"),
            DummyAdapter(name="telegram"),
        ]
        service = PostingServiceImpl(adapters=adapters)
        form = PostingForm(
            message="Excited to share our new release! Read more: https://example.com/update"
        )

        response = await service.broadcast(form=form, correlation_id="req-123")

        assert response.success is True
        assert response.status == "success"
        assert response.message == ServiceMessageConstants.POST_SUCCESS_ALL
        assert response.total_platforms == 5
        assert response.successful_posts == 5
        assert response.failed_posts == 0
        assert len(response.results) == 5
        assert response.execution_time_seconds is not None
        assert response.telemetry is not None
        assert response.telemetry.correlation_id == "req-123"
        assert response.telemetry.total_latency_ms >= 0.0

    @pytest.mark.asyncio
    async def test_concurrent_execution_speedup(self) -> None:
        """Verifies asyncio.gather executes adapters concurrently rather than sequentially."""
        adapters = [
            DummyAdapter(name="p1", delay_seconds=0.1),
            DummyAdapter(name="p2", delay_seconds=0.1),
            DummyAdapter(name="p3", delay_seconds=0.1),
        ]
        service = PostingServiceImpl(adapters=adapters)
        form = PostingForm(
            message="Concurrent test message: https://example.com/benchmark"
        )

        start = perf_counter()
        response = await service.broadcast(form=form, correlation_id="bench-1")
        elapsed = perf_counter() - start

        assert response.success is True
        assert elapsed < 0.25

    def test_posting_service_helper_compute_summary(self) -> None:
        """Verifies compute_summary tallies platform statuses accurately."""
        results = [
            PlatformResultDto(
                platform="linkedin",
                status=PlatformConstants.STATUS_SUCCESS,
                posted_url="https://linkedin.com/1",
                public_access=True,
                date="2026-11-19",
                time="10:00:00",
                post_id="li-1",
            ),
            PlatformResultDto(
                platform="devto",
                status=PlatformConstants.STATUS_FAILED,
                posted_url=None,
                public_access=False,
                date="2026-11-19",
                time="10:00:00",
                post_id=None,
                error="HTTP 500",
            ),
            PlatformResultDto(
                platform="telegram",
                status=PlatformConstants.STATUS_SKIPPED,
                posted_url=None,
                public_access=False,
                date="2026-11-19",
                time="10:00:00",
                post_id=None,
                error="Unconfigured",
            ),
        ]
        summary = PostingServiceHelper.compute_summary(results)
        assert summary.total == 3
        assert summary.successful == 1
        assert summary.failed == 1
        assert summary.skipped == 1

    def test_posting_service_helper_determine_status(self) -> None:
        """Verifies determine_aggregate_status returns correct status and message mappings."""
        from app.models.dtos.posting_dto import PostingSummaryDto

        all_ok = PostingSummaryDto(total=3, successful=3, failed=0, skipped=0)
        assert PostingServiceHelper.determine_aggregate_status(all_ok) == (
            "success",
            ServiceMessageConstants.POST_SUCCESS_ALL,
        )

        partial = PostingSummaryDto(total=3, successful=2, failed=1, skipped=0)
        assert PostingServiceHelper.determine_aggregate_status(partial) == (
            "partial_success",
            ServiceMessageConstants.POST_PARTIAL_SUCCESS,
        )

        all_failed = PostingSummaryDto(total=3, successful=0, failed=3, skipped=0)
        assert PostingServiceHelper.determine_aggregate_status(all_failed) == (
            "failed",
            ServiceMessageConstants.POST_FAILED_ALL,
        )

        no_platforms = PostingSummaryDto(total=0, successful=0, failed=0, skipped=0)
        assert PostingServiceHelper.determine_aggregate_status(no_platforms) == (
            "failed",
            ServiceMessageConstants.POST_NO_PLATFORMS,
        )

        all_skipped = PostingSummaryDto(total=3, successful=0, failed=0, skipped=3)
        assert PostingServiceHelper.determine_aggregate_status(all_skipped) == (
            "failed",
            ServiceMessageConstants.POST_NO_PLATFORMS,
        )


class TestPostingServiceNegative:
    """Negative test scenarios for bulkhead resilience, timeouts, and fault isolation."""

    @pytest.mark.asyncio
    async def test_broadcast_single_platform_failure_partial_success(self) -> None:
        """Verifies single platform failure results in partial_success without aborting peers."""
        adapters = [
            DummyAdapter(name="p1"),
            DummyAdapter(name="p2", should_fail=True),
            DummyAdapter(name="p3"),
        ]
        service = PostingServiceImpl(adapters=adapters)
        form = PostingForm(
            message="Check out our release: https://example.com/feature"
        )

        response = await service.broadcast(form=form, correlation_id="req-part")

        assert response.success is True
        assert response.status == "partial_success"
        assert response.message == ServiceMessageConstants.POST_PARTIAL_SUCCESS
        assert response.total_platforms == 3
        assert response.successful_posts == 2
        assert response.failed_posts == 1

    @pytest.mark.asyncio
    async def test_broadcast_all_platforms_fail(self) -> None:
        """Verifies all platforms failing results in failed status and success=False."""
        adapters = [
            DummyAdapter(name="p1", should_fail=True),
            DummyAdapter(name="p2", should_fail=True),
        ]
        service = PostingServiceImpl(adapters=adapters)
        form = PostingForm(
            message="Check out our release: https://example.com/feature"
        )

        response = await service.broadcast(form=form, correlation_id="req-all-fail")

        assert response.success is False
        assert response.status == "failed"
        assert response.message == ServiceMessageConstants.POST_FAILED_ALL
        assert response.successful_posts == 0
        assert response.failed_posts == 2

    @pytest.mark.asyncio
    async def test_platform_timeout_contained_by_bulkhead(self) -> None:
        """Verifies slow adapter exceeding timeout is contained without failing fast peers."""
        adapters = [
            DummyAdapter(name="fast_adapter", delay_seconds=0.01),
            DummyAdapter(name="slow_adapter", delay_seconds=0.5),
        ]
        service = PostingServiceImpl(adapters=adapters, adapter_timeout_seconds=0.05)
        form = PostingForm(
            message="Timeout resilience test: https://example.com/timeout"
        )

        response = await service.broadcast(form=form, correlation_id="req-timeout")

        assert response.success is True
        assert response.status == "partial_success"
        assert response.successful_posts == 1
        assert response.failed_posts == 1

        slow_result = next(r for r in response.results if r.platform == "slow_adapter")
        assert slow_result.status == PlatformConstants.STATUS_FAILED
        assert "timed out" in (slow_result.error or "").lower()

    @pytest.mark.asyncio
    async def test_platform_uncaught_exception_contained_by_bulkhead(self) -> None:
        """Verifies uncaught exception in adapter coroutine is safely captured by bulkhead."""
        adapters = [
            DummyAdapter(name="healthy_adapter"),
            DummyAdapter(
                name="crashing_adapter",
                should_raise=RuntimeError("Simulated unhandled OS crash"),
            ),
        ]
        service = PostingServiceImpl(adapters=adapters)
        form = PostingForm(
            message="Crash resilience test: https://example.com/crash"
        )

        response = await service.broadcast(form=form, correlation_id="req-crash")

        assert response.success is True
        assert response.status == "partial_success"
        assert response.successful_posts == 1
        assert response.failed_posts == 1

        crashed_result = next(
            r for r in response.results if r.platform == "crashing_adapter"
        )
        assert crashed_result.status == PlatformConstants.STATUS_FAILED
        assert "Internal platform communication error" in (crashed_result.error or "")


class TestPostingServiceEdgeCases:
    """Edge-case test scenarios for service initialization and execution boundaries."""

    @pytest.mark.asyncio
    async def test_broadcast_zero_adapters(self) -> None:
        """Verifies service with zero adapters returns failed status with POST_NO_PLATFORMS."""
        service = PostingServiceImpl(adapters=[])
        form = PostingForm(
            message="Zero adapters test: https://example.com/zero"
        )

        response = await service.broadcast(form=form, correlation_id="req-zero")

        assert response.success is False
        assert response.status == "failed"
        assert response.message == ServiceMessageConstants.POST_NO_PLATFORMS
        assert response.total_platforms == 0
        assert response.successful_posts == 0
        assert response.failed_posts == 0
        assert len(response.results) == 0

    @pytest.mark.asyncio
    async def test_broadcast_all_unconfigured_adapters(self) -> None:
        """Verifies all unconfigured adapters return skipped status without network calls."""
        adapters = [
            DummyAdapter(name="p1", configured=False),
            DummyAdapter(name="p2", configured=False),
        ]
        service = PostingServiceImpl(adapters=adapters)
        form = PostingForm(
            message="Unconfigured test: https://example.com/unconfigured"
        )

        response = await service.broadcast(form=form, correlation_id="req-unconf")

        assert response.success is False
        assert response.status == "failed"
        assert response.message == ServiceMessageConstants.POST_NO_PLATFORMS
        assert response.successful_posts == 0
        assert response.failed_posts == 0
        assert all(r.status == PlatformConstants.STATUS_SKIPPED for r in response.results)

    @pytest.mark.asyncio
    async def test_mix_of_success_and_skipped(self) -> None:
        """Verifies mixture of success and skipped adapters evaluates to partial_success."""
        adapters = [
            DummyAdapter(name="p1"),
            DummyAdapter(name="p2", configured=False),
        ]
        service = PostingServiceImpl(adapters=adapters)
        form = PostingForm(
            message="Mix test: https://example.com/mix"
        )

        response = await service.broadcast(form=form, correlation_id="req-mix")

        assert response.success is True
        assert response.status == "partial_success"
        assert response.successful_posts == 1
        assert response.failed_posts == 0

    @pytest.mark.asyncio
    async def test_safe_execute_directly(self) -> None:
        """Verifies _safe_execute helper returns proper result when invoked directly."""
        adapter = DummyAdapter(name="direct_test")
        service = PostingServiceImpl(adapters=[adapter])

        result = await service._safe_execute(
            adapter=adapter,
            message="Direct test message",
            cta_url="https://example.com/direct",
        )

        assert result.platform == "direct_test"
        assert result.status == PlatformConstants.STATUS_SUCCESS
        assert result.post_id == "direct_test-123"
