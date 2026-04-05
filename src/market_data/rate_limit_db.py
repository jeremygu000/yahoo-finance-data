"""SQLite-backed rate-limit quota and throttle state management.

DB location: ``~/.market_data/rate_limits.db`` (created lazily).
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from market_data.config import DATA_DIR

logger = logging.getLogger(__name__)

_DB_PATH = DATA_DIR.parent / "rate_limits.db"

_local = threading.local()


def _get_conn(db_path: Path | None = None) -> sqlite3.Connection:
    path = str(db_path or _DB_PATH)
    conn: sqlite3.Connection | None = getattr(_local, "conn", None)
    conn_path: str | None = getattr(_local, "conn_path", None)
    if conn is None or conn_path != path:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.row_factory = sqlite3.Row
        _local.conn = conn
        _local.conn_path = path
        _ensure_schema(conn)
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS api_quotas (
            source       TEXT    NOT NULL,
            window       TEXT    NOT NULL,   -- 'minute' | 'daily'
            max_calls    INTEGER NOT NULL,
            used         INTEGER NOT NULL DEFAULT 0,
            window_start TEXT    NOT NULL,   -- ISO-8601 timestamp
            PRIMARY KEY (source, window)
        );

        CREATE TABLE IF NOT EXISTS throttle_state (
            source          TEXT    NOT NULL PRIMARY KEY,
            consecutive_429 INTEGER NOT NULL DEFAULT 0,
            current_delay   REAL    NOT NULL DEFAULT 0.0,
            last_updated    TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS call_log (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            source    TEXT    NOT NULL,
            ticker    TEXT    NOT NULL DEFAULT '',
            endpoint  TEXT    NOT NULL DEFAULT '',
            status    TEXT    NOT NULL DEFAULT 'ok',  -- 'ok' | 'rate_limited' | 'error'
            timestamp TEXT    NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_call_log_source_ts
            ON call_log(source, timestamp);
        """)
    conn.commit()


def close_connection() -> None:
    conn: sqlite3.Connection | None = getattr(_local, "conn", None)
    if conn is not None:
        conn.close()
        _local.conn = None
        _local.conn_path = None


def _current_window_start(window: str) -> str:
    now = datetime.now(timezone.utc)
    if window == "daily":
        return now.strftime("%Y-%m-%d")
    return now.strftime("%Y-%m-%dT%H:%M")


def ensure_quota(source: str, window: str, max_calls: int, db_path: Path | None = None) -> None:
    conn = _get_conn(db_path)
    ws = _current_window_start(window)
    row = conn.execute(
        "SELECT window_start, used FROM api_quotas WHERE source=? AND window=?",
        (source, window),
    ).fetchone()

    if row is None:
        conn.execute(
            "INSERT INTO api_quotas (source, window, max_calls, used, window_start) VALUES (?,?,?,0,?)",
            (source, window, max_calls, ws),
        )
    elif row["window_start"] != ws:
        conn.execute(
            "UPDATE api_quotas SET used=0, window_start=?, max_calls=? WHERE source=? AND window=?",
            (ws, max_calls, source, window),
        )
    else:
        conn.execute(
            "UPDATE api_quotas SET max_calls=? WHERE source=? AND window=?",
            (max_calls, source, window),
        )
    conn.commit()


def try_consume(source: str, window: str, count: int = 1, db_path: Path | None = None) -> bool:
    """Returns True if quota allows the request, False if exhausted."""
    conn = _get_conn(db_path)
    ws = _current_window_start(window)
    row = conn.execute(
        "SELECT max_calls, used, window_start FROM api_quotas WHERE source=? AND window=?",
        (source, window),
    ).fetchone()

    if row is None:
        return True

    if row["window_start"] != ws:
        conn.execute(
            "UPDATE api_quotas SET used=?, window_start=? WHERE source=? AND window=?",
            (count, ws, source, window),
        )
        conn.commit()
        return True

    if row["used"] + count > row["max_calls"]:
        return False

    conn.execute(
        "UPDATE api_quotas SET used=used+? WHERE source=? AND window=?",
        (count, source, window),
    )
    conn.commit()
    return True


def get_quota_usage(source: str, window: str, db_path: Path | None = None) -> dict[str, Any]:
    conn = _get_conn(db_path)
    ws = _current_window_start(window)
    row = conn.execute(
        "SELECT max_calls, used, window_start FROM api_quotas WHERE source=? AND window=?",
        (source, window),
    ).fetchone()

    if row is None:
        return {"source": source, "window": window, "max_calls": 0, "used": 0, "remaining": 0}

    used = row["used"] if row["window_start"] == ws else 0
    max_calls: int = row["max_calls"]
    return {
        "source": source,
        "window": window,
        "max_calls": max_calls,
        "used": used,
        "remaining": max_calls - used,
    }


_THROTTLE_BASE: float = 5.0
_THROTTLE_MAX: float = 120.0


def get_throttle(source: str, db_path: Path | None = None) -> dict[str, Any]:
    conn = _get_conn(db_path)
    row = conn.execute(
        "SELECT consecutive_429, current_delay, last_updated FROM throttle_state WHERE source=?",
        (source,),
    ).fetchone()
    if row is None:
        return {"source": source, "consecutive_429": 0, "current_delay": 0.0}
    return {
        "source": source,
        "consecutive_429": row["consecutive_429"],
        "current_delay": row["current_delay"],
    }


def record_rate_limit(source: str, db_path: Path | None = None) -> float:
    conn = _get_conn(db_path)
    now = datetime.now(timezone.utc).isoformat()
    row = conn.execute("SELECT consecutive_429 FROM throttle_state WHERE source=?", (source,)).fetchone()

    if row is None:
        consecutive = 1
        delay = _THROTTLE_BASE
        conn.execute(
            "INSERT INTO throttle_state (source, consecutive_429, current_delay, last_updated) VALUES (?,?,?,?)",
            (source, consecutive, delay, now),
        )
    else:
        consecutive = row["consecutive_429"] + 1
        delay = min(_THROTTLE_BASE * (2 ** (consecutive - 1)), _THROTTLE_MAX)
        conn.execute(
            "UPDATE throttle_state SET consecutive_429=?, current_delay=?, last_updated=? WHERE source=?",
            (consecutive, delay, now, source),
        )

    conn.commit()
    logger.warning("Rate-limit hit #%d for %s — delay now %.1fs", consecutive, source, delay)
    return delay


def record_success(source: str, db_path: Path | None = None) -> None:
    conn = _get_conn(db_path)
    now = datetime.now(timezone.utc).isoformat()
    row = conn.execute("SELECT consecutive_429 FROM throttle_state WHERE source=?", (source,)).fetchone()

    if row is None or row["consecutive_429"] == 0:
        return

    consecutive = max(0, row["consecutive_429"] - 1)
    if consecutive == 0:
        delay = 0.0
    else:
        delay = min(_THROTTLE_BASE * (2 ** (consecutive - 1)), _THROTTLE_MAX)

    conn.execute(
        "UPDATE throttle_state SET consecutive_429=?, current_delay=?, last_updated=? WHERE source=?",
        (consecutive, delay, now, source),
    )
    conn.commit()


def reset_throttle(source: str, db_path: Path | None = None) -> None:
    conn = _get_conn(db_path)
    conn.execute("DELETE FROM throttle_state WHERE source=?", (source,))
    conn.commit()


def log_call(
    source: str,
    *,
    ticker: str = "",
    endpoint: str = "",
    status: str = "ok",
    db_path: Path | None = None,
) -> None:
    conn = _get_conn(db_path)
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO call_log (source, ticker, endpoint, status, timestamp) VALUES (?,?,?,?,?)",
        (source, ticker, endpoint, status, now),
    )
    conn.commit()


def get_call_count(
    source: str, *, since: str | None = None, status: str | None = None, db_path: Path | None = None
) -> int:
    conn = _get_conn(db_path)
    sql = "SELECT COUNT(*) FROM call_log WHERE source=?"
    params: list[str] = [source]
    if since:
        sql += " AND timestamp>=?"
        params.append(since)
    if status:
        sql += " AND status=?"
        params.append(status)
    row = conn.execute(sql, params).fetchone()
    return int(row[0]) if row else 0


def reset_all(db_path: Path | None = None) -> None:
    conn = _get_conn(db_path)
    conn.executescript("""
        DELETE FROM api_quotas;
        DELETE FROM throttle_state;
        DELETE FROM call_log;
        """)
    conn.commit()
