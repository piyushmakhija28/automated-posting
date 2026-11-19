"""Platform ports, adapter contracts, and registry factory package."""

from app.platforms.base import BasePlatformAdapter
from app.platforms.devto import DevToAdapter
from app.platforms.hashnode import HashnodeAdapter
from app.platforms.linkedin import LinkedInAdapter
from app.platforms.mastodon import MastodonAdapter
from app.platforms.registry import AdapterRegistry
from app.platforms.telegram import TelegramAdapter

__all__ = [
    "BasePlatformAdapter",
    "AdapterRegistry",
    "LinkedInAdapter",
    "DevToAdapter",
    "HashnodeAdapter",
    "MastodonAdapter",
    "TelegramAdapter",
]
