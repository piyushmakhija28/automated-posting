"""Generic API response envelope wrapper."""

from datetime import UTC, datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ApiResponseDto(BaseModel, Generic[T]):
    """Unified API response envelope with status, message, data, and timestamp."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    success: bool = Field(..., description="True if operation succeeded without critical error.")
    status: int = Field(..., description="HTTP status code corresponding to outcome.")
    message: str = Field(..., description="Human-readable response message.")
    data: T | None = Field(default=None, description="Typed response payload.")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
