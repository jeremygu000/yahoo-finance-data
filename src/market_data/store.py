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

_TICKER_PATTERN = re.compile(r"^[\w\^./\\-]{1,20}$")


def validate_ticker(ticker: str) -> str:
    if not ticker or not ticker.strip():
        raise InvalidTickerError(ticker, "Ticker symbol cannot be empty")

    ticker = ticker.strip()

    if not _TICKER_PATTERN.match(ticker):
        raise InvalidTickerError(ticker, "Only alphanumeric, ^, -, ., / characters allowed (max 20 chars).")

    return _sanitize_ticker(ticker)


def _sanitize_ticker(ticker: str) -> str:
    return ticker.replace("^", "").replace("/", "_").replace("\\", "_").upper()


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

    cached = _cache.get(cache_key)
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
    if not data_dir.exists():
        return []

    result = []
    for path in sorted(data_dir.glob("*.parquet")):
        df = pd.read_parquet(path)
        if df.empty:
            continue

        stem = path.stem
        parts = stem.rsplit("_", 1)
        if len(parts) == 2 and parts[1] in VALID_INTERVALS:
            ticker_name = parts[0]
            interval_name = parts[1]
        else:
            ticker_name = stem
            interval_name = "1d"

        result.append(
            {
                "ticker": ticker_name,
                "interval": interval_name,
                "rows": len(df),
                "first_date": df.index.min().date().isoformat(),
                "last_date": df.index.max().date().isoformat(),
                "size_kb": round(path.stat().st_size / 1024, 1),
            }
        )
    return result


def status_paginated(
    page: int = 1,
    page_size: int = 24,
    search: str = "",
    data_dir: Path = DATA_DIR,
) -> dict[str, object]:
    """Return paginated ticker overview with latest quote included.

    Avoids reading every parquet for filtering: uses file metadata first,
    then only reads full data for tickers on the requested page.
    """
    if not data_dir.exists():
        return {"items": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 0}

    # Phase 1: collect all ticker paths (cheap — just filesystem)
    entries: list[tuple[str, str, Path]] = []
    for path in sorted(data_dir.glob("*.parquet")):
        stem = path.stem
        parts = stem.rsplit("_", 1)
        if len(parts) == 2 and parts[1] in VALID_INTERVALS:
            ticker_name = parts[0]
            interval_name = parts[1]
        else:
            ticker_name = stem
            interval_name = "1d"

        if search and search.upper() not in ticker_name.upper():
            continue

        entries.append((ticker_name, interval_name, path))

    total = len(entries)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))

    start = (page - 1) * page_size
    page_entries = entries[start : start + page_size]

    # Phase 2: only read parquet files for the current page
    items: list[dict[str, object]] = []
    for ticker_name, interval_name, path in page_entries:
        df = pd.read_parquet(path)
        if df.empty:
            continue

        latest: dict[str, object] | None = None
        change: float | None = None
        change_pct: float | None = None

        if len(df) > 0:
            last_row = df.iloc[-1]
            close_val = float(last_row.get("Close", 0))
            open_val = float(last_row.get("Open", 0))
            latest = {
                "date": df.index[-1].date().isoformat(),
                "open": open_val,
                "high": float(last_row.get("High", 0)),
                "low": float(last_row.get("Low", 0)),
                "close": close_val,
                "volume": int(last_row.get("Volume", 0)),
            }
            if open_val != 0:
                change = round(close_val - open_val, 4)
                change_pct = round(((close_val - open_val) / open_val) * 100, 4)

        items.append(
            {
                "ticker": ticker_name,
                "interval": interval_name,
                "rows": len(df),
                "first_date": df.index.min().date().isoformat(),
                "last_date": df.index.max().date().isoformat(),
                "size_kb": round(path.stat().st_size / 1024, 1),
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
