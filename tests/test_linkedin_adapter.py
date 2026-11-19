"""Triad unit test suite for LinkedIn UGC Post platform adapter."""

import logging

import httpx
import pytest

from app.core.config import Settings
from app.core.constants import PlatformConstants
from app.core.logging import SensitiveDataFilter
from app.platforms.linkedin import LinkedInAdapter
from app.platforms.registry import AdapterRegistry


class TestLinkedInAdapterPositive:
    """Positive test scenarios for LinkedInAdapter publication and payload formatting."""

    def test_adapter_registration(self) -> None:
        """Verifies LinkedInAdapter is registered with the platform slug 'linkedin'."""
        AdapterRegistry.register_adapter(PlatformConstants.PLATFORM_LINKEDIN, LinkedInAdapter)
        adapter_cls = AdapterRegistry.get_adapter_class(PlatformConstants.PLATFORM_LINKEDIN)
        assert adapter_cls is LinkedInAdapter

    def test_is_configured_true(self) -> None:
        """Verifies is_configured returns True when token and person URN are set."""
        settings = Settings(
            LINKEDIN_ACCESS_TOKEN="mock-access-token",
            LINKEDIN_PERSON_URN="urn:li:person:12345",
        )
        adapter = LinkedInAdapter(settings=settings)
        assert adapter.is_configured() is True

    def test_format_author_urn_normalization(self) -> None:
        """Verifies person URN normalization handles both prefixed and raw identifiers."""
        settings_raw = Settings(
            LINKEDIN_ACCESS_TOKEN="token",
            LINKEDIN_PERSON_URN="998877",
        )
        adapter_raw = LinkedInAdapter(settings=settings_raw)
        assert adapter_raw._format_author_urn() == "urn:li:person:998877"

        settings_prefixed = Settings(
            LINKEDIN_ACCESS_TOKEN="token",
            LINKEDIN_PERSON_URN="urn:li:person:112233",
        )
        adapter_prefixed = LinkedInAdapter(settings=settings_prefixed)
        assert adapter_prefixed._format_author_urn() == "urn:li:person:112233"

    def test_build_payload_structure(self) -> None:
        """Verifies UGC ShareContent payload structure strictly conforms to specification."""
        settings = Settings(
            LINKEDIN_ACCESS_TOKEN="token",
            LINKEDIN_PERSON_URN="12345",
        )
        adapter = LinkedInAdapter(settings=settings)
        payload = adapter._build_payload(
            message="Check out our new release!",
            cta_url="https://example.com/release",
        )

        assert payload["author"] == "urn:li:person:12345"
        assert payload["lifecycleState"] == "PUBLISHED"
        assert (
            payload["visibility"]["com.linkedin.ugc.MemberNetworkVisibility"]
            == "PUBLIC"
        )

        share_content = payload["specificContent"]["com.linkedin.ugc.ShareContent"]
        assert share_content["shareCommentary"]["text"] == "Check out our new release!"
        assert share_content["shareMediaCategory"] == "ARTICLE"
        assert len(share_content["media"]) == 1
        assert share_content["media"][0]["status"] == "READY"
        assert share_content["media"][0]["originalUrl"] == "https://example.com/release"

    @pytest.mark.asyncio
    async def test_successful_post_with_x_restli_id_header(self) -> None:
        """Verifies successful post extraction when post ID is supplied in X-RestLi-Id header."""
        settings = Settings(
            LINKEDIN_ACCESS_TOKEN="mock-token",
            LINKEDIN_PERSON_URN="person-101",
        )

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            assert request.headers["Authorization"] == "Bearer mock-token"
            assert request.headers["X-Restli-Protocol-Version"] == "2.0.0"
            return httpx.Response(
                status_code=201,
                headers={"X-RestLi-Id": "urn:li:share:7123456789"},
                json={},
            )

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = LinkedInAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Launch announcement",
                cta_url="https://example.com/launch",
            )

            assert result.platform == PlatformConstants.PLATFORM_LINKEDIN
            assert result.status == PlatformConstants.STATUS_SUCCESS
            assert result.post_id == "urn:li:share:7123456789"
            assert (
                result.posted_url
                == "https://www.linkedin.com/feed/update/urn:li:share:7123456789"
            )
            assert result.public_access is True
            assert result.error is None
            assert result.latency_ms is not None
            assert result.latency_ms >= 0.0

    @pytest.mark.asyncio
    async def test_successful_post_with_body_id(self) -> None:
        """Verifies successful post extraction when post ID is supplied in JSON response body."""
        settings = Settings(
            LINKEDIN_ACCESS_TOKEN="mock-token",
            LINKEDIN_PERSON_URN="person-101",
        )

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                status_code=200,
                json={"id": "urn:li:ugcPost:987654321"},
            )

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = LinkedInAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Update post",
                cta_url="https://example.com/update",
            )

            assert result.status == PlatformConstants.STATUS_SUCCESS
            assert result.post_id == "urn:li:ugcPost:987654321"
            assert (
                result.posted_url
                == "https://www.linkedin.com/feed/update/urn:li:ugcPost:987654321"
            )


class TestLinkedInAdapterNegative:
    """Negative test scenarios for LinkedIn upstream error handling."""

    @pytest.mark.parametrize(
        ("status_code", "expected_fragment"),
        [
            (401, "Authentication failed: invalid or expired LinkedIn access token."),
            (403, "Permission denied: insufficient LinkedIn OAuth scopes"),
            (429, "Rate limit exceeded on LinkedIn UGC Posts API."),
            (500, "HTTP 500"),
            (502, "HTTP 502"),
        ],
    )
    @pytest.mark.asyncio
    async def test_http_status_errors(
        self,
        status_code: int,
        expected_fragment: str,
    ) -> None:
        """Verifies HTTP status code errors map to specific diagnostic messages."""
        settings = Settings(
            LINKEDIN_ACCESS_TOKEN="mock-token",
            LINKEDIN_PERSON_URN="person-101",
        )

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=status_code, json={"error": "Failed"})

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = LinkedInAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Test error message",
                cta_url="https://example.com/item",
            )

            assert result.status == PlatformConstants.STATUS_FAILED
            assert result.posted_url is None
            assert result.error is not None
            assert expected_fragment in result.error
            assert result.latency_ms is not None

    @pytest.mark.asyncio
    async def test_timeout_exception(self) -> None:
        """Verifies socket and read timeouts map to sanitized timeout error."""
        settings = Settings(
            LINKEDIN_ACCESS_TOKEN="mock-token",
            LINKEDIN_PERSON_URN="person-101",
        )

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("Read timed out")

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = LinkedInAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Timeout test message",
                cta_url="https://example.com/timeout",
            )

            assert result.status == PlatformConstants.STATUS_FAILED
            assert result.error is not None
            assert "timed out" in result.error.lower()

    @pytest.mark.asyncio
    async def test_network_request_error(self) -> None:
        """Verifies network transport connection failure maps to network error message."""
        settings = Settings(
            LINKEDIN_ACCESS_TOKEN="mock-token",
            LINKEDIN_PERSON_URN="person-101",
        )

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.RequestError("Connection refused by peer")

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = LinkedInAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Network error test message",
                cta_url="https://example.com/network",
            )

            assert result.status == PlatformConstants.STATUS_FAILED
            assert result.error is not None
            assert "Network or connection error" in result.error

    @pytest.mark.asyncio
    async def test_unexpected_runtime_error(self) -> None:
        """Verifies unexpected exceptions map to sanitized internal platform error."""
        settings = Settings(
            LINKEDIN_ACCESS_TOKEN="mock-token",
            LINKEDIN_PERSON_URN="person-101",
        )

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            raise RuntimeError("Unexpected memory failure")

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = LinkedInAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Unexpected error test",
                cta_url="https://example.com/error",
            )

            assert result.status == PlatformConstants.STATUS_FAILED
            assert result.error == "Internal platform communication error."


class TestLinkedInAdapterEdgeCases:
    """Edge-case scenarios: Unconfigured degradation, token scrubbing, and ID fallbacks."""

    @pytest.mark.asyncio
    async def test_unconfigured_skips_without_http_calls(self) -> None:
        """Verifies unconfigured adapter returns status='skipped' without attempting network calls."""
        settings = Settings(
            LINKEDIN_ACCESS_TOKEN=None,
            LINKEDIN_PERSON_URN=None,
        )

        called = False

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(status_code=201)

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = LinkedInAdapter(client=client, settings=settings)
            assert adapter.is_configured() is False

            result = await adapter.post(
                message="Unconfigured post",
                cta_url="https://example.com/skip",
            )

            assert called is False
            assert result.platform == PlatformConstants.PLATFORM_LINKEDIN
            assert result.status == PlatformConstants.STATUS_SKIPPED
            assert result.posted_url is None
            assert result.public_access is False
            assert result.error == "Platform credentials not configured in environment."
            assert result.latency_ms == 0.0

    @pytest.mark.asyncio
    async def test_response_without_id_uses_unknown_fallback(self) -> None:
        """Verifies response lacking X-RestLi-Id header and body ID gracefully falls back to unknown."""
        settings = Settings(
            LINKEDIN_ACCESS_TOKEN="token",
            LINKEDIN_PERSON_URN="person",
        )

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=201, json={"status": "ok"})

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = LinkedInAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Message without id",
                cta_url="https://example.com/fallback",
            )

            assert result.status == PlatformConstants.STATUS_SUCCESS
            assert result.post_id == "unknown"
            assert (
                result.posted_url
                == "https://www.linkedin.com/feed/update/unknown"
            )

    @pytest.mark.asyncio
    async def test_extract_post_id_handles_invalid_json(self) -> None:
        """Verifies invalid JSON response body without X-RestLi-Id header falls back to unknown."""
        settings = Settings(
            LINKEDIN_ACCESS_TOKEN="token",
            LINKEDIN_PERSON_URN="person",
        )

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=200, text="NOT_VALID_JSON_AT_ALL")

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = LinkedInAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Invalid JSON post",
                cta_url="https://example.com/invalid-json",
            )

            assert result.status == PlatformConstants.STATUS_SUCCESS
            assert result.post_id == "unknown"

    def test_token_scrubbing_in_logs(self) -> None:
        """Verifies SensitiveDataFilter masks LinkedIn Bearer tokens in log records."""
        filter_instance = SensitiveDataFilter()
        record = logging.LogRecord(
            name="app.platforms.linkedin",
            level=logging.INFO,
            pathname=__file__,
            lineno=10,
            msg="Sending LinkedIn request with Authorization: Bearer AQV_super_secret_token_12345",
            args=(),
            exc_info=None,
        )
        assert filter_instance.filter(record) is True
        assert "AQV_super_secret_token_12345" not in record.msg
        assert "Bearer [REDACTED]" in record.msg
