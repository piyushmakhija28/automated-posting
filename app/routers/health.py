"""Liveness and readiness SRE health probe routers."""

from datetime import UTC, datetime

from fastapi import APIRouter, status

from app.core.config import Settings
from app.core.constants import ApiConstants
from app.models.dtos.health_dto import AdapterStatusDto, HealthResponseDto, ReadinessResponseDto

router = APIRouter(tags=["Health & Probes"])


@router.get(
    ApiConstants.ENDPOINT_HEALTH,
    response_model=HealthResponseDto,
    status_code=status.HTTP_200_OK,
    summary="Liveness Probe",
    description="Returns HTTP 200 if the FastAPI application process and Uvicorn event loop are responsive.",
)
async def check_liveness() -> HealthResponseDto:
    """Evaluates process liveness for container orchestration and uptime monitoring.

    Returns:
        HealthResponseDto: Liveness status payload indicating healthy process loop.
    """
    return HealthResponseDto(
        status="ok",
        timestamp=datetime.now(UTC),
        version=ApiConstants.SERVICE_VERSION,
    )


@router.get(
    ApiConstants.ENDPOINT_READY,
    response_model=ReadinessResponseDto,
    status_code=status.HTTP_200_OK,
    summary="Readiness Probe",
    description="Returns HTTP 200 with adapter configuration status and connection pool readiness.",
)
async def check_readiness() -> ReadinessResponseDto:
    """Evaluates service readiness based on environment variable configuration.

    Returns:
        ReadinessResponseDto: Readiness telemetry detailing adapter credential availability.
    """
    settings = Settings()
    adapters_status = AdapterStatusDto(
        linkedin=bool(settings.linkedin_access_token and settings.linkedin_person_urn),
        devto=bool(settings.devto_api_key),
        hashnode=bool(settings.hashnode_api_key and settings.hashnode_publication_id),
        mastodon=bool(settings.mastodon_access_token and settings.mastodon_base_url),
        telegram=bool(settings.telegram_bot_token and settings.telegram_channel_id),
    )
    platforms_configured = (
        int(adapters_status.linkedin)
        + int(adapters_status.devto)
        + int(adapters_status.hashnode)
        + int(adapters_status.mastodon)
        + int(adapters_status.telegram)
    )

    return ReadinessResponseDto(
        status="ready",
        timestamp=datetime.now(UTC),
        version=ApiConstants.SERVICE_VERSION,
        platforms_configured=platforms_configured,
        adapters=adapters_status,
    )
