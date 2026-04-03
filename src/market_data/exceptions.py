"""Custom exceptions for market_data — used by error handling middleware."""

from __future__ import annotations


class MarketDataError(Exception):
    pass


class TickerNotFoundError(MarketDataError):
    def __init__(self, ticker: str) -> None:
        self.ticker = ticker
        super().__init__(f"No data found for ticker: {ticker!r}")


class InvalidTickerError(MarketDataError):
    def __init__(self, ticker: str, reason: str = "") -> None:
        self.ticker = ticker
        self.reason = reason
        super().__init__(f"Invalid ticker: {ticker!r}. {reason}".strip())


class DataFetchError(MarketDataError):
    pass
