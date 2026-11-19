"""Service layer contract and bulkhead concurrent orchestrator implementation.

Dispatches broadcast jobs across multiple external platforms concurrently using
isolated coroutines with strict individual per-adapter timeouts.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import Sequence
from time import perf_counter

from app.core.constants import PlatformConstants
from app.models.dtos.platform_dto import PlatformResultDto
from app.models.dtos.posting_dto import PostingResponseDto
from app.models.forms.posting_form import PostingForm
from app.platforms.base import BasePlatformAdapter
from app.services.posting_helper import PostingServiceHelper


class PostingService(ABC):
    """Abstract interface defining the business contract for multi-platform broadcasting."""

    @abstractmethod
    async def broadcast(
        self, form: PostingForm, correlation_id: str
    ) -> PostingResponseDto:
        """Broadcasts the validated form content across all configured platforms concurrently.

        Args:
            form: Validated and sanitized inbound PostingForm.
            correlation_id: Unique request correlation tracking identifier.

        Returns:
            Consolidated PostingResponseDto containing per-platform results and telemetry.
        """


class PostingServiceImpl(PostingService):
    """Production orchestrator implementing bulkhead concurrency and fault isolation."""

    def __init__(
        self,
        adapters: Sequence[BasePlatformAdapter],
        adapter_timeout_seconds: float = PlatformConstants.DEFAULT_ADAPTER_TIMEOUT_SECONDS,
        helper: type[PostingServiceHelper] = PostingServiceHelper,
    ) -> None:
        """Initializes service implementation with platform adapters and timeout SLA.

        Args:
            adapters: Sequence of initialized platform adapters.
            adapter_timeout_seconds: Strict per-adapter timeout in seconds (defaults to 3.0s).
            helper: Helper class for DTO synthesis and summary calculations.
        """
        self.adapters = list(adapters)
        self.adapter_timeout_seconds = adapter_timeout_seconds
        self.helper = helper
        self.logger = logging.getLogger("app.services.posting")

    async def _safe_execute(
        self,
        adapter: BasePlatformAdapter,
        message: str,
        cta_url: str,
    ) -> PlatformResultDto:
        """Executes a single adapter post with individual timeout and bulkhead fault isolation.

        Args:
            adapter: Concrete platform publishing adapter.
            message: Sanitized message text.
            cta_url: Validated Call-to-Action destination link.

        Returns:
            PlatformResultDto populated with successful outcome, skipped notice, or failure diagnostic.
        """
        start_time = perf_counter()
        if not adapter.is_configured():
            date_str, time_str = adapter._get_current_timestamp()
            return PlatformResultDto(
                platform=adapter.name,
                status=PlatformConstants.STATUS_SKIPPED,
                posted_url=None,
                public_access=False,
                date=date_str,
                time=time_str,
                post_id=None,
                error="Platform credentials not configured in environment.",
                latency_ms=0.0,
            )

        try:
            result = await asyncio.wait_for(
                adapter.post(message=message, cta_url=cta_url),
                timeout=self.adapter_timeout_seconds,
            )
            return result
        except TimeoutError:
            latency_ms = (perf_counter() - start_time) * 1000.0
            self.logger.warning(
                f"Platform {adapter.name} timed out after {self.adapter_timeout_seconds}s."
            )
            date_str, time_str = adapter._get_current_timestamp()
            return PlatformResultDto(
                platform=adapter.name,
                status=PlatformConstants.STATUS_FAILED,
                posted_url=None,
                public_access=False,
                date=date_str,
                time=time_str,
                post_id=None,
                error=(
                    f"Request timed out waiting for platform response "
                    f"after {self.adapter_timeout_seconds}s."
                ),
                latency_ms=round(latency_ms, 2),
            )
        except Exception as exc:
            latency_ms = (perf_counter() - start_time) * 1000.0
            self.logger.error(
                f"Platform {adapter.name} raised uncaught exception: {exc}"
            )
            date_str, time_str = adapter._get_current_timestamp()
            return PlatformResultDto(
                platform=adapter.name,
                status=PlatformConstants.STATUS_FAILED,
                posted_url=None,
                public_access=False,
                date=date_str,
                time=time_str,
                post_id=None,
                error=adapter._normalize_exception(exc),
                latency_ms=round(latency_ms, 2),
            )

    async def broadcast(
        self, form: PostingForm, correlation_id: str
    ) -> PostingResponseDto:
        """Executes concurrent broadcast across all platforms using asyncio.gather bulkhead.

        Args:
            form: Validated and sanitized inbound PostingForm.
            correlation_id: Unique request correlation tracking identifier.

        Returns:
            Consolidated PostingResponseDto with execution tallies and telemetry.
        """
        start_total = perf_counter()
        message = form.cleaned_message
        cta_url = form.extracted_url

        tasks = [
            self._safe_execute(adapter, message, cta_url)
            for adapter in self.adapters
        ]

        results: list[PlatformResultDto] = await asyncio.gather(
            *tasks, return_exceptions=False
        )

        total_latency_ms = (perf_counter() - start_total) * 1000.0
        return self.helper.build_posting_response(
            results=results,
            correlation_id=correlation_id,
            total_latency_ms=total_latency_ms,
        )
