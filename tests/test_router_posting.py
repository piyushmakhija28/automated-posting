"""Triad unit and integration test suite covering the POST /posting ingress endpoint."""

import json
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from httpx import AsyncClient
from starlette.requests import Request

from app.core.constants import ApiConstants, ErrorCodeConstants
from app.core.exceptions import InfrastructureException
from app.models.dtos.platform_dto import PlatformResultDto
from app.models.dtos.posting_dto import PostingResponseDto, TelemetryDto


class TestPostingRouterTriad:
    """Triad test suite covering POST /posting ingress endpoint."""

    def test_broadcast_success_all_platforms_200(
        self, client: TestClient, mock_posting_service: AsyncMock
    ) -> None:
        """Verifies TC-POS-01: Standard broadcast returns HTTP 200 with telemetry headers."""
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
        mock_posting_service.broadcast.return_value = mock_result

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

    @pytest.mark.asyncio
    async def test_broadcast_success_async_client_200(
        self, async_client: AsyncClient, mock_posting_service: AsyncMock
    ) -> None:
        """Verifies asynchronous client non-blocking execution returns HTTP 200."""
        mock_result = PostingResponseDto(
            success=True,
            status="success",
            message="Broadcast completed successfully.",
            total_platforms=5,
            successful_posts=5,
            failed_posts=0,
            execution_time_seconds=0.85,
            results=[],
            telemetry=TelemetryDto(
                total_latency_ms=850.0,
                correlation_id="async-test-id",
            ),
        )
        mock_posting_service.broadcast.return_value = mock_result

        payload = {"message": "Non-blocking async HTTPX dispatch test! https://techdeveloper.io"}
        response = await async_client.post(ApiConstants.ENDPOINT_POSTING, json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert ApiConstants.HEADER_TOTAL_LATENCY in response.headers

    def test_broadcast_partial_success_200(
        self, client: TestClient, mock_posting_service: AsyncMock
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
        mock_posting_service.broadcast.return_value = mock_result

        payload = {
            "message": "Explore our modern cloud architectures today! https://techdeveloper.io"
        }
        response = client.post(ApiConstants.ENDPOINT_POSTING, json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "partial_success"

    def test_client_request_id_forwarding(
        self, client: TestClient, mock_posting_service: AsyncMock
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
        mock_posting_service.broadcast.return_value = mock_result

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
        """Verifies TC-NEG-01: Exceeding 200 characters triggers HTTP 422 with ERR_CHAR_LIMIT_EXCEEDED."""
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
        """Verifies TC-NEG-02: Omitting CTA link triggers HTTP 422 with ERR_MISSING_CTA_URL."""
        payload = {"message": "Message without any call-to-action link."}
        response = client.post(ApiConstants.ENDPOINT_POSTING, json=payload)

        assert response.status_code == 422
        assert response.headers["Content-Type"] == "application/problem+json"
        data = response.json()
        assert data["code"] == ErrorCodeConstants.ERR_MISSING_CTA_URL

    def test_validation_error_multiple_urls_returns_422(self, client: TestClient) -> None:
        """Verifies TC-NEG-03: Multiple CTA links trigger HTTP 422 with ERR_MULTIPLE_CTA_URLS."""
        payload = {"message": "Check https://techdeveloper.io and https://google.com"}
        response = client.post(ApiConstants.ENDPOINT_POSTING, json=payload)

        assert response.status_code == 422
        assert response.headers["Content-Type"] == "application/problem+json"
        data = response.json()
        assert data["code"] == ErrorCodeConstants.ERR_MULTIPLE_CTA_URLS

    def test_validation_error_empty_message_returns_422(self, client: TestClient) -> None:
        """Verifies TC-NEG-04: Whitespace-only message triggers HTTP 422 with ERR_EMPTY_MESSAGE."""
        payload = {"message": "   "}
        response = client.post(ApiConstants.ENDPOINT_POSTING, json=payload)

        assert response.status_code == 422
        data = response.json()
        assert data["code"] == ErrorCodeConstants.ERR_EMPTY_MESSAGE

    def test_validation_error_missing_field_returns_422(self, client: TestClient) -> None:
        """Verifies TC-NEG-08: Missing message field triggers HTTP 422 with ERR_MISSING_FIELD."""
        payload: dict[str, Any] = {}
        response = client.post(ApiConstants.ENDPOINT_POSTING, json=payload)

        assert response.status_code == 422
        data = response.json()
        assert data["code"] == ErrorCodeConstants.ERR_MISSING_FIELD

    def test_validation_error_ssrf_returns_422(self, client: TestClient) -> None:
        """Verifies TC-NEG-10: Loopback URL triggers HTTP 422 with ERR_SSRF_PROHIBITED."""
        payload = {"message": "Test SSRF https://127.0.0.1/admin"}
        response = client.post(ApiConstants.ENDPOINT_POSTING, json=payload)

        assert response.status_code == 422
        data = response.json()
        assert data["code"] == ErrorCodeConstants.ERR_SSRF_PROHIBITED

    def test_validation_error_trojan_source_control_chars_returns_422(
        self, client: TestClient
    ) -> None:
        """Verifies TC-NEG-09: Bidi override characters trigger HTTP 422 with ERR_MALICIOUS_CONTROL_CHARS."""
        payload = {"message": "Test \u202e override https://techdeveloper.io"}
        response = client.post(ApiConstants.ENDPOINT_POSTING, json=payload)

        assert response.status_code == 422
        data = response.json()
        assert data["code"] == ErrorCodeConstants.ERR_MALICIOUS_CONTROL_CHARS

    def test_validation_error_prohibited_port_returns_422(self, client: TestClient) -> None:
        """Verifies TC-NEG-12: Disallowed port triggers HTTP 422 with ERR_PROHIBITED_PORT."""
        payload = {"message": "Test port https://example.com:22/ssh"}
        response = client.post(ApiConstants.ENDPOINT_POSTING, json=payload)

        assert response.status_code == 422
        data = response.json()
        assert data["code"] == ErrorCodeConstants.ERR_PROHIBITED_PORT

    def test_validation_error_invalid_scheme_returns_422(self, client: TestClient) -> None:
        """Verifies TC-NEG-05: Unsupported protocol scheme triggers HTTP 422 with ERR_INVALID_URL_SCHEME."""
        payload = {"message": "Visit ftp://files.techdeveloper.io/doc"}
        response = client.post(ApiConstants.ENDPOINT_POSTING, json=payload)

        assert response.status_code == 422
        data = response.json()
        assert data["code"] == ErrorCodeConstants.ERR_INVALID_URL_SCHEME

    def test_malformed_json_body_returns_400(self, client: TestClient) -> None:
        """Verifies TC-NEG-07: Malformed JSON payload returns HTTP 400 with ERR_MALFORMED_JSON."""
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
        self, client: TestClient, mock_posting_service: AsyncMock
    ) -> None:
        """Verifies TC-EDG-07: ApplicationException raised by service is formatted as RFC 7807 response."""
        mock_posting_service.broadcast.side_effect = InfrastructureException(
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
        self, client: TestClient, mock_posting_service: AsyncMock
    ) -> None:
        """Verifies uncaught runtime exceptions return HTTP 500 with ERR_INTERNAL_SERVER."""
        mock_posting_service.broadcast.side_effect = RuntimeError(
            "Fatal memory corrupt simulation."
        )

        payload = {"message": "Valid broadcast payload! https://techdeveloper.io"}
        response = client.post(ApiConstants.ENDPOINT_POSTING, json=payload)

        assert response.status_code == 500
        assert response.headers["Content-Type"] == "application/problem+json"
        data = response.json()
        assert data["code"] == ErrorCodeConstants.ERR_INTERNAL_SERVER
        assert data["status"] == 500

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("error_msg", "expected_code"),
        [
            (
                "Character count 201 exceeds limit of 200",
                ErrorCodeConstants.ERR_CHAR_LIMIT_EXCEEDED,
            ),
            (
                "Message must contain exactly one valid CTA URL (found 0)",
                ErrorCodeConstants.ERR_MISSING_CTA_URL,
            ),
            ("Message contains multiple URLs (found 2)", ErrorCodeConstants.ERR_MULTIPLE_CTA_URLS),
            (
                "Missing protocol scheme http:// or https://",
                ErrorCodeConstants.ERR_INVALID_URL_SCHEME,
            ),
            ("Message cannot be empty or whitespace", ErrorCodeConstants.ERR_EMPTY_MESSAGE),
            (
                "Contains prohibited bidirectional control characters",
                ErrorCodeConstants.ERR_MALICIOUS_CONTROL_CHARS,
            ),
            ("SSRF to private network blocked", ErrorCodeConstants.ERR_SSRF_PROHIBITED),
            ("Prohibited port 22 blocked", ErrorCodeConstants.ERR_PROHIBITED_PORT),
            ("Unknown generic violation", "ERR_VALIDATION_FAILED"),
        ],
    )
    async def test_validation_exception_handler_error_code_mapping(
        self, app_with_mock_service: FastAPI, error_msg: str, expected_code: str
    ) -> None:
        """Verifies validation_exception_handler maps Pydantic validation errors to exact RFC 7807 codes."""
        handler = app_with_mock_service.exception_handlers[RequestValidationError]
        request = Request(
            scope={"type": "http", "method": "POST", "path": "/posting", "headers": []}
        )
        exc = RequestValidationError(
            [{"loc": ("body", "message"), "msg": error_msg, "type": "value_error"}]
        )
        response = await handler(request, exc)
        assert response.status_code == 422
        assert response.headers["Content-Type"] == "application/problem+json"
        body = json.loads(response.body.decode("utf-8"))
        assert body["code"] == expected_code
