from __future__ import annotations

import json
import logging
import sys
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any


class JSONFormatter(logging.Formatter):

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

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

# 10 MB per file, keep 5 rotated files = 60 MB max
_LOG_MAX_BYTES = 10 * 1024 * 1024
_LOG_BACKUP_COUNT = 5


def setup_logging(
    *,
    json_format: bool = True,
    level: int = logging.INFO,
    log_dir: Path | None = None,
) -> None:
    root = logging.getLogger()
    root.handlers.clear()

    stderr_handler = logging.StreamHandler(sys.stderr)
    if json_format:
        stderr_handler.setFormatter(JSONFormatter())
    else:
        stderr_handler.setFormatter(logging.Formatter(HUMAN_FORMAT, datefmt=HUMAN_DATEFMT))
    root.addHandler(stderr_handler)

    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_dir / "market_data.log",
            maxBytes=_LOG_MAX_BYTES,
            backupCount=_LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(JSONFormatter())
        root.addHandler(file_handler)

    root.setLevel(level)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("yfinance").setLevel(logging.WARNING)
