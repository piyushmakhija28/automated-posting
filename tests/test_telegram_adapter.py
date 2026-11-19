"""Triad unit test suite for Telegram Channel Bot platform adapter."""

import httpx
import pytest

from app.core.config import Settings
from app.core.constants import PlatformConstants
from app.platforms.registry import AdapterRegistry
from app.platforms.telegram import TelegramAdapter


class TestTelegramAdapterPositive:
    """Positive test scenarios for TelegramAdapter message dispatch and URL resolution."""

    def test_adapter_registration(self) -> None:
        """Verifies TelegramAdapter is registered under the platform slug 'telegram'."""
        AdapterRegistry.register_adapter(PlatformConstants.PLATFORM_TELEGRAM, TelegramAdapter)
        adapter_cls = AdapterRegistry.get_adapter_class(PlatformConstants.PLATFORM_TELEGRAM)
        assert adapter_cls is TelegramAdapter

    def test_is_configured_true(self) -> None:
        """Verifies is_configured returns True when bot token and channel ID are set."""
        settings = Settings(
            TELEGRAM_BOT_TOKEN="bot123456789:ABCdefGHIjklMNOpqrSTUvwxYZ_01234",
            TELEGRAM_CHANNEL_ID="@tech_announcements",
        )
        adapter = TelegramAdapter(settings=settings)
        assert adapter.is_configured() is True

    def test_escape_html_replaces_entities(self) -> None:
        """Verifies HTML special characters are escaped into safe entity references."""
        adapter = TelegramAdapter()
        raw_text = "Check <new> feature & get 100% > results"
        escaped = adapter._escape_html(raw_text)
        assert "<" not in escaped
        assert ">" not in escaped
        assert "&amp;" in escaped
        assert "&lt;new&gt;" in escaped

    def test_build_payload_structure(self) -> None:
        """Verifies sendMessage payload structure strictly conforms to specification."""
        settings = Settings(
            TELEGRAM_BOT_TOKEN="bot123:token",
            TELEGRAM_CHANNEL_ID="@my_channel",
        )
        adapter = TelegramAdapter(settings=settings)
        payload = adapter._build_payload(
            message="Check out our <new> release & platform!",
            cta_url="https://example.com/release",
        )

        assert payload["chat_id"] == "@my_channel"
        assert payload["parse_mode"] == "HTML"
        assert payload["disable_web_page_preview"] is False
        assert "&lt;new&gt;" in payload["text"]
        assert "&amp;" in payload["text"]
        assert '<a href="https://example.com/release">Read More</a>' in payload["text"]

    def test_resolve_public_url_from_chat_username(self) -> None:
        """Verifies canonical URL synthesis from chat username metadata."""
        adapter = TelegramAdapter()
        chat_meta = {"username": "public_broadcasts"}
        url = adapter._resolve_public_url(chat_meta, message_id=5432)
        assert url == "https://t.me/public_broadcasts/5432"

    def test_resolve_public_url_from_at_channel_handle(self) -> None:
        """Verifies canonical URL synthesis from settings channel handle fallback."""
        settings = Settings(
            TELEGRAM_BOT_TOKEN="token",
            TELEGRAM_CHANNEL_ID="@official_channel",
        )
        adapter = TelegramAdapter(settings=settings)
        url = adapter._resolve_public_url({}, message_id="7788")
        assert url == "https://t.me/official_channel/7788"

    def test_resolve_public_url_private_channel_none(self) -> None:
        """Verifies private channels with numeric IDs return None for public URL."""
        settings = Settings(
            TELEGRAM_BOT_TOKEN="token",
            TELEGRAM_CHANNEL_ID="-1009876543210",
        )
        adapter = TelegramAdapter(settings=settings)
        url = adapter._resolve_public_url({}, message_id=99)
        assert url is None

    @pytest.mark.asyncio
    async def test_successful_post_with_public_channel(self) -> None:
        """Verifies successful message dispatch to public channel returning public URL."""
        settings = Settings(
            TELEGRAM_BOT_TOKEN="bot998877665:TokenSecretKeyStringXYZ_12345",
            TELEGRAM_CHANNEL_ID="@my_announcements",
        )

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            assert "bot998877665:TokenSecretKeyStringXYZ_12345" in str(request.url)
            return httpx.Response(
                status_code=200,
                json={
                    "ok": True,
                    "result": {
                        "message_id": 142,
                        "chat": {
                            "id": -1001234567890,
                            "title": "Announcements",
                            "username": "my_announcements",
                            "type": "channel",
                        },
                        "date": 1700300000,
                        "text": "Broadcast text",
                    },
                },
            )

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = TelegramAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Excited to launch our platform",
                cta_url="https://example.com/launch",
            )

            assert result.platform == PlatformConstants.PLATFORM_TELEGRAM
            assert result.status == PlatformConstants.STATUS_SUCCESS
            assert result.post_id == "142"
            assert result.posted_url == "https://t.me/my_announcements/142"
            assert result.public_access is True
            assert result.error is None
            assert result.latency_ms is not None
            assert result.latency_ms >= 0.0

    @pytest.mark.asyncio
    async def test_successful_post_with_private_channel(self) -> None:
        """Verifies successful message dispatch to private channel sets public_access=False."""
        settings = Settings(
            TELEGRAM_BOT_TOKEN="bot112233445:TokenSecretKeyStringXYZ_12345",
            TELEGRAM_CHANNEL_ID="-1001234567890",
        )

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                status_code=200,
                json={
                    "ok": True,
                    "result": {
                        "message_id": 303,
                        "chat": {
                            "id": -1001234567890,
                            "title": "Private Channel",
                            "type": "channel",
                        },
                    },
                },
            )

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = TelegramAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Internal update",
                cta_url="https://example.com/update",
            )

            assert result.status == PlatformConstants.STATUS_SUCCESS
            assert result.post_id == "303"
            assert result.posted_url is None
            assert result.public_access is False


class TestTelegramAdapterNegative:
    """Negative test scenarios for TelegramAdapter error handling."""

    @pytest.mark.asyncio
    async def test_post_http_200_with_ok_false(self) -> None:
        """Verifies HTTP 200 with ok=false returns failure result with description."""
        settings = Settings(
            TELEGRAM_BOT_TOKEN="bot123456789:TokenSecretKeyStringXYZ_12345",
            TELEGRAM_CHANNEL_ID="@channel",
        )

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                status_code=200,
                json={"ok": False, "description": "Too Many Requests: retry after 60"},
            )

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = TelegramAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Message",
                cta_url="https://example.com",
            )

            assert result.status == PlatformConstants.STATUS_FAILED
            assert "Too Many Requests" in (result.error or "")

    @pytest.mark.asyncio
    async def test_post_http_400_bad_request_chat_not_found(self) -> None:
        """Verifies HTTP 400 maps to chat not found diagnostic message."""
        settings = Settings(
            TELEGRAM_BOT_TOKEN="bot123456789:TokenSecretKeyStringXYZ_12345",
            TELEGRAM_CHANNEL_ID="@non_existent_channel_xyz",
        )

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                status_code=400,
                json={"ok": False, "description": "Bad Request: chat not found"},
            )

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = TelegramAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Message",
                cta_url="https://example.com",
            )

            assert result.status == PlatformConstants.STATUS_FAILED
            assert "chat not found" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_post_http_403_bot_not_administrator(self) -> None:
        """Verifies HTTP 403 maps to missing administrator permissions diagnostic."""
        settings = Settings(
            TELEGRAM_BOT_TOKEN="bot123456789:TokenSecretKeyStringXYZ_12345",
            TELEGRAM_CHANNEL_ID="@channel",
        )

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                status_code=403,
                json={
                    "ok": False,
                    "description": "Forbidden: bot is not an administrator of the channel",
                },
            )

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = TelegramAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Message",
                cta_url="https://example.com",
            )

            assert result.status == PlatformConstants.STATUS_FAILED
            assert "not an administrator" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_post_http_429_rate_limited(self) -> None:
        """Verifies HTTP 429 returns rate limit exceeded diagnostic."""
        settings = Settings(
            TELEGRAM_BOT_TOKEN="bot123456789:TokenSecretKeyStringXYZ_12345",
            TELEGRAM_CHANNEL_ID="@channel",
        )

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=429, json={"ok": False})

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = TelegramAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Message",
                cta_url="https://example.com",
            )

            assert result.status == PlatformConstants.STATUS_FAILED
            assert "Rate limit exceeded" in (result.error or "")

    @pytest.mark.asyncio
    async def test_post_http_500_server_error(self) -> None:
        """Verifies HTTP 500 returns generic rejection message with status code."""
        settings = Settings(
            TELEGRAM_BOT_TOKEN="bot123456789:TokenSecretKeyStringXYZ_12345",
            TELEGRAM_CHANNEL_ID="@channel",
        )

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=500, text="Internal Server Error")

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = TelegramAdapter(client=client, settings=settings)
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
            TELEGRAM_BOT_TOKEN="bot123456789:TokenSecretKeyStringXYZ_12345",
            TELEGRAM_CHANNEL_ID="@channel",
        )

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("Socket read timed out")

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = TelegramAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Message",
                cta_url="https://example.com",
            )

            assert result.status == PlatformConstants.STATUS_FAILED
            assert "timed out" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_post_connect_error(self) -> None:
        """Verifies network connection error is normalized cleanly with token masked."""
        settings = Settings(
            TELEGRAM_BOT_TOKEN="bot123456789:SecretTokenForTestingMasking000",
            TELEGRAM_CHANNEL_ID="@channel",
        )

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Failed to connect to host")

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = TelegramAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Message",
                cta_url="https://example.com",
            )

            assert result.status == PlatformConstants.STATUS_FAILED
            assert "SecretTokenForTestingMasking000" not in (result.error or "")
            assert "Network or connection error" in (result.error or "")

    @pytest.mark.asyncio
    async def test_post_unexpected_exception(self) -> None:
        """Verifies unexpected generic exception is caught and normalized."""
        settings = Settings(
            TELEGRAM_BOT_TOKEN="bot123456789:TokenSecretKeyStringXYZ_12345",
            TELEGRAM_CHANNEL_ID="@channel",
        )

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            raise RuntimeError("Unexpected internal crash")

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = TelegramAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Message",
                cta_url="https://example.com",
            )

            assert result.status == PlatformConstants.STATUS_FAILED
            assert "Internal platform communication error" in (result.error or "")


class TestTelegramAdapterEdgeCases:
    """Edge-case test scenarios for TelegramAdapter configurations and payload anomalies."""

    def test_is_configured_false_missing_token(self) -> None:
        """Verifies is_configured returns False when TELEGRAM_BOT_TOKEN is None or empty."""
        settings_none = Settings(TELEGRAM_BOT_TOKEN=None, TELEGRAM_CHANNEL_ID="@channel")
        assert TelegramAdapter(settings=settings_none).is_configured() is False

        settings_empty = Settings(TELEGRAM_BOT_TOKEN="   ", TELEGRAM_CHANNEL_ID="@channel")
        assert TelegramAdapter(settings=settings_empty).is_configured() is False

    def test_is_configured_false_missing_channel(self) -> None:
        """Verifies is_configured returns False when TELEGRAM_CHANNEL_ID is None or empty."""
        settings_none = Settings(TELEGRAM_BOT_TOKEN="bot123:token", TELEGRAM_CHANNEL_ID=None)
        assert TelegramAdapter(settings=settings_none).is_configured() is False

        settings_empty = Settings(TELEGRAM_BOT_TOKEN="bot123:token", TELEGRAM_CHANNEL_ID="   ")
        assert TelegramAdapter(settings=settings_empty).is_configured() is False

    def test_sanitize_token_helper(self) -> None:
        """Verifies bot secret token is sanitized to bot[REDACTED]."""
        adapter = TelegramAdapter()
        raw = "Error on https://api.telegram.org/bot123456789:ABCdefGHIjklMNOpqrSTUvwxYZ_012/sendMessage"
        sanitized = adapter._sanitize_token(raw)
        assert "ABCdefGHIjkl" not in sanitized
        assert "bot[REDACTED]" in sanitized

    @pytest.mark.asyncio
    async def test_post_unconfigured_skips_without_network_call(self) -> None:
        """Verifies unconfigured adapter returns skipped status with zero network calls."""
        settings = Settings(TELEGRAM_BOT_TOKEN=None, TELEGRAM_CHANNEL_ID=None)
        network_called = False

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal network_called
            network_called = True
            return httpx.Response(status_code=200)

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = TelegramAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Skip message",
                cta_url="https://example.com",
            )

            assert network_called is False
            assert result.platform == PlatformConstants.PLATFORM_TELEGRAM
            assert result.status == PlatformConstants.STATUS_SKIPPED
            assert result.posted_url is None
            assert result.post_id is None
            assert result.latency_ms == 0.0
            assert "Platform credentials not configured" in (result.error or "")

    @pytest.mark.asyncio
    async def test_post_missing_message_id_in_result(self) -> None:
        """Verifies graceful fallback when result contains no message_id attribute."""
        settings = Settings(
            TELEGRAM_BOT_TOKEN="bot123456789:TokenSecretKeyStringXYZ_12345",
            TELEGRAM_CHANNEL_ID="@channel",
        )

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=200, json={"ok": True, "result": {}})

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = TelegramAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Message",
                cta_url="https://example.com",
            )

            assert result.status == PlatformConstants.STATUS_SUCCESS
            assert result.post_id == "unknown"

    @pytest.mark.asyncio
    async def test_post_malformed_json_response(self) -> None:
        """Verifies graceful fallback when response body is unparseable JSON."""
        settings = Settings(
            TELEGRAM_BOT_TOKEN="bot123456789:TokenSecretKeyStringXYZ_12345",
            TELEGRAM_CHANNEL_ID="@channel",
        )

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=200, text="Not JSON Content")

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = TelegramAdapter(client=client, settings=settings)
            result = await adapter.post(
                message="Message",
                cta_url="https://example.com",
            )

            assert result.status == PlatformConstants.STATUS_FAILED
            assert "Telegram API error" in (result.error or "")

    def test_default_initialization_without_arguments(self) -> None:
        """Verifies TelegramAdapter defaults when instantiated without parameters."""
        adapter = TelegramAdapter()
        assert adapter.name == PlatformConstants.PLATFORM_TELEGRAM
        assert adapter.client is not None
        assert adapter.settings is not None
