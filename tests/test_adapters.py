"""Triad unit test suite for BasePlatformAdapter contract and AdapterRegistry factory."""

import re
from typing import Any

import httpx
import pytest

from app.core.config import Settings
from app.core.constants import PlatformConstants
from app.models.dtos.platform_dto import PlatformResultDto
from app.platforms.base import BasePlatformAdapter
from app.platforms.registry import AdapterRegistry


class DummyValidAdapter(BasePlatformAdapter):
    """Test stub implementing BasePlatformAdapter contract for verification."""

    def is_configured(self) -> bool:
        """Stub configuration check returning True."""
        return True

    async def post(self, message: str, cta_url: str) -> PlatformResultDto:
        """Stub publication returning a success result."""
        return self._create_success_result(
            posted_url=f"https://platform.example.com/posts/101?url={cta_url}",
            post_id="post-101",
            public_access=True,
            latency_ms=45.2,
        )


class DummyUnconfiguredAdapter(BasePlatformAdapter):
    """Test stub representing an unconfigured adapter."""

    def is_configured(self) -> bool:
        """Stub configuration check returning False."""
        return False

    async def post(self, message: str, cta_url: str) -> PlatformResultDto:
        """Stub publication returning a failure result."""
        return self._create_failure_result(error="Missing API credentials.", latency_ms=10.0)


class IncompleteAdapter(BasePlatformAdapter):
    """Test stub missing abstract method implementations."""


class TestBasePlatformAdapterPositive:
    """Positive test scenarios for BasePlatformAdapter interface and helpers."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self) -> Any:
        """Clears class-level adapter registry before and after each test, restoring baseline state."""
        saved = dict(AdapterRegistry._registry)
        AdapterRegistry.clear()
        yield
        AdapterRegistry._registry.clear()
        AdapterRegistry._registry.update(saved)

    @pytest.mark.asyncio
    async def test_concrete_adapter_initialization_and_properties(self) -> None:
        """Verifies concrete adapter instantiates with correct properties and shared client."""
        async with httpx.AsyncClient() as client:
            settings = Settings()
            adapter = DummyValidAdapter(name="test_platform", client=client, settings=settings)

            assert adapter.name == "test_platform"
            assert adapter.client is client
            assert adapter.settings is settings
            assert adapter.is_configured() is True
            assert adapter.logger.name == "app.platforms.test_platform"

    @pytest.mark.asyncio
    async def test_timestamp_generation_iso_format(self) -> None:
        """Verifies _get_current_timestamp returns valid UTC date and time."""
        async with httpx.AsyncClient() as client:
            adapter = DummyValidAdapter(name="test_platform", client=client)
            date_str, time_str = adapter._get_current_timestamp()

            date_regex = re.compile(r"^\d{4}-\d{2}-\d{2}$")
            time_regex = re.compile(r"^\d{2}:\d{2}:\d{2}$")

            assert date_regex.match(date_str) is not None
            assert time_regex.match(time_str) is not None
            assert adapter._extract_date_time() == (date_str, time_str)

    @pytest.mark.asyncio
    async def test_create_success_result_helper(self) -> None:
        """Verifies _create_success_result constructs compliant success PlatformResultDto."""
        async with httpx.AsyncClient() as client:
            adapter = DummyValidAdapter(name="test_platform", client=client)
            result = adapter._create_success_result(
                posted_url="https://platform.example.com/item/42",
                post_id="id-42",
                public_access=True,
                latency_ms=120.5,
            )

            assert result.platform == "test_platform"
            assert result.status == PlatformConstants.STATUS_SUCCESS
            assert result.posted_url == "https://platform.example.com/item/42"
            assert result.post_url == "https://platform.example.com/item/42"
            assert result.post_id == "id-42"
            assert result.public_access is True
            assert result.error is None
            assert result.latency_ms == 120.5
            assert result.date is not None
            assert result.time is not None

    @pytest.mark.asyncio
    async def test_create_failure_result_helper(self) -> None:
        """Verifies _create_failure_result constructs compliant failed PlatformResultDto."""
        async with httpx.AsyncClient() as client:
            adapter = DummyValidAdapter(name="test_platform", client=client)
            result = adapter._create_failure_result(
                error="Upstream gateway unreachable.",
                latency_ms=3000.0,
            )

            assert result.platform == "test_platform"
            assert result.status == PlatformConstants.STATUS_FAILED
            assert result.posted_url is None
            assert result.post_id is None
            assert result.public_access is False
            assert result.error == "Upstream gateway unreachable."
            assert result.latency_ms == 3000.0

    @pytest.mark.asyncio
    async def test_post_execution(self) -> None:
        """Verifies async post execution yields structured PlatformResultDto."""
        async with httpx.AsyncClient() as client:
            adapter = DummyValidAdapter(name="test_platform", client=client)
            result = await adapter.post(
                message="Promotional announcement",
                cta_url="https://example.com/promo",
            )

            assert result.status == PlatformConstants.STATUS_SUCCESS
            assert result.post_id == "post-101"
            assert "https://example.com/promo" in str(result.posted_url)


class TestBasePlatformAdapterNegative:
    """Negative test scenarios for abstract contract violations and error normalization."""

    def test_abstract_class_cannot_be_instantiated(self) -> None:
        """Verifies BasePlatformAdapter cannot be instantiated directly."""
        with pytest.raises(TypeError) as exc_info:
            BasePlatformAdapter(name="abstract", client=httpx.AsyncClient())  # type: ignore[abstract]
        assert "Can't instantiate abstract class" in str(exc_info.value)

    def test_incomplete_subclass_cannot_be_instantiated(self) -> None:
        """Verifies subclasses missing abstract methods fail instantiation."""
        with pytest.raises(TypeError) as exc_info:
            IncompleteAdapter(name="incomplete", client=httpx.AsyncClient())  # type: ignore[abstract]
        assert "Can't instantiate abstract class" in str(exc_info.value)

    @pytest.mark.parametrize(
        ("status_code", "expected_fragment"),
        [
            (401, "Authentication failed"),
            (403, "Permission denied"),
            (429, "Rate limit exceeded"),
            (500, "HTTP 500"),
            (502, "HTTP 502"),
            (503, "HTTP 503"),
        ],
    )
    def test_normalize_http_status_errors(
        self,
        status_code: int,
        expected_fragment: str,
    ) -> None:
        """Verifies _normalize_exception translates HTTP error codes into clean diagnostic messages."""
        request = httpx.Request("POST", "https://api.example.com/post")
        response = httpx.Response(status_code=status_code, request=request)
        error = httpx.HTTPStatusError("HTTP Error", request=request, response=response)

        adapter = DummyValidAdapter(name="dummy", client=httpx.AsyncClient())
        message = adapter._normalize_exception(error)
        assert expected_fragment in message
        assert adapter._handle_error(error) == message

    def test_normalize_timeout_error(self) -> None:
        """Verifies _normalize_exception handles HTTPX timeout exceptions."""
        request = httpx.Request("POST", "https://api.example.com/timeout")
        error = httpx.TimeoutException("Read timed out", request=request)

        adapter = DummyValidAdapter(name="dummy", client=httpx.AsyncClient())
        message = adapter._normalize_exception(error)
        assert "timed out" in message.lower()

    def test_normalize_network_request_error(self) -> None:
        """Verifies _normalize_exception handles connection and DNS transport errors."""
        request = httpx.Request("POST", "https://api.example.com/network")
        error = httpx.RequestError("DNS resolution failed", request=request)

        adapter = DummyValidAdapter(name="dummy", client=httpx.AsyncClient())
        message = adapter._normalize_exception(error)
        assert "Network or connection error" in message

    def test_normalize_generic_unexpected_error(self) -> None:
        """Verifies _normalize_exception handles uncaught runtime exceptions without leaking internals."""
        error = RuntimeError("Unexpected internal pointer corruption")

        adapter = DummyValidAdapter(name="dummy", client=httpx.AsyncClient())
        message = adapter._normalize_exception(error)
        assert "Internal platform communication error" in message


class TestAdapterRegistry:
    """Verification suite for AdapterRegistry registration, factory instantiation, and isolation."""

    @pytest.fixture(autouse=True)
    def clean_registry(self) -> Any:
        """Ensures isolated class-level registry state for test, restoring baseline afterwards."""
        saved = dict(AdapterRegistry._registry)
        AdapterRegistry.clear()
        yield
        AdapterRegistry._registry.clear()
        AdapterRegistry._registry.update(saved)

    def test_decorator_registration(self) -> None:
        """Verifies @AdapterRegistry.register properly binds adapter class."""

        @AdapterRegistry.register("decorated_platform")
        class DecoratedAdapter(DummyValidAdapter):
            pass

        assert AdapterRegistry.get_adapter_class("decorated_platform") is DecoratedAdapter
        assert "decorated_platform" in AdapterRegistry.registered_names()

    def test_direct_registration(self) -> None:
        """Verifies direct AdapterRegistry.register_adapter registration."""
        AdapterRegistry.register_adapter("direct_platform", DummyValidAdapter)

        assert AdapterRegistry.get_adapter_class("direct_platform") is DummyValidAdapter
        assert "direct_platform" in AdapterRegistry.registered_names()

    def test_unregistered_slug_returns_none(self) -> None:
        """Verifies query for non-existent platform slug returns None."""
        assert AdapterRegistry.get_adapter_class("unregistered_slug") is None

    @pytest.mark.asyncio
    async def test_create_all_instantiates_registered_adapters(self) -> None:
        """Verifies create_all instantiates all registered adapters with client and settings."""
        AdapterRegistry.register_adapter("platform_a", DummyValidAdapter)
        AdapterRegistry.register_adapter("platform_b", DummyUnconfiguredAdapter)

        async with httpx.AsyncClient() as client:
            settings = Settings()
            adapters = AdapterRegistry.create_all(client=client, settings=settings)

            assert len(adapters) == 2
            names = [a.name for a in adapters]
            assert "platform_a" in names
            assert "platform_b" in names

            for a in adapters:
                assert a.client is client
                assert a.settings is settings

    @pytest.mark.asyncio
    async def test_create_all_empty_registry(self) -> None:
        """Verifies create_all on empty registry returns empty list without error."""
        async with httpx.AsyncClient() as client:
            adapters = AdapterRegistry.create_all(client=client)
            assert adapters == []

    def test_registry_clear_isolation(self) -> None:
        """Verifies clear removes all registered adapters."""
        AdapterRegistry.register_adapter("temp", DummyValidAdapter)
        assert len(AdapterRegistry.registered_names()) == 1

        AdapterRegistry.clear()
        assert len(AdapterRegistry.registered_names()) == 0
        assert AdapterRegistry.get_adapter_class("temp") is None

    @pytest.mark.asyncio
    async def test_instance_registry_lifecycle(self) -> None:
        """Verifies instance-scoped registry behaves independently from class registry."""
        registry = AdapterRegistry()
        registry.register_instance("instance_plat", DummyValidAdapter)

        assert AdapterRegistry.get_adapter_class("instance_plat") is None

        async with httpx.AsyncClient() as client:
            instances = registry.create_all_instances(client=client)
            assert len(instances) == 1
            assert instances[0].name == "instance_plat"

        registry.clear_instance()
        async with httpx.AsyncClient() as client:
            assert registry.create_all_instances(client=client) == []
