"""Mastodon Status platform adapter communicating via Mastodon REST API v1.

Publishes broadcast messages and Call-to-Action destination links as public
toots across decentralized ActivityPub fediverse server instances.
"""

import uuid
from time import perf_counter
from typing import Any

import httpx

from app.core.config import Settings
from app.core.constants import PlatformConstants
from app.models.dtos.platform_dto import PlatformResultDto
from app.platforms.base import BasePlatformAdapter
from app.platforms.registry import AdapterRegistry


@AdapterRegistry.register(PlatformConstants.PLATFORM_MASTODON)
class MastodonAdapter(BasePlatformAdapter):
    """Platform adapter for Mastodon ActivityPub REST API v1."""

    def __init__(
        self,
        name: str = PlatformConstants.PLATFORM_MASTODON,
        client: httpx.AsyncClient | None = None,
        settings: Settings | None = None,
    ) -> None:
        """Initializes the Mastodon adapter with HTTP client and runtime settings.

        Args:
            name: Canonical platform slug identifier (defaults to 'mastodon').
            client: Shared asynchronous HTTPX client; falls back to an isolated client.
            settings: Optional runtime settings instance; defaults to fresh Settings.
        """
        active_client = client or httpx.AsyncClient(
            timeout=PlatformConstants.DEFAULT_ADAPTER_TIMEOUT_SECONDS
        )
        super().__init__(name=name, client=active_client, settings=settings)

    def is_configured(self) -> bool:
        """Verifies presence of mandatory Mastodon OAuth access token.

        Returns:
            True if access token is non-empty; False otherwise.
        """
        token = self.settings.mastodon_access_token
        return bool(token and token.strip())

    def _get_endpoint_url(self) -> str:
        """Resolves the canonical Mastodon statuses API endpoint URL.

        Returns:
            Fully-qualified statuses endpoint URL pointing to the configured instance.
        """
        raw_base = (
            (self.settings.mastodon_base_url or "https://mastodon.social").strip().rstrip("/")
        )
        if not raw_base:
            raw_base = "https://mastodon.social"
        return f"{raw_base}{PlatformConstants.PATH_MASTODON_STATUSES}"

    def _build_payload(self, message: str, cta_url: str) -> dict[str, Any]:
        """Constructs the Mastodon status JSON request payload.

        Args:
            message: Sanitized promotional message text.
            cta_url: Validated Call-to-Action destination link.

        Returns:
            Dictionary matching the Mastodon status creation API schema.
        """
        return {
            "status": f"{message.strip()}\n\n{cta_url.strip()}",
            "visibility": "public",
        }

    def _extract_post_id(self, body: dict[str, Any]) -> str | None:
        """Extracts the unique status ID from response payload.

        Args:
            body: Decoded JSON response body.

        Returns:
            Extracted string status ID if present; None otherwise.
        """
        raw_id = body.get("id")
        if raw_id is not None:
            return str(raw_id).strip()
        return None

    def _extract_post_url(self, body: dict[str, Any]) -> str | None:
        """Extracts the canonical public URL from response payload.

        Args:
            body: Decoded JSON response body.

        Returns:
            Extracted canonical toot URL string if present; None otherwise.
        """
        raw_url = body.get("url")
        if isinstance(raw_url, str) and raw_url.strip():
            return raw_url.strip()
        return None

    async def post(self, message: str, cta_url: str) -> PlatformResultDto:
        """Dispatches status toot to the configured Mastodon fediverse instance.

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

        endpoint_url = self._get_endpoint_url()
        idempotency_key = str(uuid.uuid4())
        headers = {
            "Authorization": f"Bearer {(self.settings.mastodon_access_token or '').strip()}",
            PlatformConstants.HEADER_IDEMPOTENCY_KEY: idempotency_key,
            "Content-Type": "application/json",
        }
        payload = self._build_payload(message, cta_url)
        start_time = perf_counter()

        try:
            response = await self.client.post(
                endpoint_url,
                json=payload,
                headers=headers,
                timeout=self.settings.adapter_timeout_seconds,
            )
            latency_ms = round((perf_counter() - start_time) * 1000.0, 2)

            if response.status_code in (200, 201):
                try:
                    body = response.json()
                except Exception:
                    body = {}
                post_id = self._extract_post_id(body) or "unknown"
                post_url = self._extract_post_url(body)
                return self._create_success_result(
                    posted_url=post_url,
                    post_id=post_id,
                    public_access=True,
                    latency_ms=latency_ms,
                )

            if response.status_code == 401:
                error = "Authentication failed: invalid or expired Mastodon access token."
            elif response.status_code == 422:
                error = "Mastodon validation error: unprocessable status payload."
            elif response.status_code == 429:
                error = "Rate limit exceeded on Mastodon API (5-minute sliding window)."
            else:
                error = f"Mastodon rejected publication request with HTTP {response.status_code}."

            return self._create_failure_result(error=error, latency_ms=latency_ms)

        except httpx.TimeoutException:
            latency_ms = round((perf_counter() - start_time) * 1000.0, 2)
            return self._create_failure_result(
                error="Request timed out waiting for platform response.",
                latency_ms=latency_ms,
            )
        except httpx.RequestError as exc:
            latency_ms = round((perf_counter() - start_time) * 1000.0, 2)
            return self._create_failure_result(
                error=self._normalize_exception(exc),
                latency_ms=latency_ms,
            )
        except Exception as exc:
            latency_ms = round((perf_counter() - start_time) * 1000.0, 2)
            return self._create_failure_result(
                error=self._normalize_exception(exc),
                latency_ms=latency_ms,
            )
