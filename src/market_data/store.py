from __future__ import annotations

import logging
import re
import tempfile
from datetime import date
from pathlib import Path

import pandas as pd

from market_data.cache import InMemoryCache
from market_data.config import CACHE_MAX_ENTRIES, CACHE_TTL_SECONDS, DATA_DIR, VALID_INTERVALS
from market_data.exceptions import InvalidTickerError

logger = logging.getLogger(__name__)

_cache = InMemoryCache(ttl_seconds=CACHE_TTL_SECONDS, max_entries=CACHE_MAX_ENTRIES)

_TICKER_PATTERN = re.compile(r"^[\w\^./\\=\-]{1,20}$")


def validate_ticker(ticker: str) -> str:
    if not ticker or not ticker.strip():
        raise InvalidTickerError(ticker, "Ticker symbol cannot be empty")

    ticker = ticker.strip()

    if not _TICKER_PATTERN.match(ticker):
        raise InvalidTickerError(ticker, "Only alphanumeric, ^, -, ., /, = characters allowed (max 20 chars).")

    return _sanitize_ticker(ticker)


def _sanitize_ticker(ticker: str) -> str:
    return ticker.replace("^", "").replace("/", "_").replace("\\", "_").replace("=", "_").upper()


def _parquet_path(ticker: str, interval: str = "1d", data_dir: Path = DATA_DIR) -> Path:
    safe_name = validate_ticker(ticker)
    new_path = (data_dir / f"{safe_name}_{interval}.parquet").resolve()

    if not str(new_path).startswith(str(data_dir.resolve())):
        raise InvalidTickerError(ticker, "Path traversal detected")

    if not new_path.exists() and interval == "1d":
        legacy_path = (data_dir / f"{safe_name}.parquet").resolve()
        if legacy_path.exists():
            legacy_path.rename(new_path)

    return new_path


def invalidate_cache(ticker: str | None = None) -> None:
    if ticker is None:
        _cache.clear()
    else:
        safe = validate_ticker(ticker)
        _cache.delete_prefix(safe + ":")


def save(ticker: str, df: pd.DataFrame, data_dir: Path = DATA_DIR, interval: str = "1d") -> int:
    data_dir.mkdir(parents=True, exist_ok=True)
    path = _parquet_path(ticker, interval=interval, data_dir=data_dir)

    if path.exists():
        existing = pd.read_parquet(path)
        rows_before = len(existing)
        combined = pd.concat([existing, df])
    else:
        rows_before = 0
        combined = df.copy()

    combined = combined[~combined.index.duplicated(keep="last")]
    combined.sort_index(inplace=True)

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


def load(ticker: str, days: int | None = None, data_dir: Path = DATA_DIR, interval: str = "1d") -> pd.DataFrame:
    path = _parquet_path(ticker, interval=interval, data_dir=data_dir)
    if not path.exists():
        logger.warning("%s: no local data at %s", ticker, path)
        return pd.DataFrame()

    safe = validate_ticker(ticker)
    cache_key = f"{safe}:{interval}:{data_dir}"

    cached: pd.DataFrame | None = _cache.get(cache_key)
    if cached is not None:
        df = cached
    else:
        df = pd.read_parquet(path)
        _cache.set(cache_key, df)

    if days is not None:
        cutoff = pd.Timestamp(date.today()) - pd.Timedelta(days=days)
        df = df[df.index >= cutoff]

    return df


def last_date(ticker: str, data_dir: Path = DATA_DIR, interval: str = "1d") -> date | None:
    path = _parquet_path(ticker, interval=interval, data_dir=data_dir)
    if not path.exists():
        return None

    df = pd.read_parquet(path, columns=["Close"])
    if df.empty:
        return None

    ts: pd.Timestamp = df.index.max()
    return ts.date()


def list_tickers(data_dir: Path = DATA_DIR) -> list[str]:
    if not data_dir.exists():
        return []

    tickers: set[str] = set()
    for p in data_dir.glob("*.parquet"):
        stem = p.stem
        parts = stem.rsplit("_", 1)
        if len(parts) == 2 and parts[1] in VALID_INTERVALS:
            tickers.add(parts[0])
        else:
            tickers.add(stem)
    return sorted(tickers)


def status(data_dir: Path = DATA_DIR) -> list[dict[str, object]]:
    from market_data.duckdb_reader import batch_status

    return batch_status(data_dir=data_dir)


def status_paginated(
    page: int = 1,
    page_size: int = 24,
    search: str = "",
    data_dir: Path = DATA_DIR,
) -> dict[str, object]:
    from market_data.duckdb_reader import batch_status_paginated

    return batch_status_paginated(page=page, page_size=page_size, search=search, data_dir=data_dir)


def clean(keep_days: int = 365, data_dir: Path = DATA_DIR) -> dict[str, int]:
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


def delete_ticker(ticker: str, data_dir: Path = DATA_DIR) -> int:
    """Delete all Parquet files for a ticker. Returns number of files removed."""
    safe = validate_ticker(ticker)
    removed = 0
    for path in sorted(data_dir.glob(f"{safe}*.parquet")):
        stem = path.stem
        parts = stem.rsplit("_", 1)
        if len(parts) == 2 and parts[0] == safe and parts[1] in VALID_INTERVALS:
            path.unlink()
            removed += 1
        elif stem == safe:
            path.unlink()
            removed += 1
    invalidate_cache(ticker)
    logger.info("%s: deleted %d file(s)", safe, removed)
    return removed


def storage_summary(data_dir: Path = DATA_DIR) -> dict[str, object]:
    """Return aggregate storage statistics."""
    if not data_dir.exists():
        return {
            "total_files": 0,
            "total_size_kb": 0.0,
            "total_rows": 0,
            "ticker_count": 0,
            "oldest_date": None,
            "newest_date": None,
        }

    items = status(data_dir)
    total_files = len(items)
    total_size_kb = sum(float(str(it.get("size_kb", 0))) for it in items)
    total_rows = sum(int(str(it.get("rows", 0))) for it in items)
    tickers: set[str] = {str(it["ticker"]) for it in items}

    first_dates = [str(it["first_date"]) for it in items if it.get("first_date")]
    last_dates = [str(it["last_date"]) for it in items if it.get("last_date")]
    oldest = min(first_dates) if first_dates else None
    newest = max(last_dates) if last_dates else None

    return {
        "total_files": total_files,
        "total_size_kb": round(total_size_kb, 2),
        "total_rows": total_rows,
        "ticker_count": len(tickers),
        "oldest_date": oldest,
        "newest_date": newest,
    }
