"""Triad unit test suite for Dev.to Article platform adapter."""

import httpx
import pytest

from app.core.config import Settings
from app.core.constants import PlatformConstants
from app.platforms.devto import DevToAdapter
from app.platforms.registry import AdapterRegistry


class TestDevToAdapterPositive:
    """Positive test scenarios for DevToAdapter publication and title synthesis."""

    def test_adapter_registration(self) -> None:
        """Verifies DevToAdapter is registered under the platform slug 'devto'."""
        AdapterRegistry.register_adapter(PlatformConstants.PLATFORM_DEVTO, DevToAdapter)
        adapter_cls = AdapterRegistry.get_adapter_class(PlatformConstants.PLATFORM_DEVTO)
        assert adapter_cls is DevToAdapter

    def test_is_configured_true(self) -> None:
        """Verifies is_configured returns True when DEVTO_API_KEY is non-blank."""
        settings = Settings(DEVTO_API_KEY="devto_live_secret_key_123")
        adapter = DevToAdapter(settings=settings)
        assert adapter.is_configured() is True

    def test_title_synthesis_short_message(self) -> None:
        """Verifies title synthesis preserves short messages without truncation."""
        adapter = DevToAdapter()
        title = adapter._synthesize_title("Announcing our new open-source platform")
        assert title == "Announcing our new open-source platform"

    def test_title_synthesis_strips_urls(self) -> None:
        """Verifies title synthesis strips embedded URLs from promotional copy."""
        adapter = DevToAdapter()
        title = adapter._synthesize_title(
            "Check out our release https://example.com/blog and give feedback"
        )
        assert "http" not in title
        assert (
            "Check out our release  and give feedback" in title or "Check out our release" in title
        )

    def test_title_synthesis_sentence_boundary_period(self) -> None:
        """Verifies title synthesis splits cleanly on first period sentence boundary."""
        adapter = DevToAdapter()
        title = adapter._synthesize_title(
            "Major version 2.0 is now live. Read the full changelog here."
        )
        assert title == "Major version 2.0 is now live."

    def test_title_synthesis_sentence_boundary_exclamation(self) -> None:
        """Verifies title synthesis splits cleanly on first exclamation mark."""
        adapter = DevToAdapter()
        title = adapter._synthesize_title(
            "Exciting update today! Check out the new dashboard features."
        )
        assert title == "Exciting update today!"

    def test_title_synthesis_sentence_boundary_newline(self) -> None:
        """Verifies title synthesis splits cleanly on newline boundary."""
        adapter = DevToAdapter()
        title = adapter._synthesize_title(
            "Header announcement line\nDetails and instructions follow below."
        )
        assert title == "Header announcement line"

    def test_title_synthesis_long_message_truncation(self) -> None:
        """Verifies title synthesis cleanly truncates messages over 60 characters with ellipsis."""
        long_message = (
            "We are thrilled to present our groundbreaking automated posting engine "
            "designed specifically for high velocity content syndication across platforms."
        )
        adapter = DevToAdapter()
        title = adapter._synthesize_title(long_message)
        assert len(title) <= 128
        assert title.endswith("...")
        assert len(title) <= 65

    def test_title_synthesis_long_message_without_spaces(self) -> None:
        """Verifies title synthesis cleanly truncates messages over 60 characters without spaces."""
        long_word_message = "A" * 70
        adapter = DevToAdapter()
        title = adapter._synthesize_title(long_word_message)
        assert len(title) <= 128
        assert title.endswith("...")
        assert len(title) == 63

    def test_title_synthesis_fallback_on_blank_or_url_only(self) -> None:
        """Verifies title synthesis returns 'Platform Update' for URL-only or whitespace messages."""
        adapter = DevToAdapter()
        assert adapter._synthesize_title("https://example.com/only-url") == "Platform Update"
        assert adapter._synthesize_title("   \n\t  ") == "Platform Update"

    def test_build_payload_structure(self) -> None:
        """Verifies Forem article payload structure strictly conforms to specification."""
        adapter = DevToAdapter()
        payload = adapter._build_payload(
            message="Check out our new release!",
            cta_url="https://example.com/release",
        )

        assert "article" in payload
        article = payload["article"]
        assert article["title"] == "Check out our new release!"
        assert (
            article["body_markdown"]
            == "Check out our new release!\n\n[Read More](https://example.com/release)"
        )
        assert article["published"] is True
        assert article["tags"] == ["tech", "updates", "announcement"]

    @pytest.mark.asyncio
    async def test_successful_post_http_201(self) -> None:
        """Verifies successful article creation when Dev.to returns HTTP 201 Created."""
        settings = Settings(DEVTO_API_KEY="valid-devto-key")

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            assert request.headers["api-key"] == "valid-devto-key"
            assert request.headers["Content-Type"] == "application/json"
            return httpx.Response(
                status_code=201,
                json={
                    "id": 987654,
                    "url": "https://dev.to/user/announcing-platform-update-abc",
                },
            )

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = DevToAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Announcing platform update",
                cta_url="https://example.com/update",
            )

            assert result.platform == PlatformConstants.PLATFORM_DEVTO
            assert result.status == PlatformConstants.STATUS_SUCCESS
            assert result.post_id == "987654"
            assert result.posted_url == "https://dev.to/user/announcing-platform-update-abc"
            assert result.public_access is True
            assert result.error is None
            assert result.latency_ms is not None
            assert result.latency_ms >= 0.0

    @pytest.mark.asyncio
    async def test_successful_post_http_200(self) -> None:
        """Verifies successful article creation when Dev.to returns HTTP 200 OK."""
        settings = Settings(DEVTO_API_KEY="valid-devto-key")

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                status_code=200,
                json={"id": "devto-101", "url": "https://dev.to/article/101"},
            )

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = DevToAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Article update",
                cta_url="https://example.com/article",
            )

            assert result.status == PlatformConstants.STATUS_SUCCESS
            assert result.post_id == "devto-101"
            assert result.posted_url == "https://dev.to/article/101"


class TestDevToAdapterNegative:
    """Negative test scenarios for DevToAdapter error handling."""

    @pytest.mark.asyncio
    async def test_post_http_401_unauthorized(self) -> None:
        """Verifies HTTP 401 returns failed status with authentication diagnostic message."""
        settings = Settings(DEVTO_API_KEY="expired-key")

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=401, json={"error": "unauthorized"})

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = DevToAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Message",
                cta_url="https://example.com",
            )

            assert result.status == PlatformConstants.STATUS_FAILED
            assert result.post_id is None
            assert result.posted_url is None
            assert result.error == "Authentication failed: invalid or missing Dev.to API key."

    @pytest.mark.asyncio
    async def test_post_http_422_validation_error_with_detail(self) -> None:
        """Verifies HTTP 422 extracts and formats Forem engine validation error detail."""
        settings = Settings(DEVTO_API_KEY="valid-key")

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                status_code=422,
                json={"error": "Title has already been taken"},
            )

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = DevToAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Duplicate Title",
                cta_url="https://example.com",
            )

            assert result.status == PlatformConstants.STATUS_FAILED
            assert "Title has already been taken" in (result.error or "")

    @pytest.mark.asyncio
    async def test_post_http_422_unparseable_json(self) -> None:
        """Verifies HTTP 422 with unparseable body uses default validation error message."""
        settings = Settings(DEVTO_API_KEY="valid-key")

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=422, text="Unprocessable Entity")

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = DevToAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Message",
                cta_url="https://example.com",
            )

            assert result.status == PlatformConstants.STATUS_FAILED
            assert "article rejected by Forem engine" in (result.error or "")

    @pytest.mark.asyncio
    async def test_post_http_429_rate_limited(self) -> None:
        """Verifies HTTP 429 returns rate limit exceeded failure diagnostic."""
        settings = Settings(DEVTO_API_KEY="valid-key")

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=429, json={"error": "rate limit"})

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = DevToAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Message",
                cta_url="https://example.com",
            )

            assert result.status == PlatformConstants.STATUS_FAILED
            assert result.error == "Rate limit exceeded on Dev.to API."

    @pytest.mark.asyncio
    async def test_post_http_500_server_error(self) -> None:
        """Verifies HTTP 500 returns generic rejection message with status code."""
        settings = Settings(DEVTO_API_KEY="valid-key")

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=500, text="Internal Server Error")

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = DevToAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Message",
                cta_url="https://example.com",
            )

            assert result.status == PlatformConstants.STATUS_FAILED
            assert "HTTP 500" in (result.error or "")

    @pytest.mark.asyncio
    async def test_post_timeout_exception(self) -> None:
        """Verifies socket timeout exception is handled cleanly with diagnostic error."""
        settings = Settings(DEVTO_API_KEY="valid-key")

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("Socket read timed out")

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = DevToAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Message",
                cta_url="https://example.com",
            )

            assert result.status == PlatformConstants.STATUS_FAILED
            assert "timed out" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_post_connect_error(self) -> None:
        """Verifies network connection error is normalized cleanly."""
        settings = Settings(DEVTO_API_KEY="valid-key")

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Failed to resolve host")

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = DevToAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Message",
                cta_url="https://example.com",
            )

            assert result.status == PlatformConstants.STATUS_FAILED
            assert "Network or connection error" in (result.error or "")

    @pytest.mark.asyncio
    async def test_post_unexpected_exception(self) -> None:
        """Verifies unexpected generic exception is caught and normalized."""
        settings = Settings(DEVTO_API_KEY="valid-key")

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            raise RuntimeError("Unexpected internal crash")

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = DevToAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Message",
                cta_url="https://example.com",
            )

            assert result.status == PlatformConstants.STATUS_FAILED
            assert "Internal platform communication error" in (result.error or "")


class TestDevToAdapterEdgeCases:
    """Edge-case test scenarios for DevToAdapter configurations and payload anomalies."""

    def test_is_configured_false_none(self) -> None:
        """Verifies is_configured returns False when DEVTO_API_KEY is None."""
        settings = Settings(DEVTO_API_KEY=None)
        adapter = DevToAdapter(settings=settings)
        assert adapter.is_configured() is False

    def test_is_configured_false_blank(self) -> None:
        """Verifies is_configured returns False when DEVTO_API_KEY contains only whitespace."""
        settings = Settings(DEVTO_API_KEY="   ")
        adapter = DevToAdapter(settings=settings)
        assert adapter.is_configured() is False

    @pytest.mark.asyncio
    async def test_post_unconfigured_skips_without_network_call(self) -> None:
        """Verifies AC-3: unconfigured adapter returns skipped status with zero network calls."""
        settings = Settings(DEVTO_API_KEY=None)
        network_called = False

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal network_called
            network_called = True
            return httpx.Response(status_code=200)

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = DevToAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Skip message",
                cta_url="https://example.com",
            )

            assert network_called is False
            assert result.platform == PlatformConstants.PLATFORM_DEVTO
            assert result.status == PlatformConstants.STATUS_SKIPPED
            assert result.posted_url is None
            assert result.post_id is None
            assert result.latency_ms == 0.0
            assert "Platform credentials not configured" in (result.error or "")

    @pytest.mark.asyncio
    async def test_post_missing_id_and_url_in_success_response(self) -> None:
        """Verifies graceful fallback when Dev.to returns HTTP 201 without id or url attributes."""
        settings = Settings(DEVTO_API_KEY="valid-key")

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=201, json={})

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = DevToAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Message",
                cta_url="https://example.com",
            )

            assert result.status == PlatformConstants.STATUS_SUCCESS
            assert result.post_id == "unknown"
            assert result.posted_url is None

    @pytest.mark.asyncio
    async def test_post_malformed_json_in_success_response(self) -> None:
        """Verifies graceful fallback when Dev.to returns HTTP 201 with non-JSON body."""
        settings = Settings(DEVTO_API_KEY="valid-key")

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=201, text="Not JSON")

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = DevToAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Message",
                cta_url="https://example.com",
            )

            assert result.status == PlatformConstants.STATUS_SUCCESS
            assert result.post_id == "unknown"
            assert result.posted_url is None

    def test_default_initialization_without_arguments(self) -> None:
        """Verifies DevToAdapter defaults when instantiated without parameters."""
        adapter = DevToAdapter()
        assert adapter.name == PlatformConstants.PLATFORM_DEVTO
        assert adapter.client is not None
        assert adapter.settings is not None
