from __future__ import annotations

import logging
import os
from datetime import date

import pandas as pd
import requests

from market_data.providers.base import MarketDataProvider

logger = logging.getLogger(__name__)

_API_BASE = "https://financialmodelingprep.com/stable"


class FMPProvider(MarketDataProvider):
    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("FMP_API_KEY", "")

    @property
    def name(self) -> str:
        return "fmp"

    def is_available(self) -> bool:
        return bool(self._api_key)

    def fetch_ohlcv(self, ticker: str, start: date, end: date) -> pd.DataFrame:
        if not self._api_key:
            logger.warning("FMP API key not configured")
            return pd.DataFrame()

        url = f"{_API_BASE}/historical-price-eod/full"
        params = {
            "symbol": ticker,
            "from": start.isoformat(),
            "to": end.isoformat(),
            "apikey": self._api_key,
        }

        try:
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            logger.error("FMP request failed for %s: %s", ticker, exc)
            return pd.DataFrame()

        if not data or not isinstance(data, list):
            return pd.DataFrame()

        df = pd.DataFrame(data)
        return _normalize_fmp(df)


def _normalize_fmp(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    column_map = {
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume",
    }

    rename = {src: dst for src, dst in column_map.items() if src in df.columns}
    if not rename:
        return pd.DataFrame()

    df = df.rename(columns=rename)
    available = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]

    if "date" not in df.columns:
        return pd.DataFrame()

    df = df[["date"] + available].copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    df.index.name = "Date"
    df.sort_index(inplace=True)
    df.dropna(how="all", inplace=True)

    return df if not df.empty else pd.DataFrame()
