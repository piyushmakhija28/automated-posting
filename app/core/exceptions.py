"""Domain and infrastructure exception hierarchy with RFC 7807 Problem Details mapping."""

from typing import Any


class ApplicationException(Exception):
    """Root base exception for all application-controlled errors."""

    def __init__(
        self,
        message: str,
        http_status: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initializes application exception with HTTP status and structured details."""
        super().__init__(message)
        self.message = message
        self.http_status = http_status
        self.error_code = error_code
        self.details = details or {}


class DomainException(ApplicationException):
    """Base exception for business logic and validation contract violations."""

    def __init__(
        self,
        message: str,
        http_status: int = 422,
        error_code: str = "DOMAIN_VALIDATION_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initializes domain exception."""
        super().__init__(message, http_status, error_code, details)


class MessageValidationError(DomainException):
    """Raised when message fails length, syntax, or character invariants."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        """Initializes message validation error with 422 Unprocessable Content."""
        super().__init__(
            message, http_status=422, error_code="MESSAGE_VALIDATION_FAILED", details=details
        )


class UrlExtractionError(DomainException):
    """Raised when CTA URL extraction detects 0 or >1 URLs."""

    def __init__(self, message: str, count: int) -> None:
        """Initializes URL extraction error with detected count."""
        super().__init__(
            message,
            http_status=422,
            error_code="INVALID_URL_COUNT",
            details={"detected_urls_count": count},
        )
        self.count = count


class SecurityThreatError(DomainException):
    """Raised when prompt injection, SSRF, or malicious payload is screened."""

    def __init__(self, message: str, threat_type: str) -> None:
        """Initializes security threat error with 422 Unprocessable Content."""
        super().__init__(
            message,
            http_status=422,
            error_code="SECURITY_THREAT_DETECTED",
            details={"threat_type": threat_type},
        )
        self.threat_type = threat_type


class InfrastructureException(ApplicationException):
    """Base exception for external platform and networking failures."""

    def __init__(
        self,
        message: str,
        http_status: int = 502,
        error_code: str = "INFRASTRUCTURE_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initializes infrastructure exception."""
        super().__init__(message, http_status, error_code, details)


class PlatformException(InfrastructureException):
    """Base exception for specific third-party platform adapter failures."""

    def __init__(
        self,
        platform: str,
        message: str,
        status_code: int | None = None,
        raw_error: str | None = None,
    ) -> None:
        """Initializes platform exception with platform identifier and upstream status."""
        super().__init__(
            message=f"[{platform}] {message}",
            http_status=502,
            error_code=f"{platform.upper()}_UPSTREAM_ERROR",
            details={"platform": platform, "upstream_status": status_code, "raw_error": raw_error},
        )
        self.platform = platform
        self.status_code = status_code
        self.raw_error = raw_error


class PlatformTimeoutException(PlatformException):
    """Raised when an external platform call exceeds the per-adapter SLA."""

    def __init__(self, platform: str, timeout_seconds: float) -> None:
        """Initializes platform timeout exception."""
        super().__init__(
            platform=platform,
            message=f"Request timed out after {timeout_seconds}s.",
            status_code=504,
            raw_error="DEADLINE_EXCEEDED",
        )
        self.timeout_seconds = timeout_seconds


class PlatformRateLimitException(PlatformException):
    """Raised when an external platform returns HTTP 429 Too Many Requests."""

    def __init__(self, platform: str, retry_after: int | None = None) -> None:
        """Initializes platform rate limit exception with optional retry duration."""
        super().__init__(
            platform=platform,
            message=f"Platform rate limit exceeded. Retry after {retry_after}s.",
            status_code=429,
            raw_error="RATE_LIMITED",
        )
        self.retry_after = retry_after
