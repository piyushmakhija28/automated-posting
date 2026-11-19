"""HTTP ingress router for the /posting multi-platform broadcast endpoint."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Response, status

from app.core.constants import ApiConstants
from app.core.logging import correlation_id_ctx
from app.models.dtos.posting_dto import PostingResponseDto
from app.models.forms.posting_form import PostingForm
from app.services.posting_service import PostingService

router = APIRouter(tags=["Posting"])


def get_posting_service() -> PostingService:
    """FastAPI dependency provider for PostingService instance.

    Raises:
        NotImplementedError: If invoked directly without application runtime override.
    """
    raise NotImplementedError("Dependency injection provider must be bound at startup.")


@router.post(
    ApiConstants.ENDPOINT_POSTING,
    response_model=PostingResponseDto,
    status_code=status.HTTP_200_OK,
    summary="Broadcast message across 5 platforms concurrently",
    description=(
        "Accepts a promotional message (max 200 characters, exactly 1 CTA link) "
        "and executes concurrent asynchronous publishing to LinkedIn, Dev.to, "
        "Hashnode, Mastodon, and Telegram via non-blocking httpx.AsyncClient."
    ),
)
async def broadcast_post(
    form: PostingForm,
    response: Response,
    service: Annotated[PostingService, Depends(get_posting_service)],
    x_correlation_id: Annotated[str | None, Header(alias=ApiConstants.HEADER_CORRELATION_ID)] = None,
    x_request_id: Annotated[str | None, Header(alias=ApiConstants.HEADER_REQUEST_ID)] = None,
) -> PostingResponseDto:
    """Handles HTTP POST /posting request, invokes service orchestrator, and populates headers.

    Args:
        form: Ingress validated form payload containing broadcast copy and extracted CTA link.
        response: FastAPI response object for setting tracing and latency headers.
        service: Injected PostingService orchestrator instance.
        x_correlation_id: Client-supplied tracing identifier (X-Correlation-ID).
        x_request_id: Client-supplied distributed tracing UUID (X-Request-ID).

    Returns:
        PostingResponseDto: Consolidated multi-platform execution outcome.
    """
    correlation_id = x_correlation_id or x_request_id or str(uuid.uuid4())
    correlation_id_ctx.set(correlation_id)

    result = await service.broadcast(form=form, correlation_id=correlation_id)

    response.headers[ApiConstants.HEADER_CORRELATION_ID] = correlation_id
    response.headers[ApiConstants.HEADER_REQUEST_ID] = correlation_id

    if result.execution_time_seconds is not None:
        response.headers[ApiConstants.HEADER_TOTAL_LATENCY] = str(
            round(result.execution_time_seconds * 1000.0, 2)
        )
        response.headers["X-Process-Time"] = str(round(result.execution_time_seconds, 4))
    elif result.telemetry is not None:
        response.headers[ApiConstants.HEADER_TOTAL_LATENCY] = str(
            round(result.telemetry.total_latency_ms, 2)
        )
        response.headers["X-Process-Time"] = str(
            round(result.telemetry.total_latency_ms / 1000.0, 4)
        )

    return result
