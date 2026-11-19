"""Triad unit and integration test suite for FastAPI ingress routers, SRE probes, and RFC 7807 handlers."""

import json
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.core.config import Settings
from app.core.constants import ApiConstants, ErrorCodeConstants
from app.core.exceptions import InfrastructureException
from app.main import build_adapter_registry, create_app, lifespan
from app.models.dtos.platform_dto import PlatformResultDto
from app.models.dtos.posting_dto import PostingResponseDto, TelemetryDto
from app.routers.posting import get_posting_service
from app.services.posting_service import PostingService


@pytest.fixture
def mock_service() -> AsyncMock:
    """Provides a mocked PostingService instance for router isolation testing."""
    return AsyncMock(spec=PostingService)


@pytest.fixture
def app_with_service(mock_service: AsyncMock):
    """Provides a FastAPI test application with PostingService dependency override."""
    test_app = create_app()
    test_app.dependency_overrides[get_posting_service] = lambda: mock_service
    yield test_app
    test_app.dependency_overrides.clear()


@pytest.fixture
def client(app_with_service) -> TestClient:
    """Provides a synchronous TestClient bound to the application with mock service."""
    return TestClient(app_with_service, raise_server_exceptions=False)


class TestPostingRouterTriad:
    """Triad test suite covering POST /posting ingress endpoint."""

    def test_broadcast_success_all_platforms_200(
        self, client: TestClient, mock_service: AsyncMock
    ) -> None:
        """Verifies successful broadcast returns HTTP 200 with telemetry headers."""
        mock_result = PostingResponseDto(
            success=True,
            status="success",
            message="Broadcast completed successfully across all configured platforms.",
            total_platforms=5,
            successful_posts=5,
            failed_posts=0,
            execution_time_seconds=1.428,
            results=[
                PlatformResultDto(
                    platform="LinkedIn",
                    status="success",
                    posted_url="https://www.linkedin.com/feed/update/urn:li:share:123",
                    public_access=True,
                    date="2026-11-19",
                    time="12:00:00",
                    latency_ms=1400,
                    error=None,
                )
            ],
            telemetry=TelemetryDto(
                total_latency_ms=1428.0,
                correlation_id="test-corr-id",
            ),
        )
        mock_service.broadcast.return_value = mock_result

        payload = {
            "message": "Scale your velocity with high-throughput event-driven microservices! https://techdeveloper.io"
        }
        response = client.post(
            ApiConstants.ENDPOINT_POSTING,
            json=payload,
            headers={ApiConstants.HEADER_CORRELATION_ID: "client-corr-001"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["total_platforms"] == 5
        assert data["successful_posts"] == 5
        assert response.headers[ApiConstants.HEADER_CORRELATION_ID] == "client-corr-001"
        assert response.headers[ApiConstants.HEADER_REQUEST_ID] == "client-corr-001"
        assert ApiConstants.HEADER_TOTAL_LATENCY in response.headers
        assert "X-Process-Time" in response.headers

    def test_broadcast_partial_success_200(
        self, client: TestClient, mock_service: AsyncMock
    ) -> None:
        """Verifies partial platform degradation returns HTTP 200 with partial_success status."""
        mock_result = PostingResponseDto(
            success=True,
            status="partial_success",
            message="Broadcast completed with partial platform failures.",
            total_platforms=5,
            successful_posts=4,
            failed_posts=1,
            execution_time_seconds=1.15,
            results=[],
        )
        mock_service.broadcast.return_value = mock_result

        payload = {
            "message": "Explore our modern cloud architectures today! https://techdeveloper.io"
        }
        response = client.post(ApiConstants.ENDPOINT_POSTING, json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "partial_success"

    def test_client_request_id_forwarding(
        self, client: TestClient, mock_service: AsyncMock
    ) -> None:
        """Verifies X-Request-ID header is propagated when X-Correlation-ID is omitted."""
        mock_result = PostingResponseDto(
            success=True,
            status="success",
            message="Broadcast completed successfully.",
            total_platforms=5,
            successful_posts=5,
            failed_posts=0,
            execution_time_seconds=None,
            results=[],
            telemetry=TelemetryDto(
                total_latency_ms=950.0,
                correlation_id="req-uuid-999",
            ),
        )
        mock_service.broadcast.return_value = mock_result

        payload = {"message": "Cloud microservices at scale! https://techdeveloper.io"}
        response = client.post(
            ApiConstants.ENDPOINT_POSTING,
            json=payload,
            headers={ApiConstants.HEADER_REQUEST_ID: "req-uuid-999"},
        )

        assert response.status_code == 200
        assert response.headers[ApiConstants.HEADER_REQUEST_ID] == "req-uuid-999"
        assert response.headers[ApiConstants.HEADER_CORRELATION_ID] == "req-uuid-999"
        assert response.headers[ApiConstants.HEADER_TOTAL_LATENCY] == "950.0"

    def test_validation_error_over_200_chars_returns_422(self, client: TestClient) -> None:
        """Verifies exceeding 200 characters triggers HTTP 422 with ERR_CHAR_LIMIT_EXCEEDED."""
        payload = {"message": "A" * 180 + " https://techdeveloper.io/very-long-path-that-exceeds"}
        response = client.post(ApiConstants.ENDPOINT_POSTING, json=payload)

        assert response.status_code == 422
        assert response.headers["Content-Type"] == "application/problem+json"
        data = response.json()
        assert data["status"] == 422
        assert data["code"] == ErrorCodeConstants.ERR_CHAR_LIMIT_EXCEEDED
        assert data["invalid_params"] is not None
        assert len(data["invalid_params"]) > 0

    def test_validation_error_zero_urls_returns_422(self, client: TestClient) -> None:
        """Verifies omitting CTA link triggers HTTP 422 with ERR_MISSING_CTA_URL."""
        payload = {"message": "Message without any call-to-action link."}
        response = client.post(ApiConstants.ENDPOINT_POSTING, json=payload)

        assert response.status_code == 422
        assert response.headers["Content-Type"] == "application/problem+json"
        data = response.json()
        assert data["code"] == ErrorCodeConstants.ERR_MISSING_CTA_URL

    def test_validation_error_multiple_urls_returns_422(self, client: TestClient) -> None:
        """Verifies multiple CTA links trigger HTTP 422 with ERR_MULTIPLE_CTA_URLS."""
        payload = {"message": "Check https://techdeveloper.io and https://google.com"}
        response = client.post(ApiConstants.ENDPOINT_POSTING, json=payload)

        assert response.status_code == 422
        assert response.headers["Content-Type"] == "application/problem+json"
        data = response.json()
        assert data["code"] == ErrorCodeConstants.ERR_MULTIPLE_CTA_URLS

    def test_validation_error_empty_message_returns_422(self, client: TestClient) -> None:
        """Verifies whitespace-only message triggers HTTP 422 with ERR_EMPTY_MESSAGE."""
        payload = {"message": "   "}
        response = client.post(ApiConstants.ENDPOINT_POSTING, json=payload)

        assert response.status_code == 422
        data = response.json()
        assert data["code"] == ErrorCodeConstants.ERR_EMPTY_MESSAGE

    def test_validation_error_missing_field_returns_422(self, client: TestClient) -> None:
        """Verifies missing message field triggers HTTP 422 with ERR_MISSING_FIELD."""
        payload: dict[str, Any] = {}
        response = client.post(ApiConstants.ENDPOINT_POSTING, json=payload)

        assert response.status_code == 422
        data = response.json()
        assert data["code"] == ErrorCodeConstants.ERR_MISSING_FIELD

    def test_validation_error_ssrf_returns_422(self, client: TestClient) -> None:
        """Verifies loopback URL triggers HTTP 422 with ERR_SSRF_PROHIBITED."""
        payload = {"message": "Test SSRF https://127.0.0.1/admin"}
        response = client.post(ApiConstants.ENDPOINT_POSTING, json=payload)

        assert response.status_code == 422
        data = response.json()
        assert data["code"] == ErrorCodeConstants.ERR_SSRF_PROHIBITED

    def test_validation_error_trojan_source_control_chars_returns_422(
        self, client: TestClient
    ) -> None:
        """Verifies bidirectional override characters trigger HTTP 422 with ERR_MALICIOUS_CONTROL_CHARS."""
        payload = {"message": "Test \u202E override https://techdeveloper.io"}
        response = client.post(ApiConstants.ENDPOINT_POSTING, json=payload)

        assert response.status_code == 422
        data = response.json()
        assert data["code"] == ErrorCodeConstants.ERR_MALICIOUS_CONTROL_CHARS

    def test_validation_error_prohibited_port_returns_422(self, client: TestClient) -> None:
        """Verifies disallowed port triggers HTTP 422 with ERR_PROHIBITED_PORT."""
        payload = {"message": "Test port https://example.com:22/ssh"}
        response = client.post(ApiConstants.ENDPOINT_POSTING, json=payload)

        assert response.status_code == 422
        data = response.json()
        assert data["code"] == ErrorCodeConstants.ERR_PROHIBITED_PORT

    def test_validation_error_invalid_scheme_returns_422(self, client: TestClient) -> None:
        """Verifies unsupported protocol scheme triggers HTTP 422 with ERR_INVALID_URL_SCHEME."""
        payload = {"message": "Visit ftp://files.techdeveloper.io/doc"}
        response = client.post(ApiConstants.ENDPOINT_POSTING, json=payload)

        assert response.status_code == 422
        data = response.json()
        assert data["code"] == ErrorCodeConstants.ERR_INVALID_URL_SCHEME

    def test_malformed_json_body_returns_400(self, client: TestClient) -> None:
        """Verifies malformed JSON payload returns HTTP 400 with ERR_MALFORMED_JSON."""
        raw_broken_json = '{"message": "broken json without closing quote'
        response = client.post(
            ApiConstants.ENDPOINT_POSTING,
            content=raw_broken_json,
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 400
        assert response.headers["Content-Type"] == "application/problem+json"
        data = response.json()
        assert data["code"] == ErrorCodeConstants.ERR_MALFORMED_JSON
        assert data["status"] == 400

    def test_application_exception_handled_as_rfc7807(
        self, client: TestClient, mock_service: AsyncMock
    ) -> None:
        """Verifies ApplicationException raised by service is formatted as RFC 7807 response."""
        mock_service.broadcast.side_effect = InfrastructureException(
            message="Gateway multi-platform timeout exceeded SLA.",
            http_status=504,
            error_code=ErrorCodeConstants.ERR_GATEWAY_TIMEOUT,
        )

        payload = {"message": "Valid broadcast payload! https://techdeveloper.io"}
        response = client.post(ApiConstants.ENDPOINT_POSTING, json=payload)

        assert response.status_code == 504
        assert response.headers["Content-Type"] == "application/problem+json"
        data = response.json()
        assert data["code"] == ErrorCodeConstants.ERR_GATEWAY_TIMEOUT
        assert data["status"] == 504

    def test_uncaught_runtime_exception_handled_as_500(
        self, client: TestClient, mock_service: AsyncMock
    ) -> None:
        """Verifies uncaught runtime exceptions return HTTP 500 with ERR_INTERNAL_SERVER."""
        mock_service.broadcast.side_effect = RuntimeError("Fatal memory corrupt simulation.")

        payload = {"message": "Valid broadcast payload! https://techdeveloper.io"}
        response = client.post(ApiConstants.ENDPOINT_POSTING, json=payload)

        assert response.status_code == 500
        assert response.headers["Content-Type"] == "application/problem+json"
        data = response.json()
        assert data["code"] == ErrorCodeConstants.ERR_INTERNAL_SERVER
        assert data["status"] == 500

    def test_get_posting_service_default_raises_not_implemented(self) -> None:
        """Verifies default get_posting_service dependency provider raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="Dependency injection provider"):
            get_posting_service()


class TestHealthAndReadinessProbes:
    """Triad test suite covering SRE health and readiness probes."""

    def test_liveness_probe_returns_200_ok(self, client: TestClient) -> None:
        """Verifies GET /health liveness probe returns HTTP 200 with ok status."""
        response = client.get(ApiConstants.ENDPOINT_HEALTH)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == ApiConstants.SERVICE_VERSION
        assert "timestamp" in data
        assert datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))

    def test_readiness_probe_returns_200_ready(self, client: TestClient) -> None:
        """Verifies GET /ready readiness probe returns HTTP 200 with platform statuses."""
        response = client.get(ApiConstants.ENDPOINT_READY)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["version"] == ApiConstants.SERVICE_VERSION
        assert isinstance(data["platforms_configured"], int)
        assert isinstance(data["adapters"], dict)
        assert "linkedin" in data["adapters"]
        assert "devto" in data["adapters"]
        assert "hashnode" in data["adapters"]
        assert "mastodon" in data["adapters"]
        assert "telegram" in data["adapters"]

    def test_readiness_probe_with_all_credentials_configured(self) -> None:
        """Verifies readiness probe reports 5 platforms configured when all credentials are set."""
        mock_settings = Settings(
            linkedin_access_token="tok",
            linkedin_person_urn="urn:li:person:123",
            devto_api_key="key",
            hashnode_api_key="key",
            hashnode_publication_id="pub-123",
            mastodon_access_token="tok",
            mastodon_base_url="https://mastodon.social",
            telegram_bot_token="bot:tok",
            telegram_channel_id="@chan",
        )
        with patch("app.routers.health.Settings", return_value=mock_settings):
            app = create_app()
            test_client = TestClient(app)
            response = test_client.get(ApiConstants.ENDPOINT_READY)

            assert response.status_code == 200
            data = response.json()
            assert data["platforms_configured"] == 5
            assert data["adapters"]["linkedin"] is True
            assert data["adapters"]["devto"] is True
            assert data["adapters"]["hashnode"] is True
            assert data["adapters"]["mastodon"] is True
            assert data["adapters"]["telegram"] is True

    def test_readiness_probe_with_no_credentials_configured(self) -> None:
        """Verifies readiness probe reports 0 platforms configured when all credentials are empty."""
        mock_settings = Settings(
            linkedin_access_token=None,
            linkedin_person_urn=None,
            devto_api_key=None,
            hashnode_api_key=None,
            hashnode_publication_id=None,
            mastodon_access_token=None,
            mastodon_base_url=None,
            telegram_bot_token=None,
            telegram_channel_id=None,
        )
        with patch("app.routers.health.Settings", return_value=mock_settings):
            app = create_app()
            test_client = TestClient(app)
            response = test_client.get(ApiConstants.ENDPOINT_READY)

            assert response.status_code == 200
            data = response.json()
            assert data["platforms_configured"] == 0
            assert data["adapters"]["linkedin"] is False
            assert data["adapters"]["devto"] is False


class TestApplicationLifecycleAndStarletteHandlers:
    """Test suite covering application factory, lifespan, and Starlette HTTP handlers."""

    def test_create_app_factory_metadata(self) -> None:
        """Verifies create_app produces application with correct OpenAPI title and version."""
        test_app = create_app()
        assert test_app.title == "Automated Multi-Platform Posting Service API"
        assert test_app.version == ApiConstants.SERVICE_VERSION

    def test_starlette_not_found_returns_404_problem_details(
        self, client: TestClient
    ) -> None:
        """Verifies non-existent route returns HTTP 404 with RFC 7807 problem details."""
        response = client.get("/nonexistent-endpoint-route")

        assert response.status_code == 404
        assert response.headers["Content-Type"] == "application/problem+json"
        data = response.json()
        assert data["status"] == 404
        assert data["code"] == "ERR_HTTP_404"

    def test_starlette_method_not_allowed_returns_405_problem_details(
        self, client: TestClient
    ) -> None:
        """Verifies unsupported HTTP method returns HTTP 405 with RFC 7807 problem details."""
        response = client.get(ApiConstants.ENDPOINT_POSTING)

        assert response.status_code == 405
        assert response.headers["Content-Type"] == "application/problem+json"
        data = response.json()
        assert data["status"] == 405
        assert data["code"] == "ERR_HTTP_405"

    def test_build_adapter_registry_registers_all_five_adapters(self) -> None:
        """Verifies build_adapter_registry registers all 5 concrete platform adapters."""
        registry = build_adapter_registry()
        registered = registry.registered_names()
        assert "linkedin" in registered
        assert "devto" in registered
        assert "hashnode" in registered
        assert "mastodon" in registered
        assert "telegram" in registered

    @pytest.mark.asyncio
    async def test_lifespan_lifecycle_management(self) -> None:
        """Verifies lifespan startup binds posting service and cleanup restores overrides."""
        test_app = create_app()
        async with lifespan(test_app):
            assert get_posting_service in test_app.dependency_overrides
            bound_service = test_app.dependency_overrides[get_posting_service]()
            assert bound_service is not None

        assert get_posting_service not in test_app.dependency_overrides

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("error_msg", "expected_code"),
        [
            ("Character count 201 exceeds limit of 200", ErrorCodeConstants.ERR_CHAR_LIMIT_EXCEEDED),
            ("Message must contain exactly one valid CTA URL (found 0)", ErrorCodeConstants.ERR_MISSING_CTA_URL),
            ("Message contains multiple URLs (found 2)", ErrorCodeConstants.ERR_MULTIPLE_CTA_URLS),
            ("Missing protocol scheme http:// or https://", ErrorCodeConstants.ERR_INVALID_URL_SCHEME),
            ("Message cannot be empty or whitespace", ErrorCodeConstants.ERR_EMPTY_MESSAGE),
            ("Contains prohibited bidirectional control characters", ErrorCodeConstants.ERR_MALICIOUS_CONTROL_CHARS),
            ("SSRF to private network blocked", ErrorCodeConstants.ERR_SSRF_PROHIBITED),
            ("Prohibited port 22 blocked", ErrorCodeConstants.ERR_PROHIBITED_PORT),
            ("Unknown generic violation", "ERR_VALIDATION_FAILED"),
        ],
    )
    async def test_validation_exception_handler_error_code_mapping(
        self, error_msg: str, expected_code: str
    ) -> None:
        """Verifies validation_exception_handler maps Pydantic validation errors to exact RFC 7807 codes."""
        test_app = create_app()
        handler = test_app.exception_handlers[RequestValidationError]
        request = Request(scope={"type": "http", "method": "POST", "path": "/posting", "headers": []})
        exc = RequestValidationError([{"loc": ("body", "message"), "msg": error_msg, "type": "value_error"}])
        response = await handler(request, exc)
        assert response.status_code == 422
        assert response.headers["Content-Type"] == "application/problem+json"
        body = json.loads(response.body.decode("utf-8"))
        assert body["code"] == expected_code

