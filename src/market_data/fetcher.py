"""Yahoo Finance batch fetcher with retry and empty-DataFrame detection."""

from __future__ import annotations

import logging
import random
import time
from datetime import date, timedelta

import pandas as pd
import yfinance as yf

from market_data.config import MAX_RETRIES, RETRY_DELAY_RANGE

logger = logging.getLogger(__name__)


def fetch_batch(
    tickers: list[str],
    start: date | None = None,
    end: date | None = None,
    period: str | None = None,
) -> dict[str, pd.DataFrame]:
    """Fetch OHLCV data for multiple tickers in one yf.download() call.

    Returns dict mapping ticker -> DataFrame[Open, High, Low, Close, Volume].
    Missing or failed tickers are omitted.
    """
    if not tickers:
        return {}

    if end is None and start is not None:
        end = date.today() + timedelta(days=1)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            raw = yf.download(
                tickers=tickers,
                start=start.isoformat() if start else None,
                end=end.isoformat() if end else None,
                period=period if period else None,
                group_by="ticker",
                threads=True,
                repair=True,
                progress=False,
            )
            break
        except Exception:
            logger.warning("yfinance download attempt %d/%d failed", attempt, MAX_RETRIES)
            if attempt < MAX_RETRIES:
                delay = random.uniform(*RETRY_DELAY_RANGE)
                time.sleep(delay)
            else:
                logger.error("All %d download attempts failed", MAX_RETRIES)
                return {}

    result: dict[str, pd.DataFrame] = {}

    if raw.empty:
        return result

    has_multiindex = isinstance(raw.columns, pd.MultiIndex)

    for ticker in tickers:
        try:
            if has_multiindex:
                level_values = raw.columns.get_level_values(0)
                if ticker in level_values:
                    df_ticker = raw[ticker]
                else:
                    field_level = raw.columns.get_level_values(1)
                    if ticker in field_level:
                        df_ticker = raw.xs(ticker, axis=1, level=1)
                    else:
                        continue
            else:
                df_ticker = raw
        except (KeyError, TypeError):
            continue

        df = _clean_df(df_ticker)
        if df is not None:
            result[ticker] = df

    return result


def _clean_df(df: pd.DataFrame) -> pd.DataFrame | None:
    """Validate and return OHLCV-only DataFrame, or None if empty/invalid."""
    if df is None or df.empty:
        return None

    if isinstance(df.columns, pd.MultiIndex):
        df = df.droplevel(level=1, axis=1) if df.columns.nlevels > 1 else df
        df.columns = [str(c) for c in df.columns]

    expected = ["Open", "High", "Low", "Close", "Volume"]
    available = [c for c in expected if c in df.columns]
    if not available:
        return None

    df = df[available].copy()
    df.dropna(how="all", inplace=True)

    if df.empty:
        return None

    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    df.index.name = "Date"
    return df
