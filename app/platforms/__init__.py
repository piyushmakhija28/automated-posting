"""Platform ports, adapter contracts, and registry factory package."""

from app.platforms.base import BasePlatformAdapter
from app.platforms.registry import AdapterRegistry

__all__ = [
    "BasePlatformAdapter",
    "AdapterRegistry",
]
