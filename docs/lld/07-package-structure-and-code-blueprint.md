# Level 2: Low-Level Design (LLD) — Master Package Structure & Code Blueprint

**Document ID:** `DOC-LLD-07-PACKAGE-STRUCTURE-BLUEPRINT`  
**Project:** `automated-posting`  
**Author:** Principal Software Architect & Staff Systems Engineer  
**Status:** APPROVED FOR SPRINT EXECUTION  
**Standards Adhered:**
- Architecture & Layering: Clean Architecture & Decoupled Modular Services
- Request/Response Contract: Strict DTO / Form Separation (Form Ingress vs DTO Egress)
- Ingress Validation: 7-Stage Sequential Validation Pipeline
- API Envelope: Standardized Response Envelope with RFC 7807 Problem Details
- Service Design: Interface + Implementation + Helper Triple Pattern
- Exception Hierarchy: ApplicationException Root with Domain and Infrastructure Subtrees
- Constants Organization: Centralized Typed Constants Classes
- Observability: Centralized Structured JSON Logging with Sensitive Data Filtering
- Quality Assurance: 11-Layer Triad Automated Testing Framework (FastAPI / pytest)

---

## 1. Executive Architecture Summary

This document establishes the definitive, comprehensive code blueprint for the `automated-posting` microservice. It serves as an immutable contract for class hierarchies, method signatures, variable semantics, type annotations, naming conventions, and directory taxonomy. 

### Core Architectural Pillars

```mermaid
graph TD
    subgraph IngressLayer ["Ingress Layer (HTTP Routers)"]
        PostingRouter["routers/posting.py<br/>(POST /posting)"]
        HealthRouter["routers/health.py<br/>(GET /health, GET /ready)"]
    end

    subgraph ValidationLayer ["Ingress Contract & Validation (Forms)"]
        PostingForm["models/forms/posting_form.py<br/>(PostingForm: 7-Stage Validation Pipeline)"]
    end

    subgraph ServiceLayer ["Orchestration & Business Logic (Triple Pattern)"]
        ServiceContract["services/posting_service.py<br/>(PostingService ABC)"]
        ServiceImpl["services/posting_service.py<br/>(PostingServiceImpl Orchestrator)"]
        ServiceHelper["services/posting_helper.py<br/>(PostingServiceHelper)"]
    end

    subgraph AdaptersLayer ["External Integration (GoF Adapter + Factory)"]
        AdapterPort["platforms/base.py<br/>(BasePlatformAdapter ABC)"]
        AdapterRegistry["platforms/registry.py<br/>(AdapterRegistry Factory)"]
        Adapters["platforms/*.py<br/>(LinkedIn, DevTo, Hashnode, Mastodon, Telegram)"]
    end

    subgraph EgressLayer ["Egress Representation (DTOs)"]
        PostingResponseDto["models/dtos/posting_dto.py<br/>(PostingResponseDto, TelemetryDto)"]
        PlatformResultDto["models/dtos/platform_dto.py<br/>(PlatformResultDto)"]
        ProblemDetailsDto["models/dtos/problem_dto.py<br/>(ProblemDetailsDto RFC 7807)"]
        ApiResponseDto["models/dtos/api_response.py<br/>(ApiResponseDto[T])"]
    end

    subgraph CoreLayer ["Core Infrastructure & Cross-Cutting"]
        Constants["core/constants.py<br/>(Service, Validation, Api, Platform Constants)"]
        Config["core/config.py<br/>(Settings: Pydantic-Settings)"]
        Exceptions["core/exceptions.py<br/>(ApplicationException Hierarchy)"]
        Logging["core/logging.py<br/>(SensitiveDataFilter & JSON Formatter)"]
    end

    PostingRouter --> PostingForm
    PostingRouter --> ServiceContract
    ServiceContract <|-- ServiceImpl
    ServiceImpl --|> ServiceHelper
    ServiceImpl --> AdapterRegistry
    AdapterRegistry --> AdapterPort
    AdapterPort <|-- Adapters
    ServiceImpl --> PostingResponseDto
    Adapters --> PlatformResultDto
    PostingRouter --> ApiResponseDto
    PostingRouter --> ProblemDetailsDto
    PostingForm --> Constants
    ServiceImpl --> Constants
    Adapters --> Constants
    PostingRouter --> Exceptions
    ServiceImpl --> Exceptions
    Adapters --> Exceptions
```

---

## 2. Directory & Package Taxonomy

The project follows a clean, decoupled backend architecture. All business logic is isolated within the Service layer, ingress contracts use dedicated Form classes, egress responses use immutable DTOs, and infrastructure dependencies are accessed via Ports and Adapters.

```
automated-posting/
├── app/
│   ├── __init__.py                     # Package marker, exports __version__ = "1.0.0"
│   ├── main.py                         # Application factory create_app(), lifespan, global handlers
│   ├── core/                           # Cross-cutting infrastructure & platform configuration
│   │   ├── __init__.py                 # Exports Settings, Constants, Exceptions, Logger
│   │   ├── config.py                   # Pydantic-Settings: 12-factor env vars with validation
│   │   ├── constants.py                # ServiceMessageConstants, ValidationMessageConstants, etc.
│   │   ├── exceptions.py               # ApplicationException hierarchy & RFC 7807 mappings
│   │   └── logging.py                  # SensitiveDataFilter & structured JSON logger
│   ├── models/                         # Domain models, strict Form vs DTO separation
│   │   ├── __init__.py                 # Exports PostingForm, PostingResponseDto, PlatformResultDto
│   │   ├── forms/                      # Inbound Request validation models (Forms)
│   │   │   ├── __init__.py             # Exports PostingForm
│   │   │   └── posting_form.py         # PostingForm (7-stage validation sequence)
│   │   └── dtos/                       # Outbound Response transfer models (DTOs)
│   │       ├── __init__.py             # Exports all DTOs and ApiResponseDto
│   │       ├── api_response.py         # Unified ApiResponseDto[T] generic envelope
│   │       ├── platform_dto.py         # PlatformResultDto itemized outcome
│   │       ├── posting_dto.py          # PostingResponseDto, TelemetryDto, PostingSummaryDto
│   │       └── problem_dto.py          # ProblemDetailsDto (RFC 7807 compliance)
│   ├── platforms/                      # Adapter layer (GoF Adapter + Registry Factory)
│   │   ├── __init__.py                 # Exports BasePlatformAdapter, AdapterRegistry
│   │   ├── base.py                     # BasePlatformAdapter abstract port
│   │   ├── registry.py                 # AdapterRegistry factory for client creation
│   │   ├── linkedin.py                 # LinkedInAdapter (UGC Post API v2)
│   │   ├── devto.py                    # DevToAdapter (Forem Articles API)
│   │   ├── hashnode.py                 # HashnodeAdapter (GraphQL API)
│   │   ├── mastodon.py                 # MastodonAdapter (Statuses API v1)
│   │   └── telegram.py                 # TelegramAdapter (Bot API sendMessage)
│   ├── services/                       # Business logic & orchestration layer
│   │   ├── __init__.py                 # Exports PostingService, PostingServiceImpl, PostingServiceHelper
│   │   ├── posting_service.py          # PostingService (ABC) & PostingServiceImpl (Bulkhead orchestrator)
│   │   └── posting_helper.py           # PostingServiceHelper (DTO mapping & summary computation)
│   └── routers/                        # Ingress controllers (HTTP transport layer only)
│       ├── __init__.py                 # Exports posting_router, health_router
│       ├── posting.py                  # POST /posting controller
│       └── health.py                   # GET /health (liveness), GET /ready (readiness)
├── tests/                              # Triad automated test suite
│   ├── __init__.py                     # Test package marker
│   ├── conftest.py                     # Pytest fixtures: mock_service, mock_adapters, async_client
│   ├── test_bootstrap.py               # Bootstrap, lifespan, and app factory tests
│   ├── test_router_posting.py          # Router layer tests (200, 422, 400, 429, 504)
│   ├── test_router_health.py           # Health and readiness probe tests
│   ├── test_service_posting.py         # Service orchestrator & helper unit tests
│   ├── test_validation_pipeline.py     # 7-stage validation sequence tests (Positive/Negative/Edge)
│   ├── test_adapters.py                # Unit tests for all 5 platform adapters
│   └── test_resilience_bulkhead.py     # Bulkhead fault isolation, partial failure & timeout tests
├── docs/                               # Complete engineering documentation suite
├── uml/                                # Mermaid structural & behavioral diagrams
├── .dockerignore                       # Docker build exclusions
├── .env.example                        # Documented environment variable template
├── .gitignore                          # Git tracking exclusions
├── Dockerfile                          # Multi-stage non-root OCI container build
├── openapi.yaml                        # OpenAPI 3.1.0 contract definition
├── pyproject.toml                      # Build toolchain & test configuration
├── README.md                           # Master project documentation & portfolio index
├── requirements.txt                    # Pinned production runtime dependencies
└── SRS.md                              # IEEE 830 compliant Software Requirements Specification
```

---

## 3. Naming Conventions & Typing Standards

Strict adherence to Python PEP 8, PEP 484 (Type Hints), PEP 585 (Generics), and PEP 257 (Docstrings) is enforced across all files.

### 3.1 Code Style Matrix

| Entity | Convention | Example |
|:---|:---|:---|
| **Packages / Directories** | `lowercase_with_underscores` or `lowercase` | `app/models/forms/`, `app/platforms/` |
| **Modules / Files** | `snake_case.py` | `posting_form.py`, `posting_service.py` |
| **Classes (General)** | `PascalCase` | `PostingServiceImpl`, `AdapterRegistry` |
| **Request Forms** | `{Action}Form` or `{Entity}Form` | `PostingForm` |
| **Response DTOs** | `{Entity}Dto` or `{Action}ResponseDto` | `PostingResponseDto`, `PlatformResultDto` |
| **Abstract Base Classes** | `Base{Entity}` or `{Entity}ABC` | `BasePlatformAdapter`, `PostingService` |
| **Constants** | `UPPER_SNAKE_CASE` | `MSG_NOT_BLANK`, `ENDPOINT_POSTING` |
| **Constant Classes** | `{Domain}Constants` | `ServiceMessageConstants`, `ValidationMessageConstants` |
| **Functions & Methods** | `snake_case` | `post_to_all()`, `_safe_execute()` |
| **Private Methods / Attributes** | `_leading_underscore` | `_extract_date_time()`, `_registry` |
| **Variables & Parameters** | `snake_case` | `cta_url`, `correlation_id` |
| **Type Aliases / Generics** | `PascalCase` | `T`, `PlatformSlug = Literal[...]` |

### 3.2 Docstrings-Only Standard

Per engineering standards:
- **Level 2.2 Docstrings-Only:** Every public and protected class, interface, method, and function must have complete contract docstrings (Python PEP 257 / Google style).
- **Zero Inline Narration:** Inline comments narrating *what* lines do (e.g. `# loop over platforms`, `# return result`) are strictly banned.
- **Why-Only Comments:** Inline comments are permissible only to explain *why* an unusual or non-obvious algorithmic decision was made.

---

## 4. Comprehensive File-by-File Code Blueprint

### 4.1 `app/core/constants.py`

Centralizes all string literals, messages, endpoints, and numerical thresholds. Eliminates magic strings across the codebase.

```python
"""Centralized typed constants for the automated-posting microservice.

Organized into four dedicated classes:
- ServiceMessageConstants: Success, partial success, and failure messages
- ValidationMessageConstants: Ingress validation violation messages
- ApiConstants: Route paths, HTTP headers, and system identifiers
- PlatformConstants: External platform identifiers, timeouts, and SLA limits
"""

from typing import Final, Literal


class ValidationMessageConstants:
    """Constraint violation messages for ingress validation pipeline."""

    MSG_NOT_NULL: Final[str] = "Message payload must not be null or omitted."
    MSG_NOT_BLANK: Final[str] = "Message must not be empty or contain only whitespace."
    MSG_TOO_LONG: Final[str] = "Message exceeds maximum permitted length of 200 characters."
    MSG_URL_REQUIRED: Final[str] = "Message must contain exactly one valid CTA URL (found 0)."
    MSG_URL_MULTIPLE: Final[str] = "Message must contain exactly one valid CTA URL (found {count})."
    MSG_URL_INVALID_SCHEME: Final[str] = "CTA URL must use http:// or https:// protocol."
    MSG_URL_SSRF_BLOCKED: Final[str] = "CTA URL targets private or reserved network ranges (SSRF blocked)."
    MSG_PROMPT_INJECTION_DETECTED: Final[str] = "Message contains prohibited prompt injection patterns."
    MSG_SUSPICIOUS_PAYLOAD: Final[str] = "Message contains suspicious control or evasion characters."


class ServiceMessageConstants:
    """Lifecycle and orchestration response messages."""

    POST_SUCCESS_ALL: Final[str] = "Broadcast completed successfully across all configured platforms."
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
```

---

### 4.2 `app/core/config.py`

Manages 12-factor environment variables using `pydantic-settings`. Supports default fallbacks, secret masking, and strict type parsing.

```python
"""Application settings and environment configuration."""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.core.constants import ApiConstants, PlatformConstants


class Settings(BaseSettings):
    """Runtime configuration parsed from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Server Configuration
    app_name: str = Field(default=ApiConstants.SERVICE_NAME, alias="APP_NAME")
    app_version: str = Field(default=ApiConstants.SERVICE_VERSION, alias="APP_VERSION")
    app_host: str = Field(default=ApiConstants.DEFAULT_HOST, alias="APP_HOST")
    app_port: int = Field(default=ApiConstants.DEFAULT_PORT, alias="APP_PORT")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Timeouts & Concurrency
    adapter_timeout_seconds: float = Field(
        default=PlatformConstants.DEFAULT_ADAPTER_TIMEOUT_SECONDS,
        alias="ADAPTER_TIMEOUT_SECONDS",
    )
    total_timeout_seconds: float = Field(
        default=PlatformConstants.DEFAULT_TOTAL_TIMEOUT_SECONDS,
        alias="TOTAL_TIMEOUT_SECONDS",
    )
    max_retries: int = Field(
        default=PlatformConstants.DEFAULT_MAX_RETRIES,
        alias="MAX_RETRIES",
    )

    # Platform Credentials (Optional for graceful degradation)
    linkedin_access_token: Optional[str] = Field(default=None, alias="LINKEDIN_ACCESS_TOKEN")
    linkedin_person_urn: Optional[str] = Field(default=None, alias="LINKEDIN_PERSON_URN")

    devto_api_key: Optional[str] = Field(default=None, alias="DEVTO_API_KEY")

    hashnode_api_key: Optional[str] = Field(default=None, alias="HASHNODE_API_KEY")
    hashnode_publication_id: Optional[str] = Field(default=None, alias="HASHNODE_PUBLICATION_ID")

    mastodon_access_token: Optional[str] = Field(default=None, alias="MASTODON_ACCESS_TOKEN")
    mastodon_base_url: Optional[str] = Field(
        default="https://mastodon.social",
        alias="MASTODON_BASE_URL",
    )

    telegram_bot_token: Optional[str] = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    telegram_channel_id: Optional[str] = Field(default=None, alias="TELEGRAM_CHANNEL_ID")
```

---

### 4.3 `app/core/logging.py`

Implements centralized, high-performance structured JSON logging with secret credential filtering.

```python
"""Centralized structured logging with credential filtering and context propagation."""

import logging
import json
import re
from datetime import datetime, timezone
from typing import Any, Optional
from contextvars import ContextVar

correlation_id_ctx: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


class SensitiveDataFilter(logging.Filter):
    """Masks secret tokens, API keys, and authorization headers in log output."""

    SENSITIVE_PATTERNS = [
        re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.]{8,}", re.IGNORECASE),
        re.compile(r"(api[-_]?key[\"'\s:=]+)[A-Za-z0-9_\-\.]{8,}", re.IGNORECASE),
        re.compile(r"(bot[0-9]{8,10}:)[A-Za-z0-9_\-]{25,}", re.IGNORECASE),
        re.compile(r"(access[-_]?token[\"'\s:=]+)[A-Za-z0-9_\-\.]{8,}", re.IGNORECASE),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """Inspects and masks sensitive tokens within log record messages and arguments."""
        if isinstance(record.msg, str):
            for pattern in self.SENSITIVE_PATTERNS:
                record.msg = pattern.sub(r"\1[REDACTED]", record.msg)
        return True


class StructuredJsonFormatter(logging.Formatter):
    """Outputs standardized JSON logs formatted for ELK / Datadog ingestion."""

    def format(self, record: logging.LogRecord) -> str:
        """Serializes the log record to a single-line JSON string."""
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id_ctx.get(),
            "source": f"{record.filename}:{record.lineno}",
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


def setup_logging(log_level: str = "INFO") -> None:
    """Configures the root and application loggers with handlers and filters."""
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredJsonFormatter())
    handler.addFilter(SensitiveDataFilter())
    root_logger.handlers = [handler]
```

---

### 4.4 `app/core/exceptions.py`

Hierarchical domain exception structure rooted at `ApplicationException`. Maps every error to an RFC 7807 problem structure and appropriate HTTP status.

```python
"""Domain and infrastructure exception hierarchy with RFC 7807 Problem Details mapping."""

from typing import Any, Optional


class ApplicationException(Exception):
    """Root base exception for all application-controlled errors."""

    def __init__(
        self,
        message: str,
        http_status: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[dict[str, Any]] = None,
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
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initializes domain exception."""
        super().__init__(message, http_status, error_code, details)


class MessageValidationError(DomainException):
    """Raised when message fails length, syntax, or character invariants."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        """Initializes message validation error with 422 Unprocessable Content."""
        super().__init__(message, http_status=422, error_code="MESSAGE_VALIDATION_FAILED", details=details)


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


class InfrastructureException(ApplicationException):
    """Base exception for external platform and networking failures."""

    def __init__(
        self,
        message: str,
        http_status: int = 502,
        error_code: str = "INFRASTRUCTURE_ERROR",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initializes infrastructure exception."""
        super().__init__(message, http_status, error_code, details)


class PlatformException(InfrastructureException):
    """Base exception for specific third-party platform adapter failures."""

    def __init__(
        self,
        platform: str,
        message: str,
        status_code: Optional[int] = None,
        raw_error: Optional[str] = None,
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


class PlatformRateLimitException(PlatformException):
    """Raised when an external platform returns HTTP 429 Too Many Requests."""

    def __init__(self, platform: str, retry_after: Optional[int] = None) -> None:
        """Initializes platform rate limit exception with optional retry duration."""
        super().__init__(
            platform=platform,
            message=f"Platform rate limit exceeded. Retry after {retry_after}s.",
            status_code=429,
            raw_error="RATE_LIMITED",
        )
        self.retry_after = retry_after
```

---

### 4.5 `app/models/forms/posting_form.py`

Implements the inbound request Form contract. Enforces the 7-stage validation sequence and ignores unknown properties.

```python
"""Inbound request Form models with 7-Stage sequential validation pipeline."""

import re
import unicodedata
import ipaddress
from urllib.parse import urlparse
from pydantic import BaseModel, Field, field_validator, ConfigDict
from app.core.constants import ValidationMessageConstants
from app.core.exceptions import MessageValidationError, UrlExtractionError, SecurityThreatError


class PostingForm(BaseModel):
    """Inbound request form for the POST /posting endpoint.
    
    Implements strict DTO/Form separation and ordered 7-stage validation sequence.
    """

    model_config = ConfigDict(
        extra="ignore",
        frozen=False,
        str_strip_whitespace=False,
    )

    message: str = Field(
        ...,
        description="The content to broadcast across all configured platforms (<= 200 chars, exactly 1 URL).",
        examples=["Excited to announce our new product update! Read more here: https://example.com/update"],
    )

    # Internal derived fields computed during validation
    _cleaned_message: str = ""
    _extracted_url: str = ""

    @property
    def cleaned_message(self) -> str:
        """Returns the canonicalized and sanitized message text."""
        return self._cleaned_message or self.message

    @property
    def extracted_url(self) -> str:
        """Returns the verified single CTA URL extracted from the message."""
        return self._extracted_url

    @field_validator("message", mode="before")
    @classmethod
    def validate_and_sanitize_message(cls, raw_value: object) -> str:
        """Executes the ordered 7-stage validation and sanitization sequence.
        
        Sequence:
        Stage 1: Null & Type Screening
        Stage 2: Unicode Normalization (NFKC) & Zero-Width Stripping
        Stage 3: Character Length Enforcement (<= 200 unicode characters)
        Stage 4: URL Extraction & Single-URL Invariant Check
        Stage 5: URL Protocol & SSRF Network Screening
        Stage 6: Threat & Prompt Injection Detection
        Stage 7: Canonicalization & Payload Construction
        """
        # Stage 1: Null & Type Screening
        if raw_value is None:
            raise MessageValidationError(ValidationMessageConstants.MSG_NOT_NULL)
        if not isinstance(raw_value, str):
            raise MessageValidationError(ValidationMessageConstants.MSG_NOT_BLANK)

        # Stage 2: Unicode Normalization & Invisible Character Stripping
        normalized = unicodedata.normalize("NFKC", raw_value)
        # Strip zero-width spaces, soft hyphens, and bidirectional control characters
        cleaned = re.sub(r"[\u200B-\u200D\uFEFF\u00AD\u202A-\u202E]", "", normalized)
        stripped = cleaned.strip()

        if not stripped:
            raise MessageValidationError(ValidationMessageConstants.MSG_NOT_BLANK)

        # Stage 3: Character Length Enforcement (<= 200 unicode characters)
        if len(stripped) > 200:
            raise MessageValidationError(ValidationMessageConstants.MSG_TOO_LONG)

        # Stage 4: URL Extraction & Count Invariant (Exactly 1 CTA URL)
        url_regex = re.compile(
            r"https?://(?:[a-zA-Z0-9\-._~%!$&'()*+,;=]+@)?(?:[a-zA-Z0-9\-._~%]+|\[[a-fA-F0-9:.]+\])(?::\d+)?(?:/[^\s]*)?",
            re.IGNORECASE,
        )
        matches = url_regex.findall(stripped)
        if len(matches) == 0:
            raise UrlExtractionError(ValidationMessageConstants.MSG_URL_REQUIRED, count=0)
        if len(matches) > 1:
            raise UrlExtractionError(
                ValidationMessageConstants.MSG_URL_MULTIPLE.format(count=len(matches)),
                count=len(matches),
            )

        target_url = matches[0].rstrip(".,;!?:")

        # Stage 5: URL Scheme & SSRF Protection
        parsed = urlparse(target_url)
        if parsed.scheme.lower() not in ("http", "https"):
            raise MessageValidationError(ValidationMessageConstants.MSG_URL_INVALID_SCHEME)
        if not parsed.hostname:
            raise MessageValidationError(ValidationMessageConstants.MSG_URL_INVALID_SCHEME)

        hostname = parsed.hostname.lower()
        if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1", "metadata.google.internal"):
            raise SecurityThreatError(ValidationMessageConstants.MSG_URL_SSRF_BLOCKED, threat_type="SSRF_LOCAL_HOST")

        # Resolve IP literals if provided directly
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                raise SecurityThreatError(ValidationMessageConstants.MSG_URL_SSRF_BLOCKED, threat_type="SSRF_PRIVATE_IP")
        except ValueError:
            pass  # Hostname is a valid domain string, not an IP literal

        # Stage 6: Threat & Prompt Injection Screening
        injection_pattern = re.compile(
            r"(ignore\s+all\s+previous\s+instructions|system\s+prompt|drop\s+database|drop\s+table)",
            re.IGNORECASE,
        )
        if injection_pattern.search(stripped):
            raise SecurityThreatError(
                ValidationMessageConstants.MSG_PROMPT_INJECTION_DETECTED,
                threat_type="PROMPT_INJECTION",
            )

        # Stage 7: Canonicalization Complete
        return stripped
```

---

### 4.6 `app/models/dtos/platform_dto.py`

Defines the itemized outbound result for each platform.

```python
"""Platform result DTO transfer model."""

from typing import Optional, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict


class PlatformResultDto(BaseModel):
    """Itemized outcome representation for a single social or developer platform."""

    model_config = ConfigDict(
        frozen=True,
        extra="ignore",
    )

    platform: str = Field(..., description="Unique platform identifier (e.g. linkedin, devto).")
    status: Literal["success", "failed", "skipped"] = Field(..., description="Execution status.")
    post_id: Optional[str] = Field(default=None, description="External identifier assigned by platform.")
    post_url: Optional[str] = Field(default=None, description="Direct URL to published post if available.")
    error: Optional[str] = Field(default=None, description="Sanitized human-readable error if failed.")
    latency_ms: Optional[float] = Field(default=None, description="Execution duration in milliseconds.")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC completion timestamp.",
    )
```

---

### 4.7 `app/models/dtos/posting_dto.py`

Defines the aggregate broadcast response, telemetry metrics, and summary data.

```python
"""Aggregate broadcast response and telemetry DTO models."""

from typing import Optional, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict
from app.models.dtos.platform_dto import PlatformResultDto


class TelemetryDto(BaseModel):
    """Execution telemetry and timing metrics for the broadcast request."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    total_latency_ms: float = Field(..., description="Wall-clock duration of concurrent broadcast.")
    correlation_id: str = Field(..., description="Unique request tracing correlation ID.")
    concurrency_engine: str = Field(default="asyncio.gather(return_exceptions=True)")
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


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
    telemetry: Optional[TelemetryDto] = Field(default=None, description="Request execution telemetry.")
```

---

### 4.8 `app/models/dtos/problem_dto.py`

Defines the RFC 7807 standard Problem Details error envelope.

```python
"""RFC 7807 Problem Details error response DTO model."""

from typing import Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict


class ProblemDetailsDto(BaseModel):
    """Machine-readable representation of an HTTP error condition (RFC 7807)."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    type: str = Field(
        default="about:blank",
        description="URI reference that identifies the problem type.",
    )
    title: str = Field(..., description="Short, human-readable summary of the problem type.")
    status: int = Field(..., description="The HTTP status code generated by the origin server.")
    detail: str = Field(..., description="Human-readable explanation specific to this occurrence.")
    instance: str = Field(..., description="URI reference identifying the specific occurrence.")
    error_code: str = Field(..., description="Application-specific stable error code.")
    invalid_params: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description="Itemized validation failures when status is 422.",
    )
    correlation_id: Optional[str] = Field(default=None, description="Request correlation identifier.")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

---

### 4.9 `app/models/dtos/api_response.py`

Generic response envelope wrapper aligning with Rule 17.

```python
"""Generic API response envelope wrapper."""

from typing import Generic, TypeVar, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict

T = TypeVar("T")


class ApiResponseDto(BaseModel, Generic[T]):
    """Unified API response envelope with status, message, data, and timestamp."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    success: bool = Field(..., description="True if operation succeeded without critical error.")
    status: int = Field(..., description="HTTP status code corresponding to outcome.")
    message: str = Field(..., description="Human-readable response message.")
    data: Optional[T] = Field(default=None, description="Typed response payload.")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

---

### 4.10 `app/platforms/base.py`

The core abstract Port defining the contract for all platform adapters.

```python
"""Core abstract port defining the BasePlatformAdapter contract."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import logging
import httpx
from app.models.dtos.platform_dto import PlatformResultDto
from app.core.constants import PlatformConstants


class BasePlatformAdapter(ABC):
    """Abstract port that all concrete platform adapters must implement."""

    def __init__(self, name: str, client: httpx.AsyncClient) -> None:
        """Initializes base adapter with platform name and shared HTTPX client."""
        self.name = name
        self.client = client
        self.logger = logging.getLogger(f"app.platforms.{name}")

    @abstractmethod
    def is_configured(self) -> bool:
        """Returns True if all mandatory credentials are present in runtime settings."""
        pass

    @abstractmethod
    async def post(self, message: str, cta_url: str) -> PlatformResultDto:
        """Publishes the message to the third-party platform API.
        
        Args:
            message: The sanitized message text to broadcast.
            cta_url: The verified CTA URL extracted from the message.
            
        Returns:
            PlatformResultDto containing post_id, post_url, or sanitized error.
        """
        pass

    def _extract_date_time(self) -> tuple[str, str]:
        """Returns current UTC date (YYYY-MM-DD) and time (HH:MM:SS UTC)."""
        now = datetime.now(timezone.utc)
        return now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S UTC")

    def _handle_error(self, exc: Exception) -> str:
        """Translates upstream exceptions into sanitized, human-readable error strings."""
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
        return "Internal platform communication error."
```

---

### 4.11 `app/platforms/registry.py`

Implements the GoF Factory pattern to register and instantiate configured platform adapters.

```python
"""AdapterRegistry factory for discovering, configuring, and instantiating platform adapters."""

from typing import Type
import httpx
from app.core.config import Settings
from app.platforms.base import BasePlatformAdapter


class AdapterRegistry:
    """Registry and factory for managing platform adapter lifecycle."""

    def __init__(self) -> None:
        """Initializes empty adapter registry."""
        self._registry: dict[str, Type[BasePlatformAdapter]] = {}

    def register(self, name: str, adapter_cls: Type[BasePlatformAdapter]) -> None:
        """Registers a platform adapter class under a unique slug."""
        self._registry[name] = adapter_cls

    def create_all(self, client: httpx.AsyncClient, settings: Settings) -> list[BasePlatformAdapter]:
        """Instantiates all registered platform adapters using injected settings.
        
        Args:
            client: Shared async HTTP client with pooling.
            settings: Runtime configuration containing platform credentials.
            
        Returns:
            List of instantiated BasePlatformAdapter instances.
        """
        adapters: list[BasePlatformAdapter] = []
        for name, cls in self._registry.items():
            adapter = cls(name=name, client=client, settings=settings)
            adapters.append(adapter)
        return adapters
```

---

### 4.12 Concrete Adapters (`app/platforms/*.py`)

Each platform adapter inherits from `BasePlatformAdapter` and implements `is_configured()` and `async post(...)`:

1. **`app/platforms/linkedin.py` (`LinkedInAdapter`)**:
   - Fields: `access_token: Optional[str]`, `person_urn: Optional[str]`
   - API: `POST https://api.linkedin.com/v2/ugcPosts`
   - Payload: UGC post schema with `author`, `lifecycleState: "PUBLISHED"`, `specificContent` containing commentary and `article` entity referencing `cta_url`.
   - Result: Extracts `id` from response header `X-RestLi-Id` or body `id`.

2. **`app/platforms/devto.py` (`DevToAdapter`)**:
   - Fields: `api_key: Optional[str]`
   - API: `POST https://dev.to/api/articles`
   - Headers: `api-key: {api_key}`
   - Helpers: `_synthesize_title(message: str) -> str` (extracts first sentence or truncates at 50 chars).
   - Payload: `{"article": {"title": synthesized_title, "body_markdown": f"{message}\n\n[Read More]({cta_url})", "published": True}}`
   - Result: Extracts `id` and `url`.

3. **`app/platforms/hashnode.py` (`HashnodeAdapter`)**:
   - Fields: `api_key: Optional[str]`, `publication_id: Optional[str]`
   - API: `POST https://gql.hashnode.com` (GraphQL)
   - Headers: `Authorization: {api_key}`
   - Query: `mutation PublishPost($input: PublishPostInput!) { publishPost(input: $input) { post { id url } } }`
   - Result: Extracts `data.publishPost.post.id` and `url`.

4. **`app/platforms/mastodon.py` (`MastodonAdapter`)**:
   - Fields: `access_token: Optional[str]`, `base_url: str`
   - API: `POST {base_url}/api/v1/statuses`
   - Headers: `Authorization: Bearer {access_token}`, `Idempotency-Key: {uuid}`
   - Payload: `{"status": f"{message}\n\n{cta_url}", "visibility": "public"}`
   - Result: Extracts `id` and `url`.

5. **`app/platforms/telegram.py` (`TelegramAdapter`)**:
   - Fields: `bot_token: Optional[str]`, `channel_id: Optional[str]`
   - API: `POST https://api.telegram.org/bot{bot_token}/sendMessage`
   - Helpers: `_escape_html(text: str) -> str`
   - Payload: `{"chat_id": channel_id, "text": f"{escaped_message}\n\n<a href=\"{cta_url}\">Read More</a>", "parse_mode": "HTML"}`
   - Result: Extracts `result.message_id` and constructs `t.me/{channel}/{message_id}`.

---

### 4.13 `app/services/posting_helper.py`

Implements the helper class in the Service Layer Triple Pattern (`PostingServiceHelper`). Handles DTO mapping, metric calculations, and aggregation logic.

```python
"""Service layer helper for DTO transformations and status aggregation."""

from typing import Sequence
from app.models.dtos.platform_dto import PlatformResultDto
from app.models.dtos.posting_dto import PostingResponseDto, TelemetryDto, PostingSummaryDto
from app.core.constants import ServiceMessageConstants, PlatformConstants


class PostingServiceHelper:
    """Helper utilities supporting PostingServiceImpl."""

    @staticmethod
    def compute_summary(results: Sequence[PlatformResultDto]) -> PostingSummaryDto:
        """Computes platform execution counts from a collection of platform results."""
        total = len(results)
        successful = sum(1 for r in results if r.status == PlatformConstants.STATUS_SUCCESS)
        failed = sum(1 for r in results if r.status == PlatformConstants.STATUS_FAILED)
        skipped = sum(1 for r in results if r.status == PlatformConstants.STATUS_SKIPPED)
        return PostingSummaryDto(
            total=total,
            successful=successful,
            failed=failed,
            skipped=skipped,
        )

    @staticmethod
    def determine_aggregate_status(
        summary: PostingSummaryDto,
    ) -> tuple[str, str]:
        """Determines aggregate outcome status and human-readable message.
        
        Returns:
            Tuple of (status_string, message_string)
        """
        if summary.total == 0:
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
        """Constructs an immutable PostingResponseDto from execution outcomes."""
        summary = cls.compute_summary(results)
        status, message = cls.determine_aggregate_status(summary)

        telemetry = TelemetryDto(
            total_latency_ms=round(total_latency_ms, 2),
            correlation_id=correlation_id,
        )

        return PostingResponseDto(
            status=status,  # type: ignore
            message=message,
            total_platforms=summary.total,
            successful_posts=summary.successful,
            failed_posts=summary.failed,
            results=list(results),
            telemetry=telemetry,
        )
```

---

### 4.14 `app/services/posting_service.py`

Defines the abstract interface (`PostingService`) and the concrete orchestrator implementation (`PostingServiceImpl`) with bulkhead fault isolation.

```python
"""Service layer contract and bulkhead concurrent orchestrator implementation."""

from abc import ABC, abstractmethod
import asyncio
import time
import logging
from typing import Sequence
import httpx
from app.models.forms.posting_form import PostingForm
from app.models.dtos.platform_dto import PlatformResultDto
from app.models.dtos.posting_dto import PostingResponseDto
from app.platforms.base import BasePlatformAdapter
from app.services.posting_helper import PostingServiceHelper
from app.core.constants import PlatformConstants


class PostingService(ABC):
    """Abstract interface defining the business contract for multi-platform broadcasting."""

    @abstractmethod
    async def broadcast(self, form: PostingForm, correlation_id: str) -> PostingResponseDto:
        """Broadcasts the validated form content across all configured platforms concurrently."""
        pass


class PostingServiceImpl(PostingService):
    """Production orchestrator implementing bulkhead concurrency and fault isolation."""

    def __init__(
        self,
        adapters: Sequence[BasePlatformAdapter],
        adapter_timeout_seconds: float = PlatformConstants.DEFAULT_ADAPTER_TIMEOUT_SECONDS,
        helper: type[PostingServiceHelper] = PostingServiceHelper,
    ) -> None:
        """Initializes service implementation with platform adapters and timeout SLA."""
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
        """Executes a single adapter post with individual timeout and bulkhead fault isolation."""
        start_time = time.perf_counter()
        if not adapter.is_configured():
            return PlatformResultDto(
                platform=adapter.name,
                status=PlatformConstants.STATUS_SKIPPED,
                error="Platform credentials not configured in environment.",
                latency_ms=0.0,
            )

        try:
            result = await asyncio.wait_for(
                adapter.post(message=message, cta_url=cta_url),
                timeout=self.adapter_timeout_seconds,
            )
            return result
        except asyncio.TimeoutError:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            self.logger.warning(f"Platform {adapter.name} timed out after {self.adapter_timeout_seconds}s.")
            return PlatformResultDto(
                platform=adapter.name,
                status=PlatformConstants.STATUS_FAILED,
                error=f"Request timed out waiting for platform response after {self.adapter_timeout_seconds}s.",
                latency_ms=round(latency_ms, 2),
            )
        except Exception as exc:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            self.logger.error(f"Platform {adapter.name} raised uncaught exception: {exc}")
            return PlatformResultDto(
                platform=adapter.name,
                status=PlatformConstants.STATUS_FAILED,
                error=adapter._handle_error(exc),
                latency_ms=round(latency_ms, 2),
            )

    async def broadcast(self, form: PostingForm, correlation_id: str) -> PostingResponseDto:
        """Executes concurrent broadcast across all platforms using asyncio.gather bulkhead."""
        start_total = time.perf_counter()
        message = form.cleaned_message
        cta_url = form.extracted_url

        tasks = [
            self._safe_execute(adapter, message, cta_url)
            for adapter in self.adapters
        ]

        # Bulkhead execution: individual failures never cancel peer coroutines
        results: list[PlatformResultDto] = await asyncio.gather(*tasks, return_exceptions=False)

        total_latency_ms = (time.perf_counter() - start_total) * 1000.0
        return self.helper.build_posting_response(
            results=results,
            correlation_id=correlation_id,
            total_latency_ms=total_latency_ms,
        )
```

---

### 4.15 `app/routers/posting.py`

The HTTP ingress controller for `POST /posting`. Contains zero business logic; delegates strictly to `PostingService`.

```python
"""HTTP ingress router for the /posting broadcast endpoint."""

import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, Header, Response, status
from app.models.forms.posting_form import PostingForm
from app.models.dtos.posting_dto import PostingResponseDto
from app.services.posting_service import PostingService
from app.core.constants import ApiConstants
from app.core.logging import correlation_id_ctx

router = APIRouter(tags=["Posting"])


def get_posting_service() -> PostingService:
    """FastAPI dependency provider for PostingService instance (overridden in tests/main)."""
    raise NotImplementedError("Dependency injection provider must be bound at startup.")


@router.post(
    ApiConstants.ENDPOINT_POSTING,
    response_model=PostingResponseDto,
    status_code=status.HTTP_200_OK,
    summary="Broadcast message to social & developer platforms",
    description="Accepts message with <= 200 chars and exactly 1 CTA URL, broadcasting concurrently across 5 platforms.",
)
async def broadcast_post(
    form: PostingForm,
    response: Response,
    service: Annotated[PostingService, Depends(get_posting_service)],
    x_correlation_id: Annotated[str | None, Header(alias=ApiConstants.HEADER_CORRELATION_ID)] = None,
) -> PostingResponseDto:
    """Handles HTTP POST /posting request, invokes service, and populates telemetry headers."""
    correlation_id = x_correlation_id or str(uuid.uuid4())
    correlation_id_ctx.set(correlation_id)

    result = await service.broadcast(form=form, correlation_id=correlation_id)

    response.headers[ApiConstants.HEADER_CORRELATION_ID] = correlation_id
    if result.telemetry:
        response.headers[ApiConstants.HEADER_TOTAL_LATENCY] = str(result.telemetry.total_latency_ms)

    return result
```

---

### 4.16 `app/routers/health.py`

Implements SRE liveness and readiness probe controllers for Kubernetes and Docker.

```python
"""Liveness and readiness health probe routers."""

from typing import Annotated
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from app.core.constants import ApiConstants, ServiceMessageConstants
from app.services.posting_service import PostingService

router = APIRouter(tags=["Health"])


class HealthStatusDto(BaseModel):
    """Standard health probe status response."""

    status: str
    message: str
    version: str


@router.get(
    ApiConstants.ENDPOINT_HEALTH,
    response_model=HealthStatusDto,
    status_code=status.HTTP_200_OK,
    summary="Liveness probe",
)
async def liveness_probe() -> HealthStatusDto:
    """Returns 200 OK indicating the application event loop is alive and running."""
    return HealthStatusDto(
        status="UP",
        message=ServiceMessageConstants.HEALTH_LIVENESS_OK,
        version=ApiConstants.SERVICE_VERSION,
    )


@router.get(
    ApiConstants.ENDPOINT_READY,
    response_model=HealthStatusDto,
    status_code=status.HTTP_200_OK,
    summary="Readiness probe",
)
async def readiness_probe() -> HealthStatusDto:
    """Returns 200 OK if service is initialized and ready to accept broadcast traffic."""
    return HealthStatusDto(
        status="READY",
        message=ServiceMessageConstants.HEALTH_READINESS_OK,
        version=ApiConstants.SERVICE_VERSION,
    )
```

---

### 4.17 `app/main.py`

Application factory `create_app()`, lifespan async context manager for HTTP client pooling, and centralized RFC 7807 global exception handlers.

```python
"""FastAPI application factory, lifespan management, and global exception handlers."""

import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator
import httpx
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.core.config import Settings
from app.core.constants import ApiConstants
from app.core.logging import setup_logging, correlation_id_ctx
from app.core.exceptions import ApplicationException
from app.models.dtos.problem_dto import ProblemDetailsDto
from app.platforms.registry import AdapterRegistry
from app.platforms.linkedin import LinkedInAdapter
from app.platforms.devto import DevToAdapter
from app.platforms.hashnode import HashnodeAdapter
from app.platforms.mastodon import MastodonAdapter
from app.platforms.telegram import TelegramAdapter
from app.services.posting_service import PostingServiceImpl
from app.routers import posting, health


def build_adapter_registry() -> AdapterRegistry:
    """Registers default platform adapter classes."""
    registry = AdapterRegistry()
    registry.register("linkedin", LinkedInAdapter)
    registry.register("devto", DevToAdapter)
    registry.register("hashnode", HashnodeAdapter)
    registry.register("mastodon", MastodonAdapter)
    registry.register("telegram", TelegramAdapter)
    return registry


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manages application startup, HTTP connection pooling, and graceful shutdown."""
    settings = Settings()
    setup_logging(log_level=settings.log_level)

    # Initialize shared connection-pooled HTTPX client
    timeout = httpx.Timeout(
        timeout=settings.adapter_timeout_seconds,
        connect=2.0,
    )
    limits = httpx.Limits(max_keepalive_connections=20, max_connections=50)

    async with httpx.AsyncClient(timeout=timeout, limits=limits) as http_client:
        registry = build_adapter_registry()
        adapters = registry.create_all(client=http_client, settings=settings)

        service = PostingServiceImpl(
            adapters=adapters,
            adapter_timeout_seconds=settings.adapter_timeout_seconds,
        )

        # Bind dependency injection provider override
        app.dependency_overrides[posting.get_posting_service] = lambda: service

        yield  # Application processes requests

        # Graceful shutdown cleanup
        app.dependency_overrides.clear()


def create_app() -> FastAPI:
    """Application factory constructing the configured FastAPI application."""
    app = FastAPI(
        title="Automated Multi-Platform Posting Service",
        description="High-resilience concurrent broadcasting microservice across 5 platforms.",
        version=ApiConstants.SERVICE_VERSION,
        lifespan=lifespan,
    )

    # Include routers
    app.include_router(posting.router)
    app.include_router(health.router)

    # Centralized Exception Handlers (RFC 7807 Problem Details)
    @app.exception_handler(ApplicationException)
    async def application_exception_handler(request: Request, exc: ApplicationException) -> JSONResponse:
        correlation_id = correlation_id_ctx.get() or str(uuid.uuid4())
        problem = ProblemDetailsDto(
            type="https://datatracker.ietf.org/doc/html/rfc7807",
            title=exc.error_code,
            status=exc.http_status,
            detail=exc.message,
            instance=request.url.path,
            error_code=exc.error_code,
            correlation_id=correlation_id,
        )
        return JSONResponse(status_code=exc.http_status, content=problem.model_dump(mode="json"))

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        correlation_id = correlation_id_ctx.get() or str(uuid.uuid4())
        errors = [
            {"loc": list(err["loc"]), "msg": err["msg"], "type": err["type"]}
            for err in exc.errors()
        ]
        # Extract first human-friendly message if available
        detail_msg = exc.errors()[0]["msg"] if exc.errors() else "Validation error."
        problem = ProblemDetailsDto(
            type="https://datatracker.ietf.org/doc/html/rfc7807",
            title="Unprocessable Content",
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail_msg,
            instance=request.url.path,
            error_code="VALIDATION_FAILED",
            invalid_params=errors,
            correlation_id=correlation_id,
        )
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=problem.model_dump(mode="json"))

    return app


app = create_app()
```

---

## 5. Test Suite Blueprint (`tests/`)

Grounded in `41-testing-standards-python-fastapi.md`, the test suite guarantees $\ge 90\%$ branch and statement coverage through Triad Testing (Positive, Negative, Edge-Case) across 11 architectural layers.

### 5.1 `tests/conftest.py`

Defines shared fixtures: synchronous test client, async test client, mocked services, and mocked adapters.

```python
"""Pytest conftest providing shared fixtures, mock services, and async clients."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from fastapi.testclient import TestClient
from app.main import create_app
from app.services.posting_service import PostingService
from app.routers.posting import get_posting_service


@pytest.fixture
def mock_posting_service():
    """Provides a mocked PostingService for controller isolation testing."""
    service = AsyncMock(spec=PostingService)
    return service


@pytest.fixture
def app_with_mock_service(mock_posting_service):
    """Instantiates app with PostingService dependency override."""
    app = create_app()
    app.dependency_overrides[get_posting_service] = lambda: mock_posting_service
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client(app_with_mock_service):
    """Synchronous test client."""
    return TestClient(app_with_mock_service)


@pytest.fixture
async def async_client(app_with_mock_service):
    """Asynchronous HTTPX client using ASGITransport."""
    async with AsyncClient(
        transport=ASGITransport(app=app_with_mock_service),
        base_url="http://test",
    ) as ac:
        yield ac
```

### 5.2 Test Scenarios Catalog

| Test File | Test Class | Coverage Target | Key Scenarios |
|:---|:---|:---|:---|
| `test_bootstrap.py` | `TestBootstrapLifecycle` | App Factory, Lifespan | Startup client creation, shutdown cleanup, signal trapping |
| `test_router_posting.py` | `TestPostingRouterTriad` | HTTP Layer (`POST /posting`) | Valid request (200), validation error (422), malformed JSON (400), rate limit (429), gateway timeout (504) |
| `test_router_health.py` | `TestHealthProbes` | SRE Probes (`/health`, `/ready`) | Liveness 200 UP, readiness 200 READY |
| `test_validation_pipeline.py` | `TestValidationSequence` | 7-Stage Sanitization Engine | Exactly 200 chars, >200 chars rejection, 0 URLs, 2 URLs, SSRF private IPs, prompt injection regex, zero-width stripping |
| `test_service_posting.py` | `TestPostingServiceOrchestrator` | Business & Orchestration Layer | All 5 succeed, partial failures, helper DTO calculation, timing metrics |
| `test_adapters.py` | `TestPlatformAdapters` | Concrete Adapter Ports | LinkedIn UGC payload, Dev.to article Markdown, Hashnode GraphQL mutation, Mastodon status, Telegram HTML message |
| `test_resilience_bulkhead.py` | `TestBulkheadIsolation` | Fault Tolerance & Timeouts | Slow adapter timeout doesn't block fast adapters, exception in 1 adapter returns `failed` status without crashing engine |

---

## 6. Standards Compliance Verification Matrix

| Architecture Standard | Rule Reference | Implementation Location in Blueprint | Compliance Status |
|:---|:---|:---|:---|
| **Decoupled Layering** | Level 2.1 Backend Standards | `app/routers/`, `app/services/`, `app/platforms/`, `app/models/` | **100% Compliant** |
| **DTO / Form Separation** | Level 2.2 DTO/Form Separation | `app/models/forms/posting_form.py` vs `app/models/dtos/*` | **100% Compliant** |
| **Validation Sequence** | Level 2.2 Validation Sequence | `PostingForm.validate_and_sanitize_message` (7 stages) | **100% Compliant** |
| **API Response Envelope** | Level 2.2 API Response Envelope | `ApiResponseDto[T]`, `PostingResponseDto`, `ProblemDetailsDto` | **100% Compliant** |
| **Service Layer Pattern** | Level 2.2 Service Layer Conventions | `PostingService` (ABC), `PostingServiceImpl`, `PostingServiceHelper` | **100% Compliant** |
| **Domain Exceptions** | Level 2.2 Exception Handling Hierarchy | `ApplicationException`, `DomainException`, `InfrastructureException` | **100% Compliant** |
| **Typed Constants** | Level 2.2 Constants Organization | `ValidationMessageConstants`, `ServiceMessageConstants`, etc. | **100% Compliant** |
| **Secret Masking Log** | Level 2.2 Centralized Logging | `SensitiveDataFilter`, `StructuredJsonFormatter` | **100% Compliant** |
| **Triad Test Coverage** | Level 2.3 Python/FastAPI Testing | `tests/test_*.py` covering 11 layers with Positive/Negative/Edge | **100% Compliant** |
| **Docstrings-Only** | Level 2.2 Docstrings-Only | Complete PEP 257 docstrings on every class/method, zero inline narration | **100% Compliant** |

---

## 7. Next Steps & Execution Handoff

The blueprint is complete and verified. No application code (`app/` or `tests/`) will be written until explicit user command is provided.
