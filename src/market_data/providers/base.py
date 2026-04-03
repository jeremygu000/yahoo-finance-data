"""Abstract base class for market data providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

import pandas as pd

# Standard column names — all providers must normalize to this
OHLCV_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]


class MarketDataProvider(ABC):
    """Interface for fetching OHLCV data from any source."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier, e.g. 'yfinance', 'tiingo', 'fmp'."""

    @abstractmethod
    def fetch_ohlcv(
        self,
        ticker: str,
        start: date,
        end: date,
    ) -> pd.DataFrame:
        """Fetch daily OHLCV for a single ticker.

        Returns DataFrame with DatetimeIndex named 'Date' and columns
        [Open, High, Low, Close, Volume]. Empty DataFrame if no data.
        """

    def fetch_batch(
        self,
        tickers: list[str],
        start: date,
        end: date,
    ) -> dict[str, pd.DataFrame]:
        """Fetch OHLCV for multiple tickers. Default: sequential calls."""
        result: dict[str, pd.DataFrame] = {}
        for ticker in tickers:
            df = self.fetch_ohlcv(ticker, start, end)
            if not df.empty:
                result[ticker] = df
        return result

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is configured (API key present, etc.)."""
