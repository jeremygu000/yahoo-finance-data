"""DuckDB-based read layer for batch Parquet operations.

Provides high-performance glob-scan queries across all ticker Parquet files.
Used as a read-only complement to the existing pandas write path in store.py.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

import duckdb
import pandas as pd

from market_data.config import DATA_DIR, VALID_INTERVALS

logger = logging.getLogger(__name__)

_local = threading.local()


def _get_conn(data_dir: Path = DATA_DIR) -> duckdb.DuckDBPyConnection:
    """Return a thread-local in-memory DuckDB connection."""
    conn: duckdb.DuckDBPyConnection | None = getattr(_local, "conn", None)
    if conn is None:
        conn = duckdb.connect(":memory:")
        _local.conn = conn
    return conn


def _glob_pattern(data_dir: Path, interval: str | None = None) -> str:
    if interval:
        return str(data_dir / f"*_{interval}.parquet")
    return str(data_dir / "*.parquet")


def _parse_ticker_from_filename(filename: str) -> tuple[str, str]:
    """Extract (ticker, interval) from a Parquet filename stem.

    Examples:
        'AAPL_1d' -> ('AAPL', '1d')
        'AAPL_1h' -> ('AAPL', '1h')
        'AAPL' -> ('AAPL', '1d')  # legacy
    """
    stem = Path(filename).stem
    parts = stem.rsplit("_", 1)
    if len(parts) == 2 and parts[1] in VALID_INTERVALS:
        return parts[0], parts[1]
    return stem, "1d"


def batch_status(data_dir: Path = DATA_DIR) -> list[dict[str, object]]:
    """Get status for all tickers using a single DuckDB glob scan.

    Replaces the N+1 pd.read_parquet loop in store.status().
    Reads all Parquet files at once, computes min/max dates and row counts.
    """
    pattern = _glob_pattern(data_dir)
    if not data_dir.exists() or not list(data_dir.glob("*.parquet")):
        return []

    conn = _get_conn(data_dir)
    try:
        result = conn.execute(
            """
            SELECT
                filename,
                COUNT(*) AS rows,
                MIN("Date") AS first_date,
                MAX("Date") AS last_date
            FROM read_parquet(?, filename=true, hive_partitioning=false)
            GROUP BY filename
            ORDER BY filename
            """,
            [pattern],
        ).fetchall()
    except duckdb.IOException:
        logger.warning("DuckDB glob scan failed, falling back to empty result")
        return []

    items: list[dict[str, object]] = []
    for filename, rows, first_dt, last_dt in result:
        ticker, interval = _parse_ticker_from_filename(filename)
        fpath = Path(filename)
        size_kb = round(fpath.stat().st_size / 1024, 1) if fpath.exists() else 0.0

        items.append(
            {
                "ticker": ticker,
                "interval": interval,
                "rows": rows,
                "first_date": pd.Timestamp(first_dt).date().isoformat(),
                "last_date": pd.Timestamp(last_dt).date().isoformat(),
                "size_kb": size_kb,
            }
        )
    return items


def batch_status_paginated(
    page: int = 1,
    page_size: int = 24,
    search: str = "",
    data_dir: Path = DATA_DIR,
) -> dict[str, object]:
    """Paginated ticker overview with latest quote, powered by DuckDB.

    Phase 1: DuckDB glob scan for all metadata (single query).
    Phase 2: DuckDB reads only the page slice for latest quote data.
    """
    if not data_dir.exists() or not list(data_dir.glob("*.parquet")):
        return {"items": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 0}

    pattern = _glob_pattern(data_dir)
    conn = _get_conn(data_dir)

    # Phase 1: Get all ticker metadata with a single scan
    try:
        all_rows = conn.execute(
            """
            SELECT
                filename,
                COUNT(*) AS rows,
                MIN("Date") AS first_date,
                MAX("Date") AS last_date
            FROM read_parquet(?, filename=true, hive_partitioning=false)
            GROUP BY filename
            ORDER BY filename
            """,
            [pattern],
        ).fetchall()
    except duckdb.IOException:
        return {"items": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 0}

    # Parse and optionally filter
    entries: list[tuple[str, str, str, int, str, str]] = []  # (ticker, interval, filename, rows, first, last)
    for filename, rows, first_dt, last_dt in all_rows:
        ticker, interval = _parse_ticker_from_filename(filename)
        if search and search.upper() not in ticker.upper():
            continue
        entries.append((
            ticker,
            interval,
            filename,
            rows,
            pd.Timestamp(first_dt).date().isoformat(),
            pd.Timestamp(last_dt).date().isoformat(),
        ))

    total = len(entries)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    start = (page - 1) * page_size
    page_entries = entries[start : start + page_size]

    if not page_entries:
        return {"items": [], "total": total, "page": page, "page_size": page_size, "total_pages": total_pages}

    items: list[dict[str, object]] = []
    for ticker, interval, filename, row_count, first_date, last_date in page_entries:
        fpath = Path(filename)
        size_kb = round(fpath.stat().st_size / 1024, 1) if fpath.exists() else 0.0

        latest: dict[str, object] | None = None
        change: float | None = None
        change_pct: float | None = None

        try:
            last_row = conn.execute(
                """
                SELECT "Date", "Open", "High", "Low", "Close", "Volume"
                FROM read_parquet(?, hive_partitioning=false)
                ORDER BY "Date" DESC
                LIMIT 1
                """,
                [filename],
            ).fetchone()

            if last_row:
                dt, open_val, high_val, low_val, close_val, volume = last_row
                open_f = float(open_val)
                close_f = float(close_val)
                latest = {
                    "date": pd.Timestamp(dt).date().isoformat(),
                    "open": open_f,
                    "high": float(high_val),
                    "low": float(low_val),
                    "close": close_f,
                    "volume": int(volume),
                }
                if open_f != 0:
                    change = round(close_f - open_f, 4)
                    change_pct = round(((close_f - open_f) / open_f) * 100, 4)
        except duckdb.IOException:
            pass

        items.append(
            {
                "ticker": ticker,
                "interval": interval,
                "rows": row_count,
                "first_date": first_date,
                "last_date": last_date,
                "size_kb": size_kb,
                "latest": latest,
                "change": change,
                "change_pct": change_pct,
            }
        )

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


def batch_latest(
    tickers: list[str],
    data_dir: Path = DATA_DIR,
    interval: str = "1d",
) -> dict[str, dict[str, object]]:
    """Get the latest OHLCV row for multiple tickers in a single query.

    Replaces the N+1 loop in _poll_prices() and portfolio_summary.
    Returns {ticker: {date, open, high, low, close, volume}} for each found ticker.
    """
    if not tickers or not data_dir.exists():
        return {}

    from market_data.store import validate_ticker

    existing_files: list[tuple[str, str]] = []
    for t in tickers:
        try:
            safe = validate_ticker(t)
        except Exception:
            continue
        fpath = data_dir / f"{safe}_{interval}.parquet"
        if fpath.exists():
            existing_files.append((t, str(fpath)))

    if not existing_files:
        return {}

    conn = _get_conn(data_dir)
    result: dict[str, dict[str, object]] = {}

    for ticker, filepath in existing_files:
        try:
            row = conn.execute(
                """
                SELECT "Date", "Open", "High", "Low", "Close", "Volume"
                FROM read_parquet(?, hive_partitioning=false)
                ORDER BY "Date" DESC
                LIMIT 1
                """,
                [filepath],
            ).fetchone()
            if row:
                dt, open_val, high_val, low_val, close_val, volume = row
                result[ticker] = {
                    "date": pd.Timestamp(dt).date().isoformat(),
                    "open": float(open_val),
                    "high": float(high_val),
                    "low": float(low_val),
                    "close": float(close_val),
                    "volume": int(volume),
                }
        except duckdb.IOException:
            logger.debug("Failed to read latest for %s", ticker)

    return result


def batch_load(
    tickers: list[str],
    days: int | None = None,
    data_dir: Path = DATA_DIR,
    interval: str = "1d",
    columns: list[str] | None = None,
) -> dict[str, pd.DataFrame]:
    """Load OHLCV data for multiple tickers, returning {ticker: DataFrame}.

    Replaces sequential store.load() loops in build_prompt() and /compare.
    """
    if not tickers or not data_dir.exists():
        return {}

    from market_data.store import validate_ticker

    existing_files: list[tuple[str, str]] = []
    for t in tickers:
        try:
            safe = validate_ticker(t)
        except Exception:
            continue
        fpath = data_dir / f"{safe}_{interval}.parquet"
        if fpath.exists():
            existing_files.append((t, str(fpath)))

    if not existing_files:
        return {}

    conn = _get_conn(data_dir)
    result: dict[str, pd.DataFrame] = {}

    col_clause = ", ".join(f'"{c}"' for c in columns) if columns else "*"

    cutoff_clause = ""
    params_extra: list[object] = []
    if days is not None:
        cutoff = pd.Timestamp.now().normalize() - pd.Timedelta(days=days)
        cutoff_clause = 'WHERE "Date" >= ?'
        params_extra = [cutoff]

    for ticker, filepath in existing_files:
        try:
            df = conn.execute(
                f"""
                SELECT {col_clause}
                FROM read_parquet(?, hive_partitioning=false)
                {cutoff_clause}
                ORDER BY "Date"
                """,
                [filepath] + params_extra,
            ).df()

            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"])
                df.set_index("Date", inplace=True)

            result[ticker] = df
        except duckdb.IOException:
            logger.debug("Failed to load %s", ticker)

    return result


def compare_close(
    tickers: list[str],
    days: int = 90,
    data_dir: Path = DATA_DIR,
    interval: str = "1d",
) -> dict[str, pd.DataFrame]:
    """Load Close price data for multiple tickers (optimized for /compare).

    Uses column projection to only read Date and Close columns.
    """
    return batch_load(tickers, days=days, data_dir=data_dir, interval=interval, columns=["Date", "Close"])
