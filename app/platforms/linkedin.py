"""LinkedIn UGC Post platform adapter communicating via OAuth 2.0 UGC API v2.

Publishes broadcast messages with commentary and Call-to-Action article
links to LinkedIn member feeds using the Community Management UGC Posts API.
"""

from time import perf_counter
from typing import Any

import httpx

from app.core.config import Settings
from app.core.constants import PlatformConstants
from app.models.dtos.platform_dto import PlatformResultDto
from app.platforms.base import BasePlatformAdapter
from app.platforms.registry import AdapterRegistry


@AdapterRegistry.register(PlatformConstants.PLATFORM_LINKEDIN)
class LinkedInAdapter(BasePlatformAdapter):
    """Platform adapter for LinkedIn UGC Posts API v2."""

    def __init__(
        self,
        name: str = PlatformConstants.PLATFORM_LINKEDIN,
        client: httpx.AsyncClient | None = None,
        settings: Settings | None = None,
    ) -> None:
        """Initializes the LinkedIn adapter with HTTP client and runtime settings.

        Args:
            name: Canonical platform slug identifier (defaults to 'linkedin').
            client: Shared asynchronous HTTPX client; falls back to an isolated client.
            settings: Optional runtime settings instance; defaults to fresh Settings.
        """
        active_client = client or httpx.AsyncClient(
            timeout=PlatformConstants.DEFAULT_ADAPTER_TIMEOUT_SECONDS
        )
        super().__init__(name=name, client=active_client, settings=settings)

    def is_configured(self) -> bool:
        """Verifies presence of mandatory LinkedIn OAuth token and Person URN.

        Returns:
            True if both access token and person URN are populated; False otherwise.
        """
        token = self.settings.linkedin_access_token
        urn = self.settings.linkedin_person_urn
        return bool(token and token.strip() and urn and urn.strip())

    def _format_author_urn(self) -> str:
        """Normalizes and formats the LinkedIn Person URN string.

        Returns:
            Fully-qualified URN string formatted as 'urn:li:person:{id}'.
        """
        raw_urn = (self.settings.linkedin_person_urn or "").strip()
        if raw_urn.startswith("urn:li:person:"):
            return raw_urn
        return f"urn:li:person:{raw_urn}"

    def _build_payload(self, message: str, cta_url: str) -> dict[str, Any]:
        """Constructs the official LinkedIn UGC ShareContent JSON request body.

        Args:
            message: Sanitized promotional text copy.
            cta_url: Validated Call-to-Action destination link.

        Returns:
            Dictionary matching the LinkedIn UGC Posts API specification.
        """
        return {
            "author": self._format_author_urn(),
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": message},
                    "shareMediaCategory": "ARTICLE",
                    "media": [
                        {
                            "status": "READY",
                            "originalUrl": cta_url,
                        }
                    ],
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC",
            },
        }

    def _extract_post_id(self, response: httpx.Response) -> str | None:
        """Extracts the unique post identifier from response headers or body.

        Args:
            response: Upstream HTTPX response object.

        Returns:
            The extracted URN string if present; None otherwise.
        """
        header_id = response.headers.get("X-RestLi-Id")
        if header_id and isinstance(header_id, str) and header_id.strip():
            return str(header_id.strip())

        try:
            body = response.json()
            if isinstance(body, dict):
                body_id = body.get("id")
                if isinstance(body_id, str) and body_id.strip():
                    return str(body_id.strip())
        except Exception:
            pass

        return None

    async def post(self, message: str, cta_url: str) -> PlatformResultDto:
        """Dispatches promotional message and CTA link to LinkedIn UGC Posts API.

        Args:
            message: Sanitized message copy (<= 200 unicode characters).
            cta_url: Validated Call-to-Action destination link.

        Returns:
            PlatformResultDto detailing execution status, post URL, or sanitized error.
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
            "Authorization": f"Bearer {self.settings.linkedin_access_token}",
            PlatformConstants.HEADER_RESTLI_PROTOCOL_VERSION: (
                PlatformConstants.RESTLI_PROTOCOL_VERSION_VALUE
            ),
            "Content-Type": "application/json",
        }
        payload = self._build_payload(message, cta_url)
        start_time = perf_counter()

        try:
            response = await self.client.post(
                PlatformConstants.URL_LINKEDIN_UGC_POSTS,
                json=payload,
                headers=headers,
                timeout=self.settings.adapter_timeout_seconds,
            )
            latency_ms = round((perf_counter() - start_time) * 1000.0, 2)

            if response.status_code in (200, 201):
                post_id = self._extract_post_id(response) or "unknown"
                post_url = PlatformConstants.URL_LINKEDIN_FEED_UPDATE.format(id=post_id)
                return self._create_success_result(
                    posted_url=post_url,
                    post_id=post_id,
                    public_access=True,
                    latency_ms=latency_ms,
                )

            if response.status_code == 401:
                error = "Authentication failed: invalid or expired LinkedIn access token."
            elif response.status_code == 403:
                error = (
                    "Permission denied: insufficient LinkedIn OAuth scopes (w_member_social required)."
                )
            elif response.status_code == 429:
                error = "Rate limit exceeded on LinkedIn UGC Posts API."
            else:
                error = f"LinkedIn rejected publication request with HTTP {response.status_code}."

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
