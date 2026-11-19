"""Triad unit test suite for Bulkhead pattern fault isolation and concurrency resilience."""

import asyncio
from time import perf_counter

import httpx
import pytest

from app.core.config import Settings
from app.core.constants import PlatformConstants, ServiceMessageConstants
from app.models.dtos.platform_dto import PlatformResultDto
from app.models.forms.posting_form import PostingForm
from app.platforms.base import BasePlatformAdapter
from app.services.posting_service import PostingServiceImpl


class MockBulkheadAdapter(BasePlatformAdapter):
    """Configurable mock adapter for bulkhead failure and latency simulation."""

    def __init__(
        self,
        name: str,
        configured: bool = True,
        delay_seconds: float = 0.0,
        should_fail: bool = False,
        error_message: str | None = None,
        should_raise: Exception | None = None,
    ) -> None:
        """Initializes mock adapter with specific timing and failure characteristics."""
        super().__init__(
            name=name,
            client=httpx.AsyncClient(),
            settings=Settings(),
        )
        self._configured = configured
        self._delay_seconds = delay_seconds
        self._should_fail = should_fail
        self._error_message = error_message
        self._should_raise = should_raise

    def is_configured(self) -> bool:
        """Returns adapter configuration state."""
        return self._configured

    async def post(self, message: str, cta_url: str) -> PlatformResultDto:
        """Executes simulated post with delay and conditional failures."""
        if self._should_raise:
            raise self._should_raise

        if self._delay_seconds > 0:
            await asyncio.sleep(self._delay_seconds)

        if self._should_fail:
            return self._create_failure_result(
                error=self._error_message or f"Platform {self.name} failed.",
                latency_ms=round(self._delay_seconds * 1000.0, 2),
            )

        return self._create_success_result(
            posted_url=f"https://{self.name}.example.com/posts/100",
            post_id=f"{self.name}-100",
            latency_ms=round(self._delay_seconds * 1000.0, 2),
        )


class TestBulkheadIsolation:
    """Test suite verifying Bulkhead fault containment and SLA timeout enforcement."""

    @pytest.mark.asyncio
    async def test_slow_adapter_timeout_does_not_block_fast_adapters(self) -> None:
        """Verifies TC-EDG-07: Adapter exceeding SLA times out without delaying fast peers."""
        fast_adapters = [
            MockBulkheadAdapter(name=f"fast_{i}", delay_seconds=0.01)
            for i in range(4)
        ]
        slow_adapter = MockBulkheadAdapter(
            name="slow_platform",
            delay_seconds=0.5,
        )
        service = PostingServiceImpl(
            adapters=[*fast_adapters, slow_adapter],
            adapter_timeout_seconds=0.08,
        )
        form = PostingForm(message="Resilient concurrency test! https://techdeveloper.io")

        start = perf_counter()
        response = await service.broadcast(form=form, correlation_id="bulkhead-sla-001")
        elapsed = perf_counter() - start

        assert elapsed < 0.35
        assert response.total_platforms == 5
        assert response.successful_posts == 4
        assert response.failed_posts == 1
        assert response.status == "partial_success"
        assert response.message == ServiceMessageConstants.POST_PARTIAL_SUCCESS

        slow_result = next(r for r in response.results if r.platform == "slow_platform")
        assert slow_result.status == PlatformConstants.STATUS_FAILED
        assert "timed out" in str(slow_result.error).lower()

    @pytest.mark.asyncio
    async def test_unhandled_exception_in_single_adapter_contained_by_bulkhead(self) -> None:
        """Verifies unexpected runtime exceptions in one adapter do not crash peer coroutines."""
        healthy_adapters = [
            MockBulkheadAdapter(name="linkedin"),
            MockBulkheadAdapter(name="devto"),
            MockBulkheadAdapter(name="hashnode"),
            MockBulkheadAdapter(name="mastodon"),
        ]
        crashing_adapter = MockBulkheadAdapter(
            name="telegram",
            should_raise=ZeroDivisionError("Division by zero in adapter parser"),
        )
        service = PostingServiceImpl(
            adapters=[*healthy_adapters, crashing_adapter],
            adapter_timeout_seconds=1.0,
        )
        form = PostingForm(message="Crash resilience test! https://techdeveloper.io")

        response = await service.broadcast(form=form, correlation_id="bulkhead-crash-002")

        assert response.success is True
        assert response.total_platforms == 5
        assert response.successful_posts == 4
        assert response.failed_posts == 1
        assert response.status == "partial_success"

        crashed_result = next(r for r in response.results if r.platform == "telegram")
        assert crashed_result.status == PlatformConstants.STATUS_FAILED
        assert "Internal platform communication error" in str(crashed_result.error)

    @pytest.mark.asyncio
    async def test_upstream_401_auth_failure_isolated(self) -> None:
        """Verifies TC-EDG-04: Single platform 401 auth expiration is isolated gracefully."""
        healthy_adapters = [
            MockBulkheadAdapter(name="devto"),
            MockBulkheadAdapter(name="hashnode"),
            MockBulkheadAdapter(name="mastodon"),
            MockBulkheadAdapter(name="telegram"),
        ]
        expired_adapter = MockBulkheadAdapter(
            name="linkedin",
            should_fail=True,
            error_message="LinkedIn API error: 401 Unauthorized - token expired",
        )
        service = PostingServiceImpl(
            adapters=[expired_adapter, *healthy_adapters],
        )
        form = PostingForm(message="Auth failure isolation test! https://techdeveloper.io")

        response = await service.broadcast(form=form, correlation_id="bulkhead-auth-003")

        assert response.success is True
        assert response.successful_posts == 4
        assert response.failed_posts == 1
        assert response.status == "partial_success"

        linkedin_res = next(r for r in response.results if r.platform == "linkedin")
        assert linkedin_res.status == PlatformConstants.STATUS_FAILED
        assert "401" in str(linkedin_res.error)

    @pytest.mark.asyncio
    async def test_upstream_429_rate_limit_isolated(self) -> None:
        """Verifies TC-EDG-05: Rate limit 429 error on one platform is isolated without crashing."""
        healthy_adapters = [
            MockBulkheadAdapter(name="linkedin"),
            MockBulkheadAdapter(name="devto"),
            MockBulkheadAdapter(name="hashnode"),
            MockBulkheadAdapter(name="telegram"),
        ]
        rate_limited_adapter = MockBulkheadAdapter(
            name="mastodon",
            should_fail=True,
            error_message="Rate limit exceeded. Retry after 60s (HTTP 429).",
        )
        service = PostingServiceImpl(
            adapters=[*healthy_adapters, rate_limited_adapter],
        )
        form = PostingForm(message="Rate limit isolation test! https://techdeveloper.io")

        response = await service.broadcast(form=form, correlation_id="bulkhead-429-004")

        assert response.success is True
        assert response.successful_posts == 4
        assert response.failed_posts == 1

        mastodon_res = next(r for r in response.results if r.platform == "mastodon")
        assert mastodon_res.status == PlatformConstants.STATUS_FAILED
        assert "429" in str(mastodon_res.error)

    @pytest.mark.asyncio
    async def test_upstream_500_server_error_isolated(self) -> None:
        """Verifies TC-EDG-06: 500 internal error on one platform does not impact other platforms."""
        healthy_adapters = [
            MockBulkheadAdapter(name="linkedin"),
            MockBulkheadAdapter(name="hashnode"),
            MockBulkheadAdapter(name="mastodon"),
            MockBulkheadAdapter(name="telegram"),
        ]
        server_error_adapter = MockBulkheadAdapter(
            name="devto",
            should_fail=True,
            error_message="Dev.to upstream 500 Internal Server Error.",
        )
        service = PostingServiceImpl(
            adapters=[*healthy_adapters, server_error_adapter],
        )
        form = PostingForm(message="Server error isolation test! https://techdeveloper.io")

        response = await service.broadcast(form=form, correlation_id="bulkhead-500-005")

        assert response.success is True
        assert response.successful_posts == 4
        assert response.failed_posts == 1

        devto_res = next(r for r in response.results if r.platform == "devto")
        assert devto_res.status == PlatformConstants.STATUS_FAILED
        assert "500" in str(devto_res.error)

    @pytest.mark.asyncio
    async def test_all_platforms_fail_returns_success_false(self) -> None:
        """Verifies TC-EDG-08: Complete platform failure returns success=False with itemized errors."""
        failing_adapters = [
            MockBulkheadAdapter(name=f"platform_{i}", should_fail=True)
            for i in range(5)
        ]
        service = PostingServiceImpl(adapters=failing_adapters)
        form = PostingForm(message="Complete failure test! https://techdeveloper.io")

        response = await service.broadcast(form=form, correlation_id="bulkhead-allfail-006")

        assert response.success is False
        assert response.total_platforms == 5
        assert response.successful_posts == 0
        assert response.failed_posts == 5
        assert response.status == "failed"
        assert response.message == ServiceMessageConstants.POST_FAILED_ALL

    @pytest.mark.asyncio
    async def test_unconfigured_platform_skips_immediately_with_zero_latency(self) -> None:
        """Verifies TC-EDG-10: Unconfigured platforms are skipped immediately with zero latency."""
        configured_adapter = MockBulkheadAdapter(name="linkedin", configured=True)
        unconfigured_adapter = MockBulkheadAdapter(name="devto", configured=False)

        service = PostingServiceImpl(adapters=[configured_adapter, unconfigured_adapter])
        form = PostingForm(message="Unconfigured skip test! https://techdeveloper.io")

        response = await service.broadcast(form=form, correlation_id="bulkhead-unconfigured-007")

        assert response.total_platforms == 2
        assert response.successful_posts == 1
        assert response.failed_posts == 0

        unconfigured_res = next(r for r in response.results if r.platform == "devto")
        assert unconfigured_res.status == PlatformConstants.STATUS_SKIPPED
        assert unconfigured_res.latency_ms == 0.0
        assert "not configured" in str(unconfigured_res.error)

    @pytest.mark.asyncio
    async def test_concurrency_fanout_timing_speedup(self) -> None:
        """Verifies concurrent execution total duration is approximately max(t_i) << sum(t_i)."""
        adapters = [
            MockBulkheadAdapter(name=f"platform_{i}", delay_seconds=0.06)
            for i in range(5)
        ]
        service = PostingServiceImpl(adapters=adapters)
        form = PostingForm(message="Concurrency speedup test! https://techdeveloper.io")

        start = perf_counter()
        response = await service.broadcast(form=form, correlation_id="bulkhead-timing-008")
        elapsed = perf_counter() - start

        assert elapsed < 0.20
        assert response.successful_posts == 5
        assert response.total_platforms == 5
