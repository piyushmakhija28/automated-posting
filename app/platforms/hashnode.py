"""Hashnode Publication platform adapter communicating via Hashnode GraphQL API.

Publishes broadcast messages as published articles to a Hashnode publication
with synthesized titles, formatted markdown body, and Call-to-Action destination links.
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


@AdapterRegistry.register(PlatformConstants.PLATFORM_HASHNODE)
class HashnodeAdapter(BasePlatformAdapter):
    """Platform adapter for Hashnode developer publication GraphQL API."""

    def __init__(
        self,
        name: str = PlatformConstants.PLATFORM_HASHNODE,
        client: httpx.AsyncClient | None = None,
        settings: Settings | None = None,
    ) -> None:
        """Initializes the Hashnode adapter with HTTP client and runtime settings.

        Args:
            name: Canonical platform slug identifier (defaults to 'hashnode').
            client: Shared asynchronous HTTPX client; falls back to an isolated client.
            settings: Optional runtime settings instance; defaults to fresh Settings.
        """
        active_client = client or httpx.AsyncClient(
            timeout=PlatformConstants.DEFAULT_ADAPTER_TIMEOUT_SECONDS
        )
        super().__init__(name=name, client=active_client, settings=settings)

    def is_configured(self) -> bool:
        """Verifies presence of mandatory Hashnode API key and publication ID.

        Returns:
            True if both API key and publication ID are populated; False otherwise.
        """
        key = self.settings.hashnode_api_key
        pub_id = self.settings.hashnode_publication_id
        return bool(key and key.strip() and pub_id and pub_id.strip())

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
        """Constructs the GraphQL publishPost mutation query and input variables.

        Args:
            message: Sanitized message copy.
            cta_url: Validated Call-to-Action destination link.

        Returns:
            Dictionary matching the Hashnode GraphQL mutation schema.
        """
        title = self._synthesize_title(message)
        body_markdown = f"{message.strip()}\n\n[Read More]({cta_url.strip()})"
        pub_id = (self.settings.hashnode_publication_id or "").strip()
        return {
            "query": PlatformConstants.MUTATION_HASHNODE_PUBLISH_POST,
            "variables": {
                "input": {
                    "title": title,
                    "contentMarkdown": body_markdown,
                    "publicationId": pub_id,
                    "tags": [],
                }
            },
        }

    def _extract_graphql_error(self, body: dict[str, Any]) -> str | None:
        """Extracts the first error message from GraphQL response errors array.

        Args:
            body: Decoded JSON response body.

        Returns:
            Error message string if errors exist; None otherwise.
        """
        errors = body.get("errors")
        if isinstance(errors, list) and errors:
            first_err = errors[0]
            if isinstance(first_err, dict):
                msg = first_err.get("message")
                if isinstance(msg, str) and msg.strip():
                    return msg.strip()
            return "Unknown GraphQL error"
        return None

    def _extract_post_details(
        self, body: dict[str, Any]
    ) -> tuple[str | None, str | None]:
        """Extracts article post ID and canonical URL from GraphQL data payload.

        Args:
            body: Decoded JSON response body.

        Returns:
            Tuple of (post_id, post_url).
        """
        data = body.get("data")
        if not isinstance(data, dict):
            return None, None

        publish_post = data.get("publishPost")
        if not isinstance(publish_post, dict):
            return None, None

        post = publish_post.get("post")
        if not isinstance(post, dict):
            return None, None

        raw_id = post.get("id")
        post_id = str(raw_id).strip() if raw_id is not None else None

        raw_url = post.get("url")
        post_url = str(raw_url).strip() if isinstance(raw_url, str) and raw_url.strip() else None

        return post_id, post_url

    async def post(self, message: str, cta_url: str) -> PlatformResultDto:
        """Dispatches GraphQL publication mutation to the Hashnode Public API.

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
            "Authorization": (self.settings.hashnode_api_key or "").strip(),
            "Content-Type": "application/json",
        }
        payload = self._build_payload(message, cta_url)
        start_time = perf_counter()

        try:
            response = await self.client.post(
                PlatformConstants.URL_HASHNODE_GQL,
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

                gql_error = self._extract_graphql_error(body)
                if gql_error:
                    error = f"Hashnode GraphQL error: {gql_error}."
                    return self._create_failure_result(
                        error=error, latency_ms=latency_ms
                    )

                post_id, post_url = self._extract_post_details(body)
                return self._create_success_result(
                    posted_url=post_url,
                    post_id=post_id or "unknown",
                    public_access=True,
                    latency_ms=latency_ms,
                )

            if response.status_code == 401:
                error = "Authentication failed: invalid or expired Hashnode API key."
            elif response.status_code == 429:
                error = "Rate limit exceeded on Hashnode GraphQL API."
            else:
                error = (
                    f"Hashnode rejected publication request with HTTP {response.status_code}."
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
