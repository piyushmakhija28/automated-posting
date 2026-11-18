"""Centralized typed constants for the automated-posting microservice.

Organized into four dedicated classes:
- ServiceMessageConstants: Success, partial success, and failure messages
- ValidationMessageConstants: Ingress validation violation messages
- ApiConstants: Route paths, HTTP headers, and system identifiers
- PlatformConstants: External platform identifiers, timeouts, and SLA limits
"""

from typing import Final


class ValidationMessageConstants:
    """Constraint violation messages for ingress validation pipeline."""

    MSG_NOT_NULL: Final[str] = "Message payload must not be null or omitted."
    MSG_NOT_BLANK: Final[str] = "Message must not be empty or contain only whitespace."
    MSG_TOO_LONG: Final[str] = "Message exceeds maximum permitted length of 200 characters."
    MSG_URL_REQUIRED: Final[str] = "Message must contain exactly one valid CTA URL (found 0)."
    MSG_URL_MULTIPLE: Final[str] = "Message must contain exactly one valid CTA URL (found {count})."
    MSG_URL_INVALID_SCHEME: Final[str] = "CTA URL must use http:// or https:// protocol."
    MSG_URL_SSRF_BLOCKED: Final[str] = (
        "CTA URL targets private or reserved network ranges (SSRF blocked)."
    )
    MSG_PROMPT_INJECTION_DETECTED: Final[str] = (
        "Message contains prohibited prompt injection patterns."
    )
    MSG_SUSPICIOUS_PAYLOAD: Final[str] = (
        "Message contains suspicious control or evasion characters."
    )


class ServiceMessageConstants:
    """Lifecycle and orchestration response messages."""

    POST_SUCCESS_ALL: Final[str] = (
        "Broadcast completed successfully across all configured platforms."
    )
    POST_PARTIAL_SUCCESS: Final[str] = "Broadcast completed with partial platform failures."
    POST_FAILED_ALL: Final[str] = "Broadcast failed across all configured platforms."
    POST_NO_PLATFORMS: Final[str] = "No external platform adapters are currently configured."
    HEALTH_LIVENESS_OK: Final[str] = "Microservice process is alive and responsive."
    HEALTH_READINESS_OK: Final[str] = "Microservice is ready to process broadcast traffic."
    HEALTH_READINESS_DEGRADED: Final[str] = "Microservice is operating in degraded state."


class ApiConstants:
    """REST API route paths, header names, and system metadata."""

    API_PREFIX: Final[str] = ""
    ENDPOINT_POSTING: Final[str] = "/posting"
    ENDPOINT_HEALTH: Final[str] = "/health"
    ENDPOINT_READY: Final[str] = "/ready"
    ENDPOINT_METRICS: Final[str] = "/metrics"

    HEADER_CORRELATION_ID: Final[str] = "X-Correlation-ID"
    HEADER_REQUEST_ID: Final[str] = "X-Request-ID"
    HEADER_TOTAL_LATENCY: Final[str] = "X-Response-Time-Ms"

    SERVICE_NAME: Final[str] = "automated-posting"
    SERVICE_VERSION: Final[str] = "1.0.0"
    DEFAULT_PORT: Final[int] = 4000
    DEFAULT_HOST: Final[str] = "0.0.0.0"


class PlatformConstants:
    """External social and developer platform constants and limits."""

    PLATFORM_LINKEDIN: Final[str] = "linkedin"
    PLATFORM_DEVTO: Final[str] = "devto"
    PLATFORM_HASHNODE: Final[str] = "hashnode"
    PLATFORM_MASTODON: Final[str] = "mastodon"
    PLATFORM_TELEGRAM: Final[str] = "telegram"

    ALL_PLATFORMS: Final[tuple[str, ...]] = (
        PLATFORM_LINKEDIN,
        PLATFORM_DEVTO,
        PLATFORM_HASHNODE,
        PLATFORM_MASTODON,
        PLATFORM_TELEGRAM,
    )

    DEFAULT_ADAPTER_TIMEOUT_SECONDS: Final[float] = 3.0
    DEFAULT_TOTAL_TIMEOUT_SECONDS: Final[float] = 5.0
    DEFAULT_MAX_RETRIES: Final[int] = 2
    DEFAULT_BACKOFF_FACTOR: Final[float] = 0.3

    STATUS_SUCCESS: Final[str] = "success"
    STATUS_FAILED: Final[str] = "failed"
    STATUS_SKIPPED: Final[str] = "skipped"
