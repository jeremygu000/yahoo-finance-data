"""Structured JSON logging configuration.

Two modes:
- JSON (default for server): machine-parseable, one JSON object per line
- Human (CLI): traditional %(asctime)s [%(levelname)s] format

Usage:
    from market_data.logging_config import setup_logging
    setup_logging()           # JSON mode (default)
    setup_logging(json=False) # Human-readable mode
"""

from __future__ import annotations

import json
import logging
import sys
import time
from typing import Any


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Merge extra structured fields (set via logger.info("msg", extra={...}))
        for key in (
            "request_id",
            "method",
            "path",
            "status_code",
            "latency_ms",
            "client_ip",
            "ticker",
            "provider",
            "error_type",
        ):
            val = getattr(record, key, None)
            if val is not None:
                log_entry[key] = val

        return json.dumps(log_entry, default=str)

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)) + f".{int(record.msecs):03d}Z"


HUMAN_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
HUMAN_DATEFMT = "%Y-%m-%d %H:%M:%S"


def setup_logging(*, json_format: bool = True, level: int = logging.INFO) -> None:
    """Configure root logger with JSON or human-readable format.

    Call once at application startup (server lifespan or CLI main).
    """
    root = logging.getLogger()

    # Clear existing handlers to avoid duplicate output
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stderr)
    if json_format:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter(HUMAN_FORMAT, datefmt=HUMAN_DATEFMT))

    root.addHandler(handler)
    root.setLevel(level)

    # Quiet noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("yfinance").setLevel(logging.WARNING)
