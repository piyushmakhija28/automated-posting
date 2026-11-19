"""Triad unit test suite for Hashnode Publication platform adapter."""

import httpx
import pytest

from app.core.config import Settings
from app.core.constants import PlatformConstants
from app.platforms.hashnode import HashnodeAdapter
from app.platforms.registry import AdapterRegistry


class TestHashnodeAdapterPositive:
    """Positive test scenarios for HashnodeAdapter publication and GraphQL payload formatting."""

    def test_adapter_registration(self) -> None:
        """Verifies HashnodeAdapter is registered under the platform slug 'hashnode'."""
        AdapterRegistry.register_adapter(PlatformConstants.PLATFORM_HASHNODE, HashnodeAdapter)
        adapter_cls = AdapterRegistry.get_adapter_class(PlatformConstants.PLATFORM_HASHNODE)
        assert adapter_cls is HashnodeAdapter

    def test_is_configured_true(self) -> None:
        """Verifies is_configured returns True when both API key and publication ID are set."""
        settings = Settings(
            HASHNODE_API_KEY="hashnode_secret_pat_9988",
            HASHNODE_PUBLICATION_ID="pub_654321",
        )
        adapter = HashnodeAdapter(settings=settings)
        assert adapter.is_configured() is True

    def test_title_synthesis_short_message(self) -> None:
        """Verifies title synthesis preserves short messages without truncation."""
        adapter = HashnodeAdapter()
        title = adapter._synthesize_title("Announcing our developer release")
        assert title == "Announcing our developer release"

    def test_title_synthesis_strips_urls(self) -> None:
        """Verifies title synthesis strips embedded URLs from promotional copy."""
        adapter = HashnodeAdapter()
        title = adapter._synthesize_title(
            "Check out our release https://example.com/blog and give feedback"
        )
        assert "http" not in title
        assert "Check out our release" in title

    def test_title_synthesis_sentence_boundary_period(self) -> None:
        """Verifies title synthesis splits cleanly on first period sentence boundary."""
        adapter = HashnodeAdapter()
        title = adapter._synthesize_title(
            "Major version 2.0 is now live. Read the full changelog here."
        )
        assert title == "Major version 2.0 is now live."

    def test_title_synthesis_sentence_boundary_exclamation(self) -> None:
        """Verifies title synthesis splits cleanly on first exclamation mark."""
        adapter = HashnodeAdapter()
        title = adapter._synthesize_title(
            "Exciting update today! Check out the new dashboard features."
        )
        assert title == "Exciting update today!"

    def test_title_synthesis_sentence_boundary_newline(self) -> None:
        """Verifies title synthesis splits cleanly on newline boundary."""
        adapter = HashnodeAdapter()
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
        adapter = HashnodeAdapter()
        title = adapter._synthesize_title(long_message)
        assert len(title) <= 128
        assert title.endswith("...")
        assert len(title) <= 65

    def test_title_synthesis_long_message_without_spaces(self) -> None:
        """Verifies title synthesis cleanly truncates messages over 60 characters without spaces."""
        long_word_message = "B" * 70
        adapter = HashnodeAdapter()
        title = adapter._synthesize_title(long_word_message)
        assert len(title) <= 128
        assert title.endswith("...")
        assert len(title) == 63

    def test_title_synthesis_fallback_on_blank_or_url_only(self) -> None:
        """Verifies title synthesis returns 'Platform Update' for URL-only or whitespace messages."""
        adapter = HashnodeAdapter()
        assert adapter._synthesize_title("https://example.com/only-url") == "Platform Update"
        assert adapter._synthesize_title("   \n\t  ") == "Platform Update"

    def test_build_payload_structure(self) -> None:
        """Verifies GraphQL mutation payload structure strictly conforms to specification."""
        settings = Settings(
            HASHNODE_API_KEY="key-123",
            HASHNODE_PUBLICATION_ID="pub-abc-456",
        )
        adapter = HashnodeAdapter(settings=settings)
        payload = adapter._build_payload(
            message="Check out our new release!",
            cta_url="https://example.com/release",
        )

        assert "query" in payload
        assert "mutation PublishPost" in payload["query"]
        assert "variables" in payload
        input_vars = payload["variables"]["input"]
        assert input_vars["title"] == "Check out our new release!"
        assert (
            input_vars["contentMarkdown"]
            == "Check out our new release!\n\n[Read More](https://example.com/release)"
        )
        assert input_vars["publicationId"] == "pub-abc-456"
        assert input_vars["tags"] == []

    @pytest.mark.asyncio
    async def test_successful_post_http_200(self) -> None:
        """Verifies successful article creation when Hashnode returns HTTP 200 OK with post data."""
        settings = Settings(
            HASHNODE_API_KEY="valid-pat-key",
            HASHNODE_PUBLICATION_ID="pub-123",
        )

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            assert request.headers["Authorization"] == "valid-pat-key"
            assert request.headers["Content-Type"] == "application/json"
            return httpx.Response(
                status_code=200,
                json={
                    "data": {
                        "publishPost": {
                            "post": {
                                "id": "hn-post-987",
                                "title": "Announcing Platform Update",
                                "url": "https://blog.tech.org/announcing-update-123",
                            }
                        }
                    }
                },
            )

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = HashnodeAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Announcing Platform Update",
                cta_url="https://example.com/update",
            )

            assert result.platform == PlatformConstants.PLATFORM_HASHNODE
            assert result.status == PlatformConstants.STATUS_SUCCESS
            assert result.post_id == "hn-post-987"
            assert result.posted_url == "https://blog.tech.org/announcing-update-123"
            assert result.public_access is True
            assert result.error is None
            assert result.latency_ms is not None
            assert result.latency_ms >= 0.0

    @pytest.mark.asyncio
    async def test_successful_post_http_201(self) -> None:
        """Verifies successful article creation when Hashnode returns HTTP 201 Created."""
        settings = Settings(
            HASHNODE_API_KEY="valid-pat-key",
            HASHNODE_PUBLICATION_ID="pub-123",
        )

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                status_code=201,
                json={
                    "data": {
                        "publishPost": {
                            "post": {
                                "id": 555666,
                                "url": "https://blog.tech.org/post-555666",
                            }
                        }
                    }
                },
            )

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = HashnodeAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Update announcement",
                cta_url="https://example.com/update",
            )

            assert result.status == PlatformConstants.STATUS_SUCCESS
            assert result.post_id == "555666"
            assert result.posted_url == "https://blog.tech.org/post-555666"


class TestHashnodeAdapterNegative:
    """Negative test scenarios for HashnodeAdapter error handling."""

    @pytest.mark.asyncio
    async def test_post_graphql_error_array(self) -> None:
        """Verifies GraphQL error array under HTTP 200 returns failed status with diagnostic."""
        settings = Settings(
            HASHNODE_API_KEY="valid-key",
            HASHNODE_PUBLICATION_ID="invalid-pub-id",
        )

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                status_code=200,
                json={
                    "errors": [
                        {
                            "message": "Publication not found or unauthorized",
                            "locations": [{"line": 1, "column": 45}],
                        }
                    ],
                    "data": None,
                },
            )

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = HashnodeAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Message",
                cta_url="https://example.com",
            )

            assert result.status == PlatformConstants.STATUS_FAILED
            assert result.post_id is None
            assert result.posted_url is None
            assert "Publication not found or unauthorized" in (result.error or "")

    @pytest.mark.asyncio
    async def test_post_graphql_error_array_empty_message_fallback(self) -> None:
        """Verifies GraphQL error array with missing message attribute falls back safely."""
        settings = Settings(
            HASHNODE_API_KEY="valid-key",
            HASHNODE_PUBLICATION_ID="pub-123",
        )

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                status_code=200,
                json={"errors": [{}]},
            )

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = HashnodeAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Message",
                cta_url="https://example.com",
            )

            assert result.status == PlatformConstants.STATUS_FAILED
            assert "Unknown GraphQL error" in (result.error or "")

    @pytest.mark.asyncio
    async def test_post_graphql_error_array_non_dict_fallback(self) -> None:
        """Verifies GraphQL error array containing non-dictionary elements falls back safely."""
        settings = Settings(
            HASHNODE_API_KEY="valid-key",
            HASHNODE_PUBLICATION_ID="pub-123",
        )

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                status_code=200,
                json={"errors": ["Raw string error"]},
            )

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = HashnodeAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Message",
                cta_url="https://example.com",
            )

            assert result.status == PlatformConstants.STATUS_FAILED
            assert "Unknown GraphQL error" in (result.error or "")

    @pytest.mark.asyncio
    async def test_post_http_401_unauthorized(self) -> None:
        """Verifies HTTP 401 returns failed status with authentication diagnostic message."""
        settings = Settings(
            HASHNODE_API_KEY="expired-key",
            HASHNODE_PUBLICATION_ID="pub-123",
        )

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=401, json={"error": "unauthorized"})

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = HashnodeAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Message",
                cta_url="https://example.com",
            )

            assert result.status == PlatformConstants.STATUS_FAILED
            assert result.post_id is None
            assert result.posted_url is None
            assert result.error == "Authentication failed: invalid or expired Hashnode API key."

    @pytest.mark.asyncio
    async def test_post_http_429_rate_limited(self) -> None:
        """Verifies HTTP 429 returns rate limit exceeded failure diagnostic."""
        settings = Settings(
            HASHNODE_API_KEY="valid-key",
            HASHNODE_PUBLICATION_ID="pub-123",
        )

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=429, json={"error": "rate limit"})

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = HashnodeAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Message",
                cta_url="https://example.com",
            )

            assert result.status == PlatformConstants.STATUS_FAILED
            assert result.error == "Rate limit exceeded on Hashnode GraphQL API."

    @pytest.mark.asyncio
    async def test_post_http_500_server_error(self) -> None:
        """Verifies HTTP 500 returns rejection message with status code."""
        settings = Settings(
            HASHNODE_API_KEY="valid-key",
            HASHNODE_PUBLICATION_ID="pub-123",
        )

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=500, text="Internal Server Error")

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = HashnodeAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Message",
                cta_url="https://example.com",
            )

            assert result.status == PlatformConstants.STATUS_FAILED
            assert "HTTP 500" in (result.error or "")

    @pytest.mark.asyncio
    async def test_post_timeout_exception(self) -> None:
        """Verifies socket timeout exception is handled cleanly with diagnostic error."""
        settings = Settings(
            HASHNODE_API_KEY="valid-key",
            HASHNODE_PUBLICATION_ID="pub-123",
        )

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("Socket read timed out")

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = HashnodeAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Message",
                cta_url="https://example.com",
            )

            assert result.status == PlatformConstants.STATUS_FAILED
            assert "timed out" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_post_connect_error(self) -> None:
        """Verifies network connection error is normalized cleanly."""
        settings = Settings(
            HASHNODE_API_KEY="valid-key",
            HASHNODE_PUBLICATION_ID="pub-123",
        )

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Failed to resolve host")

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = HashnodeAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Message",
                cta_url="https://example.com",
            )

            assert result.status == PlatformConstants.STATUS_FAILED
            assert "Network or connection error" in (result.error or "")

    @pytest.mark.asyncio
    async def test_post_unexpected_exception(self) -> None:
        """Verifies unexpected generic exception is caught and normalized."""
        settings = Settings(
            HASHNODE_API_KEY="valid-key",
            HASHNODE_PUBLICATION_ID="pub-123",
        )

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            raise RuntimeError("Unexpected internal crash")

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = HashnodeAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Message",
                cta_url="https://example.com",
            )

            assert result.status == PlatformConstants.STATUS_FAILED
            assert "Internal platform communication error" in (result.error or "")


class TestHashnodeAdapterEdgeCases:
    """Edge-case test scenarios for HashnodeAdapter configurations and payload anomalies."""

    def test_is_configured_false_missing_key(self) -> None:
        """Verifies is_configured returns False when HASHNODE_API_KEY is None or empty."""
        settings_none = Settings(HASHNODE_API_KEY=None, HASHNODE_PUBLICATION_ID="pub-123")
        assert HashnodeAdapter(settings=settings_none).is_configured() is False

        settings_empty = Settings(HASHNODE_API_KEY="   ", HASHNODE_PUBLICATION_ID="pub-123")
        assert HashnodeAdapter(settings=settings_empty).is_configured() is False

    def test_is_configured_false_missing_pub_id(self) -> None:
        """Verifies is_configured returns False when HASHNODE_PUBLICATION_ID is None or empty."""
        settings_none = Settings(HASHNODE_API_KEY="key-123", HASHNODE_PUBLICATION_ID=None)
        assert HashnodeAdapter(settings=settings_none).is_configured() is False

        settings_empty = Settings(HASHNODE_API_KEY="key-123", HASHNODE_PUBLICATION_ID="   ")
        assert HashnodeAdapter(settings=settings_empty).is_configured() is False

    def test_is_configured_false_both_missing(self) -> None:
        """Verifies is_configured returns False when both credentials are None."""
        settings = Settings(HASHNODE_API_KEY=None, HASHNODE_PUBLICATION_ID=None)
        assert HashnodeAdapter(settings=settings).is_configured() is False

    @pytest.mark.asyncio
    async def test_post_unconfigured_skips_without_network_call(self) -> None:
        """Verifies unconfigured adapter returns skipped status with zero network calls."""
        settings = Settings(HASHNODE_API_KEY=None, HASHNODE_PUBLICATION_ID=None)
        network_called = False

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal network_called
            network_called = True
            return httpx.Response(status_code=200)

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = HashnodeAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Skip message",
                cta_url="https://example.com",
            )

            assert network_called is False
            assert result.platform == PlatformConstants.PLATFORM_HASHNODE
            assert result.status == PlatformConstants.STATUS_SKIPPED
            assert result.posted_url is None
            assert result.post_id is None
            assert result.latency_ms == 0.0
            assert "Platform credentials not configured" in (result.error or "")

    @pytest.mark.asyncio
    async def test_post_missing_data_in_graphql_response(self) -> None:
        """Verifies graceful fallback when GraphQL response has no data object."""
        settings = Settings(
            HASHNODE_API_KEY="valid-key",
            HASHNODE_PUBLICATION_ID="pub-123",
        )

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=200, json={})

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = HashnodeAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Message",
                cta_url="https://example.com",
            )

            assert result.status == PlatformConstants.STATUS_SUCCESS
            assert result.post_id == "unknown"
            assert result.posted_url is None

    @pytest.mark.asyncio
    async def test_post_missing_publish_post_in_data(self) -> None:
        """Verifies graceful fallback when data contains no publishPost object."""
        settings = Settings(
            HASHNODE_API_KEY="valid-key",
            HASHNODE_PUBLICATION_ID="pub-123",
        )

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=200, json={"data": {}})

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = HashnodeAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Message",
                cta_url="https://example.com",
            )

            assert result.status == PlatformConstants.STATUS_SUCCESS
            assert result.post_id == "unknown"
            assert result.posted_url is None

    @pytest.mark.asyncio
    async def test_post_missing_post_in_publish_post(self) -> None:
        """Verifies graceful fallback when publishPost contains no post object."""
        settings = Settings(
            HASHNODE_API_KEY="valid-key",
            HASHNODE_PUBLICATION_ID="pub-123",
        )

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                status_code=200,
                json={"data": {"publishPost": {}}},
            )

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = HashnodeAdapter(client=client, settings=settings)
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
        settings = Settings(
            HASHNODE_API_KEY="valid-key",
            HASHNODE_PUBLICATION_ID="pub-123",
        )

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=200, text="Invalid JSON Content")

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = HashnodeAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Message",
                cta_url="https://example.com",
            )

            assert result.status == PlatformConstants.STATUS_SUCCESS
            assert result.post_id == "unknown"
            assert result.posted_url is None

    def test_default_initialization_without_arguments(self) -> None:
        """Verifies HashnodeAdapter defaults when instantiated without parameters."""
        adapter = HashnodeAdapter()
        assert adapter.name == PlatformConstants.PLATFORM_HASHNODE
        assert adapter.client is not None
        assert adapter.settings is not None
