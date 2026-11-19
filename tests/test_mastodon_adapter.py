"""Triad unit test suite for Mastodon Status platform adapter."""

import uuid

import httpx
import pytest

from app.core.config import Settings
from app.core.constants import PlatformConstants
from app.platforms.mastodon import MastodonAdapter
from app.platforms.registry import AdapterRegistry


class TestMastodonAdapterPositive:
    """Positive test scenarios for MastodonAdapter publication and payload formatting."""

    def test_adapter_registration(self) -> None:
        """Verifies MastodonAdapter is registered under the platform slug 'mastodon'."""
        AdapterRegistry.register_adapter(PlatformConstants.PLATFORM_MASTODON, MastodonAdapter)
        adapter_cls = AdapterRegistry.get_adapter_class(PlatformConstants.PLATFORM_MASTODON)
        assert adapter_cls is MastodonAdapter

    def test_is_configured_true(self) -> None:
        """Verifies is_configured returns True when MASTODON_ACCESS_TOKEN is non-empty."""
        settings = Settings(MASTODON_ACCESS_TOKEN="mastodon_valid_token_xyz")
        adapter = MastodonAdapter(settings=settings)
        assert adapter.is_configured() is True

    def test_get_endpoint_url_default(self) -> None:
        """Verifies endpoint URL defaults to mastodon.social statuses API."""
        adapter = MastodonAdapter()
        assert adapter._get_endpoint_url() == "https://mastodon.social/api/v1/statuses"

    def test_get_endpoint_url_custom_instance(self) -> None:
        """Verifies custom fediverse instance URL is resolved correctly."""
        settings = Settings(
            MASTODON_ACCESS_TOKEN="token",
            MASTODON_BASE_URL="https://fosstodon.org",
        )
        adapter = MastodonAdapter(settings=settings)
        assert adapter._get_endpoint_url() == "https://fosstodon.org/api/v1/statuses"

    def test_get_endpoint_url_trailing_slash_stripped(self) -> None:
        """Verifies trailing slashes in base URL are cleanly stripped."""
        settings = Settings(
            MASTODON_ACCESS_TOKEN="token",
            MASTODON_BASE_URL="https://hachyderm.io///",
        )
        adapter = MastodonAdapter(settings=settings)
        assert adapter._get_endpoint_url() == "https://hachyderm.io/api/v1/statuses"

    def test_get_endpoint_url_empty_base_fallback(self) -> None:
        """Verifies blank base URL falls back cleanly to mastodon.social."""
        settings = Settings(
            MASTODON_ACCESS_TOKEN="token",
            MASTODON_BASE_URL="   ",
        )
        adapter = MastodonAdapter(settings=settings)
        assert adapter._get_endpoint_url() == "https://mastodon.social/api/v1/statuses"

    def test_build_payload_structure(self) -> None:
        """Verifies status payload structure strictly conforms to specification."""
        adapter = MastodonAdapter()
        payload = adapter._build_payload(
            message="Check out our new release!",
            cta_url="https://example.com/release",
        )

        assert payload["status"] == "Check out our new release!\n\nhttps://example.com/release"
        assert payload["visibility"] == "public"

    @pytest.mark.asyncio
    async def test_successful_post_http_200(self) -> None:
        """Verifies successful status toot when Mastodon returns HTTP 200 OK."""
        settings = Settings(
            MASTODON_ACCESS_TOKEN="valid-user-token",
            MASTODON_BASE_URL="https://mastodon.social",
        )
        observed_idempotency_key = ""

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal observed_idempotency_key
            assert request.headers["Authorization"] == "Bearer valid-user-token"
            assert request.headers["Content-Type"] == "application/json"
            assert "Idempotency-Key" in request.headers
            observed_idempotency_key = request.headers["Idempotency-Key"]
            return httpx.Response(
                status_code=200,
                json={
                    "id": "112345678901234567",
                    "url": "https://mastodon.social/@user/112345678901234567",
                    "content": "<p>Content</p>",
                },
            )

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = MastodonAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Excited to launch our platform",
                cta_url="https://example.com/launch",
            )

            assert result.platform == PlatformConstants.PLATFORM_MASTODON
            assert result.status == PlatformConstants.STATUS_SUCCESS
            assert result.post_id == "112345678901234567"
            assert result.posted_url == "https://mastodon.social/@user/112345678901234567"
            assert result.public_access is True
            assert result.error is None
            assert result.latency_ms is not None
            assert result.latency_ms >= 0.0
            uuid_obj = uuid.UUID(observed_idempotency_key)
            assert uuid_obj.version == 4

    @pytest.mark.asyncio
    async def test_successful_post_http_201(self) -> None:
        """Verifies successful status toot when Mastodon returns HTTP 201 Created."""
        settings = Settings(
            MASTODON_ACCESS_TOKEN="valid-token",
            MASTODON_BASE_URL="https://mastodon.social",
        )

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                status_code=201,
                json={
                    "id": 998877,
                    "url": "https://mastodon.social/@user/998877",
                },
            )

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = MastodonAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Toot announcement",
                cta_url="https://example.com/toot",
            )

            assert result.status == PlatformConstants.STATUS_SUCCESS
            assert result.post_id == "998877"
            assert result.posted_url == "https://mastodon.social/@user/998877"


class TestMastodonAdapterNegative:
    """Negative test scenarios for MastodonAdapter error handling."""

    @pytest.mark.asyncio
    async def test_post_http_401_unauthorized(self) -> None:
        """Verifies HTTP 401 returns failed status with authentication diagnostic message."""
        settings = Settings(MASTODON_ACCESS_TOKEN="expired-token")

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=401, json={"error": "The access token is invalid"})

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = MastodonAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Message",
                cta_url="https://example.com",
            )

            assert result.status == PlatformConstants.STATUS_FAILED
            assert result.post_id is None
            assert result.posted_url is None
            assert result.error == "Authentication failed: invalid or expired Mastodon access token."

    @pytest.mark.asyncio
    async def test_post_http_422_unprocessable_entity(self) -> None:
        """Verifies HTTP 422 returns validation failure diagnostic."""
        settings = Settings(MASTODON_ACCESS_TOKEN="valid-token")

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=422, json={"error": "Validation failed: Text is too long"})

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = MastodonAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Message",
                cta_url="https://example.com",
            )

            assert result.status == PlatformConstants.STATUS_FAILED
            assert "unprocessable status payload" in (result.error or "")

    @pytest.mark.asyncio
    async def test_post_http_429_rate_limited(self) -> None:
        """Verifies HTTP 429 returns 5-minute sliding window rate limit diagnostic."""
        settings = Settings(MASTODON_ACCESS_TOKEN="valid-token")

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=429, json={"error": "Throttled"})

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = MastodonAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Message",
                cta_url="https://example.com",
            )

            assert result.status == PlatformConstants.STATUS_FAILED
            assert "5-minute sliding window" in (result.error or "")

    @pytest.mark.asyncio
    async def test_post_http_500_server_error(self) -> None:
        """Verifies HTTP 500 returns rejection message with status code."""
        settings = Settings(MASTODON_ACCESS_TOKEN="valid-token")

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=500, text="Internal Server Error")

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = MastodonAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Message",
                cta_url="https://example.com",
            )

            assert result.status == PlatformConstants.STATUS_FAILED
            assert "HTTP 500" in (result.error or "")

    @pytest.mark.asyncio
    async def test_post_timeout_exception(self) -> None:
        """Verifies socket timeout exception is handled cleanly with diagnostic error."""
        settings = Settings(MASTODON_ACCESS_TOKEN="valid-token")

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("Socket read timed out")

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = MastodonAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Message",
                cta_url="https://example.com",
            )

            assert result.status == PlatformConstants.STATUS_FAILED
            assert "timed out" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_post_connect_error(self) -> None:
        """Verifies network connection error is normalized cleanly."""
        settings = Settings(MASTODON_ACCESS_TOKEN="valid-token")

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Failed to resolve host")

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = MastodonAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Message",
                cta_url="https://example.com",
            )

            assert result.status == PlatformConstants.STATUS_FAILED
            assert "Network or connection error" in (result.error or "")

    @pytest.mark.asyncio
    async def test_post_unexpected_exception(self) -> None:
        """Verifies unexpected generic exception is caught and normalized."""
        settings = Settings(MASTODON_ACCESS_TOKEN="valid-token")

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            raise RuntimeError("Unexpected internal crash")

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = MastodonAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Message",
                cta_url="https://example.com",
            )

            assert result.status == PlatformConstants.STATUS_FAILED
            assert "Internal platform communication error" in (result.error or "")


class TestMastodonAdapterEdgeCases:
    """Edge-case test scenarios for MastodonAdapter configurations and payload anomalies."""

    def test_is_configured_false_none(self) -> None:
        """Verifies is_configured returns False when MASTODON_ACCESS_TOKEN is None."""
        settings = Settings(MASTODON_ACCESS_TOKEN=None)
        adapter = MastodonAdapter(settings=settings)
        assert adapter.is_configured() is False

    def test_is_configured_false_blank(self) -> None:
        """Verifies is_configured returns False when MASTODON_ACCESS_TOKEN contains only whitespace."""
        settings = Settings(MASTODON_ACCESS_TOKEN="   ")
        adapter = MastodonAdapter(settings=settings)
        assert adapter.is_configured() is False

    @pytest.mark.asyncio
    async def test_post_unconfigured_skips_without_network_call(self) -> None:
        """Verifies unconfigured adapter returns skipped status with zero network calls."""
        settings = Settings(MASTODON_ACCESS_TOKEN=None)
        network_called = False

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal network_called
            network_called = True
            return httpx.Response(status_code=200)

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = MastodonAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Skip message",
                cta_url="https://example.com",
            )

            assert network_called is False
            assert result.platform == PlatformConstants.PLATFORM_MASTODON
            assert result.status == PlatformConstants.STATUS_SKIPPED
            assert result.posted_url is None
            assert result.post_id is None
            assert result.latency_ms == 0.0
            assert "Platform credentials not configured" in (result.error or "")

    @pytest.mark.asyncio
    async def test_post_missing_id_and_url_in_success_response(self) -> None:
        """Verifies graceful fallback when response body has no id or url attributes."""
        settings = Settings(MASTODON_ACCESS_TOKEN="valid-token")

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=200, json={})

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = MastodonAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Message",
                cta_url="https://example.com",
            )

            assert result.status == PlatformConstants.STATUS_SUCCESS
            assert result.post_id == "unknown"
            assert result.posted_url is None

    @pytest.mark.asyncio
    async def test_post_malformed_json_in_success_response(self) -> None:
        """Verifies graceful fallback when response body is unparseable JSON."""
        settings = Settings(MASTODON_ACCESS_TOKEN="valid-token")

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=200, text="Invalid JSON Content")

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = MastodonAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Message",
                cta_url="https://example.com",
            )

            assert result.status == PlatformConstants.STATUS_SUCCESS
            assert result.post_id == "unknown"
            assert result.posted_url is None

    def test_default_initialization_without_arguments(self) -> None:
        """Verifies MastodonAdapter defaults when instantiated without parameters."""
        adapter = MastodonAdapter()
        assert adapter.name == PlatformConstants.PLATFORM_MASTODON
        assert adapter.client is not None
        assert adapter.settings is not None
