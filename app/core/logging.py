"""Centralized structured logging with credential filtering and context propagation."""

import json
import logging
import re
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

correlation_id_ctx: ContextVar[str | None] = ContextVar("correlation_id", default=None)


class SensitiveDataFilter(logging.Filter):
    """Masks secret tokens, API keys, and authorization headers in log output."""

    SENSITIVE_PATTERNS = [
        re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.]{8,}", re.IGNORECASE),
        re.compile(r"(api[-_]?key[\"'\s:=]+)[A-Za-z0-9_\-\.]{8,}", re.IGNORECASE),
        re.compile(r"(bot[0-9]{8,10}:)[A-Za-z0-9_\-]{25,}", re.IGNORECASE),
        re.compile(r"(access[-_]?token[\"'\s:=]+)[A-Za-z0-9_\-\.]{8,}", re.IGNORECASE),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """Inspects and masks sensitive tokens within log record messages and arguments."""
        if isinstance(record.msg, str):
            for pattern in self.SENSITIVE_PATTERNS:
                record.msg = pattern.sub(r"\1[REDACTED]", record.msg)
        return True


class StructuredJsonFormatter(logging.Formatter):
    """Outputs standardized JSON logs formatted for ELK / Datadog ingestion."""

    def format(self, record: logging.LogRecord) -> str:
        """Serializes the log record to a single-line JSON string."""
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id_ctx.get(),
            "source": f"{record.filename}:{record.lineno}",
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


def setup_logging(log_level: str = "INFO") -> None:
    """Configures the root and application loggers with handlers and filters."""
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredJsonFormatter())
    handler.addFilter(SensitiveDataFilter())
    root_logger.handlers = [handler]
