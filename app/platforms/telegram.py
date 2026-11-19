"""Telegram Channel Bot platform adapter communicating via Telegram Bot API sendMessage.

Publishes broadcast messages and Call-to-Action destination links formatted in HTML
to public or private Telegram channels using official Telegram Bot API webhooks.
"""

import html
import re
from time import perf_counter
from typing import Any

import httpx

from app.core.config import Settings
from app.core.constants import PlatformConstants
from app.models.dtos.platform_dto import PlatformResultDto
from app.platforms.base import BasePlatformAdapter
from app.platforms.registry import AdapterRegistry


@AdapterRegistry.register(PlatformConstants.PLATFORM_TELEGRAM)
class TelegramAdapter(BasePlatformAdapter):
    """Platform adapter for Telegram Bot API sendMessage endpoint."""

    def __init__(
        self,
        name: str = PlatformConstants.PLATFORM_TELEGRAM,
        client: httpx.AsyncClient | None = None,
        settings: Settings | None = None,
    ) -> None:
        """Initializes the Telegram adapter with HTTP client and runtime settings.

        Args:
            name: Canonical platform slug identifier (defaults to 'telegram').
            client: Shared asynchronous HTTPX client; falls back to an isolated client.
            settings: Optional runtime settings instance; defaults to fresh Settings.
        """
        active_client = client or httpx.AsyncClient(
            timeout=PlatformConstants.DEFAULT_ADAPTER_TIMEOUT_SECONDS
        )
        super().__init__(name=name, client=active_client, settings=settings)

    def is_configured(self) -> bool:
        """Verifies presence of mandatory Telegram Bot token and target channel ID.

        Returns:
            True if both bot token and channel ID are populated; False otherwise.
        """
        token = self.settings.telegram_bot_token
        channel_id = self.settings.telegram_channel_id
        return bool(token and token.strip() and channel_id and channel_id.strip())

    def _escape_html(self, text: str) -> str:
        """Safely escapes HTML special entities to prevent Telegram parse mode errors.

        Args:
            text: Raw message text copy.

        Returns:
            Sanitized text with '<', '>', and '&' escaped as character entities.
        """
        return html.escape(text, quote=False)

    def _build_payload(self, message: str, cta_url: str) -> dict[str, Any]:
        """Constructs the Telegram sendMessage JSON request payload.

        Args:
            message: Raw message text to be escaped and sent.
            cta_url: Validated Call-to-Action destination link.

        Returns:
            Dictionary matching the Telegram Bot API sendMessage schema.
        """
        escaped_message = self._escape_html(message.strip())
        formatted_text = f'{escaped_message}\n\n<a href="{cta_url.strip()}">Read More</a>'
        channel_id = (self.settings.telegram_channel_id or "").strip()
        return {
            "chat_id": channel_id,
            "text": formatted_text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }

    def _resolve_public_url(self, chat: dict[str, Any], message_id: str | int) -> str | None:
        """Synthesizes the canonical public t.me post URL if the channel is public.

        Args:
            chat: Chat metadata dictionary from response payload.
            message_id: Integer or string message identifier.

        Returns:
            Canonical 'https://t.me/{channel}/{message_id}' URL if public; None otherwise.
        """
        username = chat.get("username")
        if isinstance(username, str) and username.strip():
            clean_username = username.strip().lstrip("@")
            return PlatformConstants.URL_TELEGRAM_PUBLIC_POST.format(
                channel=clean_username, message_id=str(message_id).strip()
            )

        channel_id = (self.settings.telegram_channel_id or "").strip()
        if channel_id.startswith("@"):
            clean_channel = channel_id.lstrip("@").strip()
            return PlatformConstants.URL_TELEGRAM_PUBLIC_POST.format(
                channel=clean_channel, message_id=str(message_id).strip()
            )

        return None

    def _sanitize_token(self, text: str) -> str:
        """Redacts bot secret tokens from URLs and diagnostic error strings.

        Args:
            text: Input string potentially containing secret bot token in URL.

        Returns:
            Sanitized string with bot token masked as 'bot[REDACTED]'.
        """
        return re.sub(r"bot[0-9]{8,10}:[A-Za-z0-9_\-]+", "bot[REDACTED]", text)

    def _extract_error_detail(self, response: httpx.Response) -> str:
        """Extracts and sanitizes Telegram error description from JSON response.

        Args:
            response: Upstream HTTPX response object.

        Returns:
            Sanitized error description string.
        """
        try:
            body = response.json()
            if isinstance(body, dict):
                description = body.get("description")
                if isinstance(description, str) and description.strip():
                    return self._sanitize_token(description.strip())
        except Exception:
            pass
        return f"HTTP {response.status_code}"

    async def post(self, message: str, cta_url: str) -> PlatformResultDto:
        """Dispatches formatted HTML message and CTA link to target Telegram channel.

        Args:
            message: Sanitized message copy (<= 200 unicode characters).
            cta_url: Validated Call-to-Action destination link.

        Returns:
            PlatformResultDto detailing publication outcome, post URL, or error diagnostic.
        """
        if not self.is_configured():
            date_str, time_str = self._get_current_timestamp()
            return PlatformResultDto(
                platform=self.name,
                status=PlatformConstants.STATUS_SKIPPED,
                posted_url=None,
                public_access=False,
                date=date_str,
                time=time_str,
                post_id=None,
                error="Platform credentials not configured in environment.",
                latency_ms=0.0,
            )

        token = (self.settings.telegram_bot_token or "").strip()
        endpoint_url = PlatformConstants.URL_TELEGRAM_SEND_MESSAGE.format(token=token)
        payload = self._build_payload(message, cta_url)
        headers = {"Content-Type": "application/json"}
        start_time = perf_counter()

        try:
            response = await self.client.post(
                endpoint_url,
                json=payload,
                headers=headers,
                timeout=self.settings.adapter_timeout_seconds,
            )
            latency_ms = round((perf_counter() - start_time) * 1000.0, 2)

            if response.status_code == 200:
                try:
                    body = response.json()
                except Exception:
                    body = {}

                if body.get("ok") is True:
                    result_data = (
                        body.get("result", {}) if isinstance(body.get("result"), dict) else {}
                    )
                    raw_msg_id = result_data.get("message_id")
                    post_id = str(raw_msg_id).strip() if raw_msg_id is not None else "unknown"
                    chat_meta = (
                        result_data.get("chat", {})
                        if isinstance(result_data.get("chat"), dict)
                        else {}
                    )
                    post_url = self._resolve_public_url(chat_meta, post_id)
                    public_access = bool(post_url)
                    return self._create_success_result(
                        posted_url=post_url,
                        post_id=post_id,
                        public_access=public_access,
                        latency_ms=latency_ms,
                    )

                description = self._sanitize_token(
                    str(body.get("description", "Unknown Telegram API rejection"))
                )
                error = f"Telegram API error: {description}."
                return self._create_failure_result(error=error, latency_ms=latency_ms)

            if response.status_code == 400:
                detail = self._extract_error_detail(response)
                error = f"Telegram bad request: {detail} (verify channel ID and bot membership)."
            elif response.status_code == 403:
                detail = self._extract_error_detail(response)
                error = (
                    f"Telegram permission denied: {detail} "
                    "(bot must be channel administrator with post messages permission)."
                )
            elif response.status_code == 429:
                error = "Rate limit exceeded on Telegram Bot API."
            else:
                detail = self._extract_error_detail(response)
                error = f"Telegram rejected publication request with HTTP {response.status_code}: {detail}."

            return self._create_failure_result(error=error, latency_ms=latency_ms)

        except httpx.TimeoutException:
            latency_ms = round((perf_counter() - start_time) * 1000.0, 2)
            return self._create_failure_result(
                error="Request timed out waiting for platform response.",
                latency_ms=latency_ms,
            )
        except httpx.RequestError as exc:
            latency_ms = round((perf_counter() - start_time) * 1000.0, 2)
            sanitized_err = self._sanitize_token(self._normalize_exception(exc))
            return self._create_failure_result(
                error=sanitized_err,
                latency_ms=latency_ms,
            )
        except Exception as exc:
            latency_ms = round((perf_counter() - start_time) * 1000.0, 2)
            sanitized_err = self._sanitize_token(self._normalize_exception(exc))
            return self._create_failure_result(
                error=sanitized_err,
                latency_ms=latency_ms,
            )
