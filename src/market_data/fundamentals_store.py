"""Parquet persistence layer for fundamental data.

Stores four types of data per ticker:
- {TICKER}_fundamentals.parquet  — scalar info snapshot (append, dedup by day)
- {TICKER}_recommendations.parquet — analyst recommendation history
- {TICKER}_earnings_dates.parquet — earnings dates with EPS
- {TICKER}_upgrades_downgrades.parquet — analyst rating changes
"""

from __future__ import annotations

import logging
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf

from market_data.config import DATA_DIR
from market_data.store import validate_ticker

logger = logging.getLogger(__name__)

_ALL_INFO_KEYS: list[str] = [
    # Valuation
    "marketCap",
    "trailingPE",
    "forwardPE",
    "trailingEps",
    "forwardEps",
    "priceToBook",
    "priceToSalesTrailing12Months",
    "pegRatio",
    "enterpriseValue",
    "enterpriseToEbitda",
    "dividendYield",
    "beta",
    # Price / Quote
    "regularMarketPrice",
    "currentPrice",
    "currency",
    # Price Targets
    "targetLowPrice",
    "targetHighPrice",
    "targetMeanPrice",
    "targetMedianPrice",
    "numberOfAnalystOpinions",
    # Analyst
    "recommendationKey",
    "recommendationMean",
    # Short Interest
    "shortRatio",
    "shortPercentOfFloat",
    "sharesShort",
    # Income
    "totalRevenue",
    "revenueGrowth",
    "grossMargins",
    "operatingMargins",
    "profitMargins",
    "earningsQuarterlyGrowth",
    "earningsGrowth",
    # Quality factors
    "returnOnEquity",
    "debtToEquity",
    # Identity & descriptive
    "shortName",
    "longName",
    "sector",
    "industry",
    "fiftyTwoWeekHigh",
    "fiftyTwoWeekLow",
    "averageVolume",
    "quoteType",
]


def _fundamentals_path(ticker: str, data_dir: Path = DATA_DIR) -> Path:
    safe = validate_ticker(ticker)
    return data_dir / f"{safe}_fundamentals.parquet"


def _recommendations_path(ticker: str, data_dir: Path = DATA_DIR) -> Path:
    safe = validate_ticker(ticker)
    return data_dir / f"{safe}_recommendations.parquet"


def _earnings_dates_path(ticker: str, data_dir: Path = DATA_DIR) -> Path:
    safe = validate_ticker(ticker)
    return data_dir / f"{safe}_earnings_dates.parquet"


def _upgrades_downgrades_path(ticker: str, data_dir: Path = DATA_DIR) -> Path:
    safe = validate_ticker(ticker)
    return data_dir / f"{safe}_upgrades_downgrades.parquet"


def _atomic_write(df: pd.DataFrame, path: Path) -> None:
    """Write a DataFrame to Parquet atomically via temp file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".parquet.tmp")
    try:
        import os

        os.close(tmp_fd)
        df.to_parquet(tmp_path, engine="pyarrow")
        Path(tmp_path).replace(path)
    except BaseException:
        Path(tmp_path).unlink(missing_ok=True)
        raise


def fetch_and_save_fundamentals(ticker: str, data_dir: Path = DATA_DIR) -> dict[str, Any]:
    """Fetch fundamental snapshot from yfinance and save to Parquet.

    Returns the fetched dict (with all _ALL_INFO_KEYS + fetched_at).
    Appends to existing Parquet file, deduplicates by calendar day.
    """
    data_dir.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()

    try:
        t = yf.Ticker(ticker)
        info: dict[str, Any] = t.info or {}
    except Exception:
        logger.warning("fundamentals fetch failed for %s", ticker, exc_info=True)
        return {}

    now = datetime.now(timezone.utc)
    row: dict[str, Any] = {"fetched_at": now}
    for key in _ALL_INFO_KEYS:
        row[key] = info.get(key)

    df_new = pd.DataFrame([row])
    df_new["fetched_at"] = pd.to_datetime(df_new["fetched_at"], utc=True)
    df_new = df_new.set_index("fetched_at")

    path = _fundamentals_path(ticker, data_dir)
    if path.exists():
        existing = pd.read_parquet(path)
        if not isinstance(existing.index, pd.DatetimeIndex):
            existing.index = pd.to_datetime(existing.index, utc=True)
        combined = pd.concat([existing, df_new])
    else:
        combined = df_new

    # Deduplicate: keep latest row per calendar day
    dt_index = pd.DatetimeIndex(combined.index)
    combined["_day"] = dt_index.date
    combined = combined[~combined["_day"].duplicated(keep="last")]
    combined = combined.drop(columns=["_day"])
    combined.sort_index(inplace=True)

    _atomic_write(combined, path)

    elapsed_ms = round((time.monotonic() - start) * 1000)
    logger.info("fundamentals saved for %s (%d rows, %dms)", ticker, len(combined), elapsed_ms)

    row["ticker"] = ticker.upper()
    return row


def fetch_and_save_recommendations(ticker: str, data_dir: Path = DATA_DIR) -> int:
    """Fetch recommendations from yfinance and save/merge to Parquet. Returns row count."""
    data_dir.mkdir(parents=True, exist_ok=True)
    try:
        t = yf.Ticker(ticker)
        df: pd.DataFrame | None = t.recommendations
    except Exception:
        logger.warning("recommendations fetch failed for %s", ticker, exc_info=True)
        return 0

    if df is None or df.empty:
        logger.info("no recommendations data for %s", ticker)
        return 0

    path = _recommendations_path(ticker, data_dir)
    if path.exists():
        existing = pd.read_parquet(path)
        combined = pd.concat([existing, df])
        combined = combined[~combined.index.duplicated(keep="last")]
        combined.sort_index(inplace=True)
    else:
        combined = df

    _atomic_write(combined, path)
    logger.info("recommendations saved for %s (%d rows)", ticker, len(combined))
    return len(combined)


def fetch_and_save_earnings_dates(ticker: str, data_dir: Path = DATA_DIR) -> int:
    """Fetch earnings dates from yfinance and save/merge to Parquet. Returns row count."""
    data_dir.mkdir(parents=True, exist_ok=True)
    try:
        t = yf.Ticker(ticker)
        df: pd.DataFrame | None = t.earnings_dates
    except Exception:
        logger.warning("earnings_dates fetch failed for %s", ticker, exc_info=True)
        return 0

    if df is None or df.empty:
        logger.info("no earnings_dates data for %s", ticker)
        return 0

    path = _earnings_dates_path(ticker, data_dir)
    if path.exists():
        existing = pd.read_parquet(path)
        combined = pd.concat([existing, df])
        combined = combined[~combined.index.duplicated(keep="last")]
        combined.sort_index(inplace=True)
    else:
        combined = df

    _atomic_write(combined, path)
    logger.info("earnings_dates saved for %s (%d rows)", ticker, len(combined))
    return len(combined)


def fetch_and_save_upgrades_downgrades(ticker: str, data_dir: Path = DATA_DIR) -> int:
    """Fetch upgrades/downgrades from yfinance and save/merge to Parquet. Returns row count."""
    data_dir.mkdir(parents=True, exist_ok=True)
    try:
        t = yf.Ticker(ticker)
        df: pd.DataFrame | None = t.upgrades_downgrades
    except Exception:
        logger.warning("upgrades_downgrades fetch failed for %s", ticker, exc_info=True)
        return 0

    if df is None or df.empty:
        logger.info("no upgrades_downgrades data for %s", ticker)
        return 0

    path = _upgrades_downgrades_path(ticker, data_dir)
    if path.exists():
        existing = pd.read_parquet(path)
        combined = pd.concat([existing, df])
        combined = combined[~combined.index.duplicated(keep="last")]
        combined.sort_index(inplace=True)
    else:
        combined = df

    _atomic_write(combined, path)
    logger.info("upgrades_downgrades saved for %s (%d rows)", ticker, len(combined))
    return len(combined)


def fetch_all_fundamental_data(ticker: str, data_dir: Path = DATA_DIR, delay: float = 0.5) -> dict[str, Any]:
    """Fetch all fundamental data types for a ticker.

    Returns a summary dict with counts for each type.
    """
    result: dict[str, Any] = {"ticker": ticker.upper()}

    fundamentals = fetch_and_save_fundamentals(ticker, data_dir)
    result["fundamentals"] = bool(fundamentals)

    time.sleep(delay)
    result["recommendations"] = fetch_and_save_recommendations(ticker, data_dir)

    time.sleep(delay)
    result["earnings_dates"] = fetch_and_save_earnings_dates(ticker, data_dir)

    time.sleep(delay)
    result["upgrades_downgrades"] = fetch_and_save_upgrades_downgrades(ticker, data_dir)

    return result


def load_fundamentals(ticker: str, data_dir: Path = DATA_DIR) -> dict[str, Any] | None:
    """Load the latest fundamental snapshot from Parquet.

    Returns a dict with all info keys + fetched_at, or None if no local data.
    """
    path = _fundamentals_path(ticker, data_dir)
    if not path.exists():
        return None

    df = pd.read_parquet(path)
    if df.empty:
        return None

    latest = df.iloc[-1]
    result: dict[str, Any] = {"ticker": ticker.upper()}
    result["fetched_at"] = str(latest.name)
    for key in _ALL_INFO_KEYS:
        val = latest.get(key)
        # Convert numpy types to Python native
        if pd.isna(val):
            result[key] = None
        else:
            result[key] = val
    return result


def load_recommendations(ticker: str, data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Load recommendations from Parquet. Returns empty DataFrame if missing."""
    path = _recommendations_path(ticker, data_dir)
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


def load_earnings_dates(ticker: str, data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Load earnings dates from Parquet. Returns empty DataFrame if missing."""
    path = _earnings_dates_path(ticker, data_dir)
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


def load_upgrades_downgrades(ticker: str, data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Load upgrades/downgrades from Parquet. Returns empty DataFrame if missing."""
    path = _upgrades_downgrades_path(ticker, data_dir)
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)
