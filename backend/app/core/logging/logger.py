"""Structured application logging for CurrencyHub."""

from datetime import datetime, timezone
import json
import logging
import sys
from typing import Any

from app.core.config.settings import Settings, get_settings


class StructuredFormatter(logging.Formatter):
    """Format log records with ISO-8601 timestamps and structured context."""

    _STANDARD_ATTRS = {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "message",
    }

    def __init__(self, json_format: bool = False) -> None:
        super().__init__()
        self.json_format = json_format

    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()
        timestamp = datetime.now(timezone.utc).isoformat()

        # Extract extra structured fields
        extra_fields: dict[str, Any] = {
            key: value
            for key, value in record.__dict__.items()
            if key not in self._STANDARD_ATTRS and not key.startswith("_")
        }

        if self.json_format:
            log_data: dict[str, Any] = {
                "timestamp": timestamp,
                "level": record.levelname,
                "logger": record.name,
                "message": record.message,
            }
            if extra_fields:
                log_data["extra"] = extra_fields
            if record.exc_info:
                log_data["exception"] = self.formatException(record.exc_info)
            return json.dumps(log_data)

        # Structured readable text format
        extra_str = ""
        if extra_fields:
            kv_pairs = [f"{k}={v}" for k, v in sorted(extra_fields.items())]
            extra_str = f" [{', '.join(kv_pairs)}]"

        msg = f"{timestamp} [{record.levelname:<5}] {record.name}: {record.message}{extra_str}"
        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
            msg = f"{msg}\n{record.exc_text}"
        return msg


def configure_logging(settings: Settings | None = None, json_format: bool = False) -> None:
    """Configure application logging using settings.

    Args:
        settings: Application settings instance; loads default settings if None.
        json_format: Whether to output logs in JSON format instead of structured text.
    """
    app_settings = settings or get_settings()
    log_level = getattr(logging, app_settings.log_level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    formatter = StructuredFormatter(json_format=json_format)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    handler.setFormatter(formatter)

    # Replace existing handlers to avoid duplicates
    for existing_handler in list(root_logger.handlers):
        root_logger.removeHandler(existing_handler)

    root_logger.addHandler(handler)


def get_logger(name: str = "currencyhub") -> logging.Logger:
    """Return a logger instance configured for the application."""
    return logging.getLogger(name)
