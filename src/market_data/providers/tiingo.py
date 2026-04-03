from __future__ import annotations

import logging
import os
from datetime import date

import pandas as pd
import requests

from market_data.providers.base import MarketDataProvider

logger = logging.getLogger(__name__)

_API_BASE = "https://api.tiingo.com/tiingo/daily"


class TiingoProvider(MarketDataProvider):
    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("TIINGO_API_KEY", "")

    @property
    def name(self) -> str:
        return "tiingo"

    def is_available(self) -> bool:
        return bool(self._api_key)

    def fetch_ohlcv(self, ticker: str, start: date, end: date) -> pd.DataFrame:
        if not self._api_key:
            logger.warning("Tiingo API key not configured")
            return pd.DataFrame()

        url = f"{_API_BASE}/{ticker}/prices"
        headers = {"Authorization": f"Token {self._api_key}"}
        params = {
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            "format": "json",
            "resampleFreq": "daily",
        }

        try:
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            logger.error("Tiingo request failed for %s: %s", ticker, exc)
            return pd.DataFrame()

        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)
        return _normalize_tiingo(df)


def _normalize_tiingo(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    column_map = {
        "adjOpen": "Open",
        "adjHigh": "High",
        "adjLow": "Low",
        "adjClose": "Close",
        "adjVolume": "Volume",
    }

    fallback_map = {
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume",
    }

    rename = {}
    for src, dst in column_map.items():
        if src in df.columns:
            rename[src] = dst

    if not rename:
        for src, dst in fallback_map.items():
            if src in df.columns:
                rename[src] = dst

    if not rename:
        return pd.DataFrame()

    df = df.rename(columns=rename)
    available = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
    df = df[["date"] + available].copy()

    df["date"] = pd.to_datetime(df["date"], utc=True)
    df["date"] = df["date"].dt.tz_localize(None)
    df = df.set_index("date")
    df.index.name = "Date"
    df.dropna(how="all", inplace=True)

    return df if not df.empty else pd.DataFrame()
