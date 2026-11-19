"""Pytest conftest providing shared fixtures, mock services, and async clients."""

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app
from app.routers.posting import get_posting_service
from app.services.posting_service import PostingService


@pytest.fixture
def mock_posting_service() -> AsyncMock:
    """Provides a mocked PostingService for controller isolation testing."""
    return AsyncMock(spec=PostingService)


@pytest.fixture
def app_with_mock_service(mock_posting_service: AsyncMock) -> FastAPI:
    """Instantiates app with PostingService dependency override."""
    test_app = create_app()
    test_app.dependency_overrides[get_posting_service] = lambda: mock_posting_service
    yield test_app
    test_app.dependency_overrides.clear()


@pytest.fixture
def client(app_with_mock_service: FastAPI) -> TestClient:
    """Provides a synchronous TestClient bound to the mock service override."""
    return TestClient(app_with_mock_service, raise_server_exceptions=False)


@pytest.fixture
async def async_client(app_with_mock_service: FastAPI) -> AsyncIterator[AsyncClient]:
    """Provides an asynchronous HTTPX client using ASGITransport for non-blocking testing."""
    transport = ASGITransport(app=app_with_mock_service)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
def mock_settings() -> Settings:
    """Provides a fully populated Settings instance for multi-platform integration testing."""
    return Settings(
        linkedin_access_token="test_linkedin_token",
        linkedin_person_urn="urn:li:person:test12345",
        devto_api_key="test_devto_key",
        hashnode_api_key="test_hashnode_key",
        hashnode_publication_id="test_pub_12345",
        mastodon_access_token="test_mastodon_token",
        mastodon_base_url="https://mastodon.social",
        telegram_bot_token="test_bot_token:123456",
        telegram_channel_id="@test_channel",
    )
