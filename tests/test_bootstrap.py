"""Triad unit tests covering application bootstrap, lifespan, and dependency injection lifecycle."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.constants import ApiConstants
from app.main import build_adapter_registry, create_app, lifespan
from app.routers.posting import get_posting_service


class TestBootstrapLifecycle:
    """Bootstrap layer test suite verifying application factory and lifespan context manager."""

    def test_create_app_factory_metadata(self) -> None:
        """Verifies create_app produces an application with OpenAPI contract metadata."""
        app = create_app()
        assert app.title == "Automated Multi-Platform Posting Service API"
        assert app.version == ApiConstants.SERVICE_VERSION
        assert app.description is not None

        route_paths = [route.path for route in app.routes]  # type: ignore[attr-defined]
        assert ApiConstants.ENDPOINT_POSTING in route_paths
        assert ApiConstants.ENDPOINT_HEALTH in route_paths
        assert ApiConstants.ENDPOINT_READY in route_paths

    def test_build_adapter_registry_registers_all_five_adapters(self) -> None:
        """Verifies build_adapter_registry registers all 5 concrete platform adapters."""
        registry = build_adapter_registry()
        registered = registry.registered_names()
        assert len(registered) == 5
        assert "linkedin" in registered
        assert "devto" in registered
        assert "hashnode" in registered
        assert "mastodon" in registered
        assert "telegram" in registered

    @pytest.mark.asyncio
    async def test_lifespan_startup_and_shutdown_management(self) -> None:
        """Verifies lifespan startup binds posting service and cleanup restores overrides."""
        app = create_app()
        assert get_posting_service not in app.dependency_overrides

        async with lifespan(app):
            assert get_posting_service in app.dependency_overrides
            bound_service = app.dependency_overrides[get_posting_service]()
            assert bound_service is not None
            assert len(bound_service.adapters) == 5

        assert get_posting_service not in app.dependency_overrides

    def test_dependency_provider_raises_not_implemented_when_unbound(self) -> None:
        """Verifies get_posting_service provider raises NotImplementedError if called directly."""
        with pytest.raises(
            NotImplementedError, match="Dependency injection provider must be bound"
        ):
            get_posting_service()

    def test_client_executes_with_lifespan_context(self) -> None:
        """Verifies TestClient manages startup and shutdown lifespan hooks seamlessly."""
        app = create_app()
        with TestClient(app) as test_client:
            response = test_client.get(ApiConstants.ENDPOINT_HEALTH)
            assert response.status_code == 200
            assert response.json()["status"] == "ok"

    def test_settings_supports_dual_environment_variable_aliases(self) -> None:
        """Verifies Settings resolves both primary and fallback environment variable aliases."""
        settings_author = Settings(
            LINKEDIN_AUTHOR_URN="urn:li:person:auth123",
            HASHNODE_ACCESS_TOKEN="pat_access_456",
        )
        assert settings_author.linkedin_person_urn == "urn:li:person:auth123"
        assert settings_author.hashnode_api_key == "pat_access_456"

        settings_standard = Settings(
            LINKEDIN_PERSON_URN="urn:li:person:std789",
            HASHNODE_API_KEY="pat_std_012",
        )
        assert settings_standard.linkedin_person_urn == "urn:li:person:std789"
        assert settings_standard.hashnode_api_key == "pat_std_012"
