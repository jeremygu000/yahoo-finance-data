"""Parquet store: ~/.market_data/parquet/{TICKER}.parquet

Ticker sanitization: "^VIX" -> "VIX", "/" -> "_".
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import pandas as pd

from market_data.config import DATA_DIR

logger = logging.getLogger(__name__)


def _sanitize_ticker(ticker: str) -> str:
    return ticker.replace("^", "").replace("/", "_").replace("\\", "_").upper()


def _parquet_path(ticker: str, data_dir: Path = DATA_DIR) -> Path:
    return data_dir / f"{_sanitize_ticker(ticker)}.parquet"


def save(ticker: str, df: pd.DataFrame, data_dir: Path = DATA_DIR) -> int:
    """Append-save DataFrame to parquet, deduplicating by date. Returns new row count."""
    data_dir.mkdir(parents=True, exist_ok=True)
    path = _parquet_path(ticker, data_dir)

    if path.exists():
        existing = pd.read_parquet(path)
        combined = pd.concat([existing, df])
    else:
        combined = df.copy()

    combined = combined[~combined.index.duplicated(keep="last")]
    combined.sort_index(inplace=True)

    rows_before = len(pd.read_parquet(path)) if path.exists() else 0
    combined.to_parquet(path, engine="pyarrow")
    rows_added = len(combined) - rows_before
    logger.info("%s: saved %d rows (total %d)", ticker, rows_added, len(combined))
    return rows_added


def load(ticker: str, days: int | None = None, data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Load OHLCV data from local parquet. Returns empty DataFrame if not found."""
    path = _parquet_path(ticker, data_dir)
    if not path.exists():
        logger.warning("%s: no local data at %s", ticker, path)
        return pd.DataFrame()

    df = pd.read_parquet(path)

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
