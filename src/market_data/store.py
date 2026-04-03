"""Parquet store: ~/.market_data/parquet/{TICKER}.parquet

Ticker sanitization: "^VIX" -> "VIX", "/" -> "_".
"""

from __future__ import annotations

import logging
import re
import tempfile
import threading
import time
from datetime import date
from pathlib import Path

import pandas as pd

from market_data.config import DATA_DIR
from market_data.exceptions import InvalidTickerError

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 60
_cache: dict[str, tuple[float, pd.DataFrame]] = {}
_cache_lock = threading.Lock()

# Alphanumeric, ^, -, ., / (caret for ^VIX, slash for BRK/B, dot for BRK.B)
_TICKER_PATTERN = re.compile(r"^[\w\^./\\-]{1,20}$")


def validate_ticker(ticker: str) -> str:
    """Validate and sanitize a ticker symbol.

    Raises InvalidTickerError for empty, too long, or invalid-character tickers.
    Returns the sanitized (uppercase, safe-for-filename) ticker.
    """
    if not ticker or not ticker.strip():
        raise InvalidTickerError(ticker, "Ticker symbol cannot be empty")

    ticker = ticker.strip()

    if not _TICKER_PATTERN.match(ticker):
        raise InvalidTickerError(ticker, "Only alphanumeric, ^, -, ., / characters allowed (max 20 chars).")

    return _sanitize_ticker(ticker)


def _sanitize_ticker(ticker: str) -> str:
    return ticker.replace("^", "").replace("/", "_").replace("\\", "_").upper()


def _parquet_path(ticker: str, data_dir: Path = DATA_DIR) -> Path:
    safe_name = validate_ticker(ticker)
    path = (data_dir / f"{safe_name}.parquet").resolve()

    # Path traversal defense: ensure resolved path is inside data_dir
    if not str(path).startswith(str(data_dir.resolve())):
        raise InvalidTickerError(ticker, "Path traversal detected")

    return path


def invalidate_cache(ticker: str | None = None) -> None:
    """Clear cached DataFrames. Pass ticker to clear one, or None to clear all."""
    with _cache_lock:
        if ticker is None:
            _cache.clear()
        else:
            safe = validate_ticker(ticker)
            keys = [k for k in _cache if k.startswith(safe + ":")]
            for k in keys:
                del _cache[k]


def save(ticker: str, df: pd.DataFrame, data_dir: Path = DATA_DIR) -> int:
    """Append-save DataFrame to parquet, deduplicating by date. Returns new row count."""
    data_dir.mkdir(parents=True, exist_ok=True)
    path = _parquet_path(ticker, data_dir)

    if path.exists():
        existing = pd.read_parquet(path)
        rows_before = len(existing)
        combined = pd.concat([existing, df])
    else:
        rows_before = 0
        combined = df.copy()

    combined = combined[~combined.index.duplicated(keep="last")]
    combined.sort_index(inplace=True)

    # Atomic write: write to temp file then rename to avoid partial writes
    tmp_fd, tmp_path = tempfile.mkstemp(dir=data_dir, suffix=".parquet.tmp")
    try:
        import os

        os.close(tmp_fd)
        combined.to_parquet(tmp_path, engine="pyarrow")
        Path(tmp_path).replace(path)
    except BaseException:
        Path(tmp_path).unlink(missing_ok=True)
        raise

    invalidate_cache(ticker)
    rows_added = len(combined) - rows_before
    logger.info("%s: saved %d rows (total %d)", ticker, rows_added, len(combined))
    return rows_added


def load(ticker: str, days: int | None = None, data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Load OHLCV data from local parquet. Returns empty DataFrame if not found."""
    path = _parquet_path(ticker, data_dir)
    if not path.exists():
        logger.warning("%s: no local data at %s", ticker, path)
        return pd.DataFrame()

    safe = validate_ticker(ticker)
    cache_key = f"{safe}:{data_dir}"

    with _cache_lock:
        if cache_key in _cache:
            ts, cached_df = _cache[cache_key]
            if time.monotonic() - ts < CACHE_TTL_SECONDS:
                df = cached_df
            else:
                del _cache[cache_key]
                df = pd.read_parquet(path)
                _cache[cache_key] = (time.monotonic(), df)
        else:
            df = pd.read_parquet(path)
            _cache[cache_key] = (time.monotonic(), df)

    if days is not None:
        cutoff = pd.Timestamp(date.today()) - pd.Timedelta(days=days)
        df = df[df.index >= cutoff]

    return df


def last_date(ticker: str, data_dir: Path = DATA_DIR) -> date | None:
    """Most recent date in stored data, or None."""
    path = _parquet_path(ticker, data_dir)
    if not path.exists():
        return None

    df = pd.read_parquet(path, columns=["Close"])
    if df.empty:
        return None

    ts: pd.Timestamp = df.index.max()
    return ts.date()


def list_tickers(data_dir: Path = DATA_DIR) -> list[str]:
    """All ticker names with stored data."""
    if not data_dir.exists():
        return []
    return sorted(p.stem for p in data_dir.glob("*.parquet"))


def status(data_dir: Path = DATA_DIR) -> list[dict[str, object]]:
    """Status info for all cached tickers: ticker, rows, first_date, last_date, size_kb."""
    if not data_dir.exists():
        return []

    result = []
    for path in sorted(data_dir.glob("*.parquet")):
        df = pd.read_parquet(path)
        if df.empty:
            continue
        result.append(
            {
                "ticker": path.stem,
                "rows": len(df),
                "first_date": df.index.min().date().isoformat(),
                "last_date": df.index.max().date().isoformat(),
                "size_kb": round(path.stat().st_size / 1024, 1),
            }
        )
    return result


def clean(keep_days: int = 365, data_dir: Path = DATA_DIR) -> dict[str, int]:
    """Remove data older than keep_days. Returns {ticker: rows_removed}."""
    if not data_dir.exists():
        return {}

    cutoff = pd.Timestamp(date.today()) - pd.Timedelta(days=keep_days)
    removed: dict[str, int] = {}

    for path in sorted(data_dir.glob("*.parquet")):
        df = pd.read_parquet(path)
        original_len = len(df)
        df = df[df.index >= cutoff]

        if len(df) < original_len:
            removed[path.stem] = original_len - len(df)
            df.to_parquet(path, engine="pyarrow")

    return removed
