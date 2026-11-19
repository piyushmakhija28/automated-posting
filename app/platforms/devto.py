"""Dev.to Article platform adapter communicating via Forem REST API.

Publishes broadcast messages as published articles on Dev.to with synthesized
readable titles, formatted markdown body content, and Call-to-Action destination links.
"""

import re
from time import perf_counter
from typing import Any

import httpx

from app.core.config import Settings
from app.core.constants import PlatformConstants
from app.models.dtos.platform_dto import PlatformResultDto
from app.platforms.base import BasePlatformAdapter
from app.platforms.registry import AdapterRegistry


@AdapterRegistry.register(PlatformConstants.PLATFORM_DEVTO)
class DevToAdapter(BasePlatformAdapter):
    """Platform adapter for Dev.to (Forem engine) Articles REST API."""

    def __init__(
        self,
        name: str = PlatformConstants.PLATFORM_DEVTO,
        client: httpx.AsyncClient | None = None,
        settings: Settings | None = None,
    ) -> None:
        """Initializes the Dev.to adapter with HTTP client and runtime settings.

        Args:
            name: Canonical platform slug identifier (defaults to 'devto').
            client: Shared asynchronous HTTPX client; falls back to an isolated client.
            settings: Optional runtime settings instance; defaults to fresh Settings.
        """
        active_client = client or httpx.AsyncClient(
            timeout=PlatformConstants.DEFAULT_ADAPTER_TIMEOUT_SECONDS
        )
        super().__init__(name=name, client=active_client, settings=settings)

    def is_configured(self) -> bool:
        """Verifies presence of mandatory Dev.to API key in settings.

        Returns:
            True if DEVTO_API_KEY is populated and non-blank; False otherwise.
        """
        key = self.settings.devto_api_key
        return bool(key and key.strip())

    def _synthesize_title(self, message: str) -> str:
        """Synthesizes a clean, readable article title from promotional message copy.

        Strips raw URL artifacts, detects the first sentence boundary, or cleanly
        truncates at 60 characters with an ellipsis, ensuring length <= 128 characters.

        Args:
            message: Ingress message text.

        Returns:
            Synthesized title string guaranteed to be non-empty and <= 128 characters.
        """
        cleaned = re.sub(r"https?://\S+", "", message).strip()
        if not cleaned:
            return "Platform Update"

        parts = re.split(r"(?<=[.!?])(?:\s+|$)|[\r\n]+", cleaned)
        first_sentence = parts[0].strip() if parts else cleaned
        candidate = first_sentence or cleaned

        if len(candidate) > 60:
            truncated = candidate[:60].rstrip()
            last_space = truncated.rfind(" ")
            if last_space > 20:
                truncated = truncated[:last_space].rstrip()
            title = f"{truncated}..."
        else:
            title = candidate

        title = title.strip() or "Platform Update"
        return title[:128]

    def _build_payload(self, message: str, cta_url: str) -> dict[str, Any]:
        """Constructs the Forem article JSON request payload.

        Args:
            message: Sanitized message copy.
            cta_url: Validated Call-to-Action destination link.

        Returns:
            Dictionary matching the Forem Article creation API schema.
        """
        title = self._synthesize_title(message)
        body_markdown = f"{message.strip()}\n\n[Read More]({cta_url.strip()})"
        return {
            "article": {
                "title": title,
                "body_markdown": body_markdown,
                "published": True,
                "tags": ["tech", "updates", "announcement"],
            }
        }

    def _extract_post_id(self, body: dict[str, Any]) -> str | None:
        """Extracts the unique article ID from the response payload.

        Args:
            body: Decoded JSON response body.

        Returns:
            Extracted string post ID if present; None otherwise.
        """
        raw_id = body.get("id")
        if raw_id is not None:
            return str(raw_id).strip()
        return None

    def _extract_post_url(self, body: dict[str, Any]) -> str | None:
        """Extracts the canonical public URL from the response payload.

        Args:
            body: Decoded JSON response body.

        Returns:
            Extracted canonical article URL string if present; None otherwise.
        """
        raw_url = body.get("url")
        if isinstance(raw_url, str) and raw_url.strip():
            return raw_url.strip()
        return None

    async def post(self, message: str, cta_url: str) -> PlatformResultDto:
        """Dispatches synthesized article payload to the Dev.to Forem REST API.

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

        headers = {
            PlatformConstants.HEADER_DEVTO_API_KEY: (
                self.settings.devto_api_key or ""
            ).strip(),
            "Content-Type": "application/json",
        }
        payload = self._build_payload(message, cta_url)
        start_time = perf_counter()

        try:
            response = await self.client.post(
                PlatformConstants.URL_DEVTO_ARTICLES,
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
                error = "Authentication failed: invalid or missing Dev.to API key."
            elif response.status_code == 422:
                try:
                    error_body = response.json()
                    detail = error_body.get("error", "article rejected by Forem engine")
                except Exception:
                    detail = "article rejected by Forem engine"
                error = f"Dev.to validation error: {detail}."
            elif response.status_code == 429:
                error = "Rate limit exceeded on Dev.to API."
            else:
                error = (
                    f"Dev.to rejected publication request with HTTP {response.status_code}."
                )

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
