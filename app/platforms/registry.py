"""AdapterRegistry factory for registering and instantiating platform adapters.

Implements the GoF Factory and Registry patterns, decoupling the domain
service orchestrator from concrete adapter implementations (DIP & OCP).
"""

from collections.abc import Callable
from typing import TypeVar

import httpx

from app.core.config import Settings
from app.platforms.base import BasePlatformAdapter

TAdapter = TypeVar("TAdapter", bound=BasePlatformAdapter)


class AdapterRegistry:
    """Central registry and creational factory for platform adapters."""

    _registry: dict[str, type[BasePlatformAdapter]] = {}

    def __init__(self) -> None:
        """Initializes an instance-scoped registry copy."""
        self._instance_registry: dict[str, type[BasePlatformAdapter]] = {}

    @classmethod
    def register(cls, name: str) -> Callable[[type[TAdapter]], type[TAdapter]]:
        """Class decorator for registering an adapter class under a platform name slug.

        Args:
            name: Canonical platform identifier slug (e.g. 'linkedin', 'devto').

        Returns:
            Decorator function that registers and returns the adapter class.
        """

        def decorator(adapter_cls: type[TAdapter]) -> type[TAdapter]:
            cls._registry[name] = adapter_cls
            return adapter_cls

        return decorator

    @classmethod
    def register_adapter(cls, name: str, adapter_cls: type[BasePlatformAdapter]) -> None:
        """Directly registers an adapter class in the class-level registry.

        Args:
            name: Canonical platform identifier slug.
            adapter_cls: Class implementing BasePlatformAdapter interface.
        """
        cls._registry[name] = adapter_cls

    @classmethod
    def get_adapter_class(cls, name: str) -> type[BasePlatformAdapter] | None:
        """Retrieves a registered adapter class by its platform slug.

        Args:
            name: Canonical platform identifier slug.

        Returns:
            The adapter class if registered; None otherwise.
        """
        return cls._registry.get(name)

    @classmethod
    def registered_names(cls) -> list[str]:
        """Returns a list of all currently registered platform slugs.

        Returns:
            List of string platform identifiers in order of registration.
        """
        return list(cls._registry.keys())

    @classmethod
    def create_all(
        cls,
        client: httpx.AsyncClient,
        settings: Settings | None = None,
    ) -> list[BasePlatformAdapter]:
        """Instantiates all registered platform adapters using injected dependencies.

        Args:
            client: Shared asynchronous HTTPX client.
            settings: Optional runtime settings; defaults to fresh Settings.

        Returns:
            List of instantiated BasePlatformAdapter instances.
        """
        active_settings = settings or Settings()
        adapters: list[BasePlatformAdapter] = []
        for name, adapter_cls in cls._registry.items():
            adapter = adapter_cls(name=name, client=client, settings=active_settings)
            adapters.append(adapter)
        return adapters

    @classmethod
    def clear(cls) -> None:
        """Flushes all registered adapters from the class-level registry."""
        cls._registry.clear()

    def register_instance(self, name: str, adapter_cls: type[BasePlatformAdapter]) -> None:
        """Registers an adapter class in this specific registry instance.

        Args:
            name: Canonical platform identifier slug.
            adapter_cls: Class implementing BasePlatformAdapter interface.
        """
        self._instance_registry[name] = adapter_cls

    def create_all_instances(
        self,
        client: httpx.AsyncClient,
        settings: Settings | None = None,
    ) -> list[BasePlatformAdapter]:
        """Instantiates all adapters registered in this specific registry instance.

        Args:
            client: Shared asynchronous HTTPX client.
            settings: Optional runtime settings; defaults to fresh Settings.

        Returns:
            List of instantiated BasePlatformAdapter instances.
        """
        active_settings = settings or Settings()
        adapters: list[BasePlatformAdapter] = []
        for name, adapter_cls in self._instance_registry.items():
            adapter = adapter_cls(name=name, client=client, settings=active_settings)
            adapters.append(adapter)
        return adapters

    def clear_instance(self) -> None:
        """Flushes all registered adapters from this specific registry instance."""
        self._instance_registry.clear()
