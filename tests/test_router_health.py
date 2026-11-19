"""Triad unit tests covering SRE health, liveness, readiness, and Starlette error handlers."""

from datetime import datetime
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.constants import ApiConstants
from app.main import create_app


class TestHealthProbes:
    """Triad test suite covering SRE health probes and Starlette HTTP exceptions."""

    def test_liveness_probe_returns_200_ok(self, client: TestClient) -> None:
        """Verifies TC-POS-05: GET /health liveness probe returns HTTP 200 with ok status."""
        response = client.get(ApiConstants.ENDPOINT_HEALTH)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == ApiConstants.SERVICE_VERSION
        assert "timestamp" in data
        assert datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))

    def test_readiness_probe_returns_200_ready(self, client: TestClient) -> None:
        """Verifies TC-POS-05: GET /ready readiness probe returns HTTP 200 with platform statuses."""
        response = client.get(ApiConstants.ENDPOINT_READY)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["version"] == ApiConstants.SERVICE_VERSION
        assert isinstance(data["platforms_configured"], int)
        assert isinstance(data["adapters"], dict)
        assert "linkedin" in data["adapters"]
        assert "devto" in data["adapters"]
        assert "hashnode" in data["adapters"]
        assert "mastodon" in data["adapters"]
        assert "telegram" in data["adapters"]

    def test_readiness_probe_with_all_credentials_configured(self) -> None:
        """Verifies readiness probe reports 5 platforms configured when all credentials are set."""
        mock_settings = Settings(
            linkedin_access_token="tok",
            linkedin_person_urn="urn:li:person:123",
            devto_api_key="key",
            hashnode_api_key="key",
            hashnode_publication_id="pub-123",
            mastodon_access_token="tok",
            mastodon_base_url="https://mastodon.social",
            telegram_bot_token="bot:tok",
            telegram_channel_id="@chan",
        )
        with patch("app.routers.health.Settings", return_value=mock_settings):
            app = create_app()
            test_client = TestClient(app)
            response = test_client.get(ApiConstants.ENDPOINT_READY)

            assert response.status_code == 200
            data = response.json()
            assert data["platforms_configured"] == 5
            assert data["adapters"]["linkedin"] is True
            assert data["adapters"]["devto"] is True
            assert data["adapters"]["hashnode"] is True
            assert data["adapters"]["mastodon"] is True
            assert data["adapters"]["telegram"] is True

    def test_readiness_probe_with_no_credentials_configured(self) -> None:
        """Verifies readiness probe reports 0 platforms configured when all credentials are empty."""
        mock_settings = Settings(
            linkedin_access_token=None,
            linkedin_person_urn=None,
            devto_api_key=None,
            hashnode_api_key=None,
            hashnode_publication_id=None,
            mastodon_access_token=None,
            mastodon_base_url=None,
            telegram_bot_token=None,
            telegram_channel_id=None,
        )
        with patch("app.routers.health.Settings", return_value=mock_settings):
            app = create_app()
            test_client = TestClient(app)
            response = test_client.get(ApiConstants.ENDPOINT_READY)

            assert response.status_code == 200
            data = response.json()
            assert data["platforms_configured"] == 0
            assert data["adapters"]["linkedin"] is False
            assert data["adapters"]["devto"] is False

    def test_starlette_not_found_returns_404_problem_details(
        self, client: TestClient
    ) -> None:
        """Verifies non-existent route returns HTTP 404 with RFC 7807 problem details."""
        response = client.get("/nonexistent-endpoint-route")

        assert response.status_code == 404
        assert response.headers["Content-Type"] == "application/problem+json"
        data = response.json()
        assert data["status"] == 404
        assert data["code"] == "ERR_HTTP_404"

    def test_starlette_method_not_allowed_returns_405_problem_details(
        self, client: TestClient
    ) -> None:
        """Verifies unsupported HTTP method returns HTTP 405 with RFC 7807 problem details."""
        response = client.get(ApiConstants.ENDPOINT_POSTING)

        assert response.status_code == 405
        assert response.headers["Content-Type"] == "application/problem+json"
        data = response.json()
        assert data["status"] == 405
        assert data["code"] == "ERR_HTTP_405"
