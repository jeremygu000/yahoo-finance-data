from __future__ import annotations

import logging
import random
import time
from datetime import date, timedelta

import pandas as pd
import yfinance as yf

from market_data.config import MAX_RETRIES, RETRY_DELAY_RANGE
from market_data.providers.base import OHLCV_COLUMNS, MarketDataProvider

logger = logging.getLogger(__name__)


class YFinanceProvider(MarketDataProvider):
    @property
    def name(self) -> str:
        return "yfinance"

    @property
    def supported_intervals(self) -> list[str]:
        return ["1d", "1h", "15m", "5m"]

    def is_available(self) -> bool:
        return True

    def fetch_ohlcv(self, ticker: str, start: date, end: date, interval: str = "1d") -> pd.DataFrame:
        end_inclusive = end + timedelta(days=1)
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                raw: pd.DataFrame = yf.download(
                    tickers=[ticker],
                    start=start.isoformat(),
                    end=end_inclusive.isoformat(),
                    interval=interval,
                    group_by="ticker",
                    threads=False,
                    repair=True,
                    progress=False,
                )
                break
            except Exception:
                logger.warning("yfinance attempt %d/%d failed for %s", attempt, MAX_RETRIES, ticker)
                if attempt < MAX_RETRIES:
                    time.sleep(random.uniform(*RETRY_DELAY_RANGE))
                else:
                    logger.error("All %d yfinance attempts failed for %s", MAX_RETRIES, ticker)
                    return pd.DataFrame()

        return _normalize(raw)

    def fetch_batch(
        self, tickers: list[str], start: date, end: date, interval: str = "1d"
    ) -> dict[str, pd.DataFrame]:
        if not tickers:
            return {}

        end_inclusive = end + timedelta(days=1)

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                raw: pd.DataFrame = yf.download(
                    tickers=tickers,
                    start=start.isoformat(),
                    end=end_inclusive.isoformat(),
                    interval=interval,
                    group_by="ticker",
                    threads=True,
                    repair=True,
                    progress=False,
                )
                break
            except Exception:
                logger.warning("yfinance batch attempt %d/%d failed", attempt, MAX_RETRIES)
                if attempt < MAX_RETRIES:
                    time.sleep(random.uniform(*RETRY_DELAY_RANGE))
                else:
                    logger.error("All %d yfinance batch attempts failed", MAX_RETRIES)
                    return {}

        if raw.empty:
            return {}

        result: dict[str, pd.DataFrame] = {}
        has_multiindex = isinstance(raw.columns, pd.MultiIndex)

        for ticker in tickers:
            try:
                if has_multiindex:
                    level_values = raw.columns.get_level_values(0)
                    if ticker in level_values:
                        df_ticker = pd.DataFrame(raw[ticker])
                    else:
                        field_level = raw.columns.get_level_values(1)
                        if ticker in field_level:
                            df_ticker = pd.DataFrame(raw.xs(ticker, axis=1, level=1))
                        else:
                            continue
                else:
                    df_ticker = raw
            except (KeyError, TypeError):
                continue

            df = _normalize(df_ticker)
            if not df.empty:
                result[ticker] = df

        return result


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    if isinstance(df.columns, pd.MultiIndex):
        df = df.droplevel(level=1, axis=1) if df.columns.nlevels > 1 else df
        df.columns = [str(c) for c in df.columns]

    available = [c for c in OHLCV_COLUMNS if c in df.columns]
    if not available:
        return pd.DataFrame()

    df = df[available].copy()
    df.dropna(how="all", inplace=True)

    if df.empty:
        return pd.DataFrame()

    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    df.index.name = "Date"
    return df
