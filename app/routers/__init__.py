"""Ingress routers package for API endpoints and SRE health probes."""

from app.routers.health import router as health_router
from app.routers.posting import router as posting_router

__all__ = [
    "health_router",
    "posting_router",
]
