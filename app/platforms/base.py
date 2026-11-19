"""Core abstract port defining the BasePlatformAdapter contract.

All third-party publishing adapters must implement this abstract contract,
guaranteeing a uniform API, failure containment, and polymorphic execution.
"""

import logging
from abc import ABC, abstractmethod
from datetime import UTC, datetime

import httpx

from app.core.config import Settings
from app.core.constants import PlatformConstants
from app.models.dtos.platform_dto import PlatformResultDto


class BasePlatformAdapter(ABC):
    """Abstract port defining the interface for all social and developer platform adapters."""

    def __init__(
        self,
        name: str,
        client: httpx.AsyncClient,
        settings: Settings | None = None,
    ) -> None:
        """Initializes the base platform adapter with client and configuration.

        Args:
            name: Canonical platform identifier slug (e.g. 'linkedin', 'devto').
            client: Shared asynchronous HTTPX client session.
            settings: Optional runtime application settings; defaults to fresh Settings.
        """
        self._name = name
        self.client = client
        self.settings = settings or Settings()
        self.logger = logging.getLogger(f"app.platforms.{name}")

    @property
    def name(self) -> str:
        """Returns the canonical human-readable platform identifier slug."""
        return self._name

    @abstractmethod
    def is_configured(self) -> bool:
        """Evaluates whether all mandatory credentials exist in configuration.

        Returns:
            True if all required credentials are non-empty; False otherwise.
        """

    @abstractmethod
    async def post(self, message: str, cta_url: str) -> PlatformResultDto:
        """Asynchronously dispatches the publication payload to the platform.

        Args:
            message: Sanitized message copy (<= 200 unicode characters).
            cta_url: Validated single Call-To-Action destination link.

        Returns:
            Structured PlatformResultDto detailing execution status and metadata.
        """

    def _get_current_timestamp(self) -> tuple[str, str]:
        """Calculates current UTC date and time strings.

        Returns:
            A tuple of (YYYY-MM-DD, HH:MM:SS) formatted in UTC.
        """
        now = datetime.now(UTC)
        return now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S")

    def _extract_date_time(self) -> tuple[str, str]:
        """Alias for _get_current_timestamp providing backward compatibility.

        Returns:
            A tuple of (YYYY-MM-DD, HH:MM:SS) formatted in UTC.
        """
        return self._get_current_timestamp()

    def _normalize_exception(self, exc: Exception) -> str:
        """Converts raw transport and upstream HTTP exceptions into sanitized messages.

        Args:
            exc: The caught upstream exception.

        Returns:
            A sanitized, human-readable diagnostic error string.
        """
        if isinstance(exc, httpx.TimeoutException):
            return "Request timed out waiting for platform response."
        if isinstance(exc, httpx.HTTPStatusError):
            status = exc.response.status_code
            if status == 401:
                return "Authentication failed: invalid or expired API credentials."
            if status == 403:
                return "Permission denied: access forbidden by platform."
            if status == 429:
                return "Rate limit exceeded on target platform."
            return f"Platform rejected request with HTTP {status}."
        if isinstance(exc, httpx.RequestError):
            return "Network or connection error communicating with platform."
        return "Internal platform communication error."

    def _handle_error(self, exc: Exception) -> str:
        """Alias for _normalize_exception providing backward compatibility.

        Args:
            exc: The caught upstream exception.

        Returns:
            A sanitized, human-readable diagnostic error string.
        """
        return self._normalize_exception(exc)

    def _create_failure_result(
        self,
        error: str,
        latency_ms: float | None = None,
    ) -> PlatformResultDto:
        """Factory helper constructing a standardized failure PlatformResultDto.

        Args:
            error: Descriptive, sanitized failure message.
            latency_ms: Optional round-trip latency in milliseconds.

        Returns:
            PlatformResultDto populated with status='failed'.
        """
        date_str, time_str = self._get_current_timestamp()
        return PlatformResultDto(
            platform=self.name,
            status=PlatformConstants.STATUS_FAILED,
            posted_url=None,
            public_access=False,
            date=date_str,
            time=time_str,
            post_id=None,
            error=error,
            latency_ms=latency_ms,
        )

    def _create_success_result(
        self,
        posted_url: str | None = None,
        post_id: str | None = None,
        public_access: bool = True,
        latency_ms: float | None = None,
    ) -> PlatformResultDto:
        """Factory helper constructing a standardized success PlatformResultDto.

        Args:
            posted_url: Public canonical URL of the published post.
            post_id: Platform-assigned unique entity identifier.
            public_access: Whether content is accessible without login.
            latency_ms: Optional round-trip latency in milliseconds.

        Returns:
            PlatformResultDto populated with status='success'.
        """
        date_str, time_str = self._get_current_timestamp()
        return PlatformResultDto(
            platform=self.name,
            status=PlatformConstants.STATUS_SUCCESS,
            posted_url=posted_url,
            public_access=public_access,
            date=date_str,
            time=time_str,
            post_id=post_id,
            error=None,
            latency_ms=latency_ms,
        )
