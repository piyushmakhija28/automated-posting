"""FastAPI application factory, lifespan management, and global RFC 7807 handlers."""

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import Settings
from app.core.constants import ApiConstants, ErrorCodeConstants
from app.core.exceptions import ApplicationException
from app.core.logging import correlation_id_ctx, setup_logging
from app.models.dtos.problem_dto import ProblemDetailsDto
from app.platforms.devto import DevToAdapter
from app.platforms.hashnode import HashnodeAdapter
from app.platforms.linkedin import LinkedInAdapter
from app.platforms.mastodon import MastodonAdapter
from app.platforms.registry import AdapterRegistry
from app.platforms.telegram import TelegramAdapter
from app.routers.health import router as health_router
from app.routers.posting import get_posting_service
from app.routers.posting import router as posting_router
from app.services.posting_service import PostingServiceImpl


def get_error_type_and_title(error_code: str) -> tuple[str, str]:
    """Maps standardized error codes to RFC 7807 type URIs and titles matching openapi.yaml.

    Args:
        error_code: Standardized domain error code.

    Returns:
        tuple[str, str]: Tuple of (type_uri, title).
    """
    error_metadata: dict[str, tuple[str, str]] = {
        ErrorCodeConstants.ERR_CHAR_LIMIT_EXCEEDED: (
            "https://dxora.com/errors/character-budget-exceeded",
            "Character Budget Exceeded",
        ),
        ErrorCodeConstants.ERR_MISSING_CTA_URL: (
            "https://dxora.com/errors/missing-cta-url",
            "Missing Call-to-Action URL",
        ),
        ErrorCodeConstants.ERR_MULTIPLE_CTA_URLS: (
            "https://dxora.com/errors/multiple-cta-urls",
            "Multiple Call-to-Action URLs Detected",
        ),
        ErrorCodeConstants.ERR_INVALID_URL_SCHEME: (
            "https://dxora.com/errors/invalid-url-scheme",
            "Missing Protocol Scheme",
        ),
        ErrorCodeConstants.ERR_EMPTY_MESSAGE: (
            "https://dxora.com/errors/empty-message",
            "Empty Message Body",
        ),
        ErrorCodeConstants.ERR_MISSING_FIELD: (
            "https://dxora.com/errors/missing-field",
            "Missing Required Payload Field",
        ),
        ErrorCodeConstants.ERR_MALFORMED_JSON: (
            "https://dxora.com/errors/malformed-json",
            "Malformed JSON Request Body",
        ),
        ErrorCodeConstants.ERR_MALICIOUS_CONTROL_CHARS: (
            "https://dxora.com/errors/malicious-control-chars",
            "Prohibited Bidirectional Control Characters",
        ),
        ErrorCodeConstants.ERR_SSRF_PROHIBITED: (
            "https://dxora.com/errors/ssrf-prohibited",
            "Prohibited Destination Hostname",
        ),
        ErrorCodeConstants.ERR_PROHIBITED_PORT: (
            "https://dxora.com/errors/prohibited-port",
            "Prohibited Destination Port",
        ),
        ErrorCodeConstants.ERR_GATEWAY_TIMEOUT: (
            "https://dxora.com/errors/gateway-timeout",
            "Gateway Execution Timeout",
        ),
        ErrorCodeConstants.ERR_INTERNAL_SERVER: (
            "https://dxora.com/errors/internal-server-error",
            "Internal Server Error",
        ),
    }
    return error_metadata.get(
        error_code,
        (
            f"https://dxora.com/errors/{error_code.lower().replace('_', '-')}",
            error_code.replace("_", " ").title(),
        ),
    )


def build_adapter_registry() -> AdapterRegistry:
    """Builds and populates the platform adapter registry with concrete implementations.

    Returns:
        AdapterRegistry: Configured registry with all 5 platform adapters registered.
    """
    registry = AdapterRegistry()
    registry.register_adapter("linkedin", LinkedInAdapter)
    registry.register_adapter("devto", DevToAdapter)
    registry.register_adapter("hashnode", HashnodeAdapter)
    registry.register_adapter("mastodon", MastodonAdapter)
    registry.register_adapter("telegram", TelegramAdapter)
    return registry


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manages application startup, HTTP connection pooling, and graceful shutdown.

    Args:
        app: The FastAPI application instance being managed.

    Yields:
        None: Yields control to process inbound HTTP requests while services are bound.
    """
    settings = Settings()
    setup_logging(log_level=settings.log_level)

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

        app.dependency_overrides[get_posting_service] = lambda: service
        yield
        app.dependency_overrides.clear()


def create_app() -> FastAPI:
    """Application factory constructing and configuring the FastAPI instance.

    Returns:
        FastAPI: Fully configured FastAPI application with routers and exception handlers.
    """
    app = FastAPI(
        title="Automated Multi-Platform Posting Service API",
        description=(
            "Production-grade asynchronous microservice developed for the Dxora Technologies "
            "Practical Test assessment. Concurrently broadcasts short messages and CTA links "
            "across LinkedIn, Dev.to, Hashnode, Mastodon, and Telegram with bulkhead isolation."
        ),
        version=ApiConstants.SERVICE_VERSION,
        lifespan=lifespan,
    )

    app.include_router(posting_router)
    app.include_router(health_router)

    @app.exception_handler(ApplicationException)
    async def application_exception_handler(
        request: Request, exc: ApplicationException
    ) -> JSONResponse:
        """Translates internal application and domain exceptions into RFC 7807 responses.

        Args:
            request: The inbound Starlette HTTP request.
            exc: The raised ApplicationException instance.

        Returns:
            JSONResponse: Standardized RFC 7807 problem details response.
        """
        correlation_id = (
            correlation_id_ctx.get()
            or request.headers.get(ApiConstants.HEADER_REQUEST_ID)
            or request.headers.get(ApiConstants.HEADER_CORRELATION_ID)
            or str(uuid.uuid4())
        )
        type_uri, title = get_error_type_and_title(exc.error_code)
        invalid_params = (
            [{"name": "message", "reason": exc.message}]
            if exc.http_status == status.HTTP_422_UNPROCESSABLE_ENTITY
            else None
        )

        problem = ProblemDetailsDto(
            type=type_uri,
            title=title,
            status=exc.http_status,
            detail=exc.message,
            instance=str(request.url.path),
            code=exc.error_code,
            error_code=exc.error_code,
            invalid_params=invalid_params,
            correlation_id=correlation_id,
        )

        headers = {
            "Content-Type": "application/problem+json",
            ApiConstants.HEADER_CORRELATION_ID: correlation_id,
            ApiConstants.HEADER_REQUEST_ID: correlation_id,
        }
        return JSONResponse(
            status_code=exc.http_status,
            content=problem.model_dump(mode="json"),
            media_type="application/problem+json",
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Translates Pydantic request validation errors into RFC 7807 responses.

        Args:
            request: The inbound Starlette HTTP request.
            exc: The raised RequestValidationError instance.

        Returns:
            JSONResponse: Standardized RFC 7807 problem details response.
        """
        correlation_id = (
            correlation_id_ctx.get()
            or request.headers.get(ApiConstants.HEADER_REQUEST_ID)
            or request.headers.get(ApiConstants.HEADER_CORRELATION_ID)
            or str(uuid.uuid4())
        )

        invalid_params: list[dict[str, Any]] = []
        is_malformed_json = False

        for err in exc.errors():
            err_type = str(err.get("type", ""))
            if err_type in ("json_invalid", "json_type"):
                is_malformed_json = True
            loc = err.get("loc", ())
            field_name = str(loc[-1]) if loc else "message"
            raw_msg = str(err.get("msg", "Validation error"))
            cleaned_reason = raw_msg.removeprefix("Value error, ").strip()
            invalid_params.append({"name": field_name, "reason": cleaned_reason})

        if is_malformed_json:
            http_status = status.HTTP_400_BAD_REQUEST
            code = ErrorCodeConstants.ERR_MALFORMED_JSON
            detail = (
                "The request body could not be parsed as valid JSON. "
                "Check for unmatched braces or trailing commas."
            )
        else:
            http_status = status.HTTP_422_UNPROCESSABLE_ENTITY
            first_msg = invalid_params[0]["reason"] if invalid_params else "Validation failed."
            first_type = str(exc.errors()[0].get("type", "")) if exc.errors() else ""

            if (
                "200" in first_msg
                or "budget" in first_msg.lower()
                or "too long" in first_msg.lower()
            ):
                code = ErrorCodeConstants.ERR_CHAR_LIMIT_EXCEEDED
                detail = first_msg
            elif (
                "found 0" in first_msg
                or "0 URLs" in first_msg
                or ("CTA URL" in first_msg and "required" in first_msg.lower())
            ):
                code = ErrorCodeConstants.ERR_MISSING_CTA_URL
                detail = first_msg
            elif "multiple" in first_msg.lower() or (
                "found" in first_msg.lower() and "urls" in first_msg.lower()
            ):
                code = ErrorCodeConstants.ERR_MULTIPLE_CTA_URLS
                detail = first_msg
            elif "scheme" in first_msg.lower() or "protocol" in first_msg.lower():
                code = ErrorCodeConstants.ERR_INVALID_URL_SCHEME
                detail = first_msg
            elif (
                "empty" in first_msg.lower()
                or "whitespace" in first_msg.lower()
                or "blank" in first_msg.lower()
            ):
                code = ErrorCodeConstants.ERR_EMPTY_MESSAGE
                detail = first_msg
            elif "missing" in first_type or "field required" in first_msg.lower():
                code = ErrorCodeConstants.ERR_MISSING_FIELD
                detail = (
                    f"Field '{invalid_params[0]['name']}' is required in request body."
                    if invalid_params
                    else first_msg
                )
            elif (
                "bidirectional" in first_msg.lower()
                or "trojan" in first_msg.lower()
                or "control" in first_msg.lower()
            ):
                code = ErrorCodeConstants.ERR_MALICIOUS_CONTROL_CHARS
                detail = first_msg
            elif (
                "ssrf" in first_msg.lower()
                or "private" in first_msg.lower()
                or "loopback" in first_msg.lower()
                or "reserved" in first_msg.lower()
            ):
                code = ErrorCodeConstants.ERR_SSRF_PROHIBITED
                detail = first_msg
            elif "port" in first_msg.lower():
                code = ErrorCodeConstants.ERR_PROHIBITED_PORT
                detail = first_msg
            else:
                code = "ERR_VALIDATION_FAILED"
                detail = first_msg

        type_uri, title = get_error_type_and_title(code)

        problem = ProblemDetailsDto(
            type=type_uri,
            title=title,
            status=http_status,
            detail=detail,
            instance=str(request.url.path),
            code=code,
            error_code=code,
            invalid_params=invalid_params,
            correlation_id=correlation_id,
        )

        headers = {
            "Content-Type": "application/problem+json",
            ApiConstants.HEADER_CORRELATION_ID: correlation_id,
            ApiConstants.HEADER_REQUEST_ID: correlation_id,
        }
        return JSONResponse(
            status_code=http_status,
            content=problem.model_dump(mode="json"),
            media_type="application/problem+json",
            headers=headers,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        """Translates standard HTTP errors (such as 404 and 405) into RFC 7807 responses.

        Args:
            request: The inbound Starlette HTTP request.
            exc: The raised StarletteHTTPException instance.

        Returns:
            JSONResponse: Standardized RFC 7807 problem details response.
        """
        correlation_id = (
            correlation_id_ctx.get()
            or request.headers.get(ApiConstants.HEADER_REQUEST_ID)
            or request.headers.get(ApiConstants.HEADER_CORRELATION_ID)
            or str(uuid.uuid4())
        )
        code = f"ERR_HTTP_{exc.status_code}"
        type_uri = f"https://dxora.com/errors/http-{exc.status_code}"
        title = str(exc.detail) if isinstance(exc.detail, str) else "HTTP Error"

        problem = ProblemDetailsDto(
            type=type_uri,
            title=title,
            status=exc.status_code,
            detail=str(exc.detail),
            instance=str(request.url.path),
            code=code,
            error_code=code,
            correlation_id=correlation_id,
        )

        headers = {
            "Content-Type": "application/problem+json",
            ApiConstants.HEADER_CORRELATION_ID: correlation_id,
            ApiConstants.HEADER_REQUEST_ID: correlation_id,
        }
        return JSONResponse(
            status_code=exc.status_code,
            content=problem.model_dump(mode="json"),
            media_type="application/problem+json",
            headers=headers,
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Failsafe exception handler intercepting unhandled runtime errors with HTTP 500.

        Args:
            request: The inbound Starlette HTTP request.
            exc: The uncaught Exception instance.

        Returns:
            JSONResponse: Standardized RFC 7807 internal server error response.
        """
        correlation_id = (
            correlation_id_ctx.get()
            or request.headers.get(ApiConstants.HEADER_REQUEST_ID)
            or request.headers.get(ApiConstants.HEADER_CORRELATION_ID)
            or str(uuid.uuid4())
        )
        problem = ProblemDetailsDto(
            type="https://dxora.com/errors/internal-server-error",
            title="Internal Server Error",
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected runtime exception occurred. Reference X-Request-ID in log investigations.",
            instance=str(request.url.path),
            code=ErrorCodeConstants.ERR_INTERNAL_SERVER,
            error_code=ErrorCodeConstants.ERR_INTERNAL_SERVER,
            correlation_id=correlation_id,
        )

        headers = {
            "Content-Type": "application/problem+json",
            ApiConstants.HEADER_CORRELATION_ID: correlation_id,
            ApiConstants.HEADER_REQUEST_ID: correlation_id,
        }
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=problem.model_dump(mode="json"),
            media_type="application/problem+json",
            headers=headers,
        )

    return app


app = create_app()
