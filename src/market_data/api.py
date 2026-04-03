from __future__ import annotations

import pandas as pd

from market_data import store


def get_ohlcv(ticker: str, days: int = 30) -> pd.DataFrame:
    """Read locally cached OHLCV data. This is the primary API for consumers."""
    return store.load(ticker, days=days)


def get_latest(ticker: str) -> dict[str, object] | None:
    """Most recent data point as dict: date, open, high, low, close, volume."""
    df = store.load(ticker, days=7)
    if df.empty:
        return None

    last = df.iloc[-1]
    return {
        "date": df.index[-1].date().isoformat(),
        "open": float(last.get("Open", 0)),
        "high": float(last.get("High", 0)),
        "low": float(last.get("Low", 0)),
        "close": float(last.get("Close", 0)),
        "volume": int(last.get("Volume", 0)),
    }


def list_tickers() -> list[str]:
    """All ticker names with cached data."""
    return store.list_tickers()
