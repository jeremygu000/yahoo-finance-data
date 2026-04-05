from __future__ import annotations

import logging
import os
import time
from datetime import date

import pandas as pd
import requests

from market_data.providers.base import MarketDataProvider
from market_data.rate_limit_db import (
    ensure_quota,
    try_consume,
    record_rate_limit,
    record_success,
    log_call,
    get_throttle,
)

logger = logging.getLogger(__name__)

_API_BASE = "https://api.twelvedata.com"

_MINUTE_QUOTA = 8
_DAILY_QUOTA = 800
_MAX_OUTPUTSIZE = 5000


class TwelvedataProvider(MarketDataProvider):
    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("TWELVEDATA_API_KEY", "")
        if self._api_key:
            ensure_quota("twelvedata", "minute", _MINUTE_QUOTA)
            ensure_quota("twelvedata", "daily", _DAILY_QUOTA)

    @property
    def name(self) -> str:
        return "twelvedata"

    @property
    def supported_intervals(self) -> list[str]:
        return ["1day"]

    def is_available(self) -> bool:
        return bool(self._api_key)

    def fetch_ohlcv(self, ticker: str, start: date, end: date, interval: str = "1d") -> pd.DataFrame:
        if not self._api_key:
            logger.warning("Twelvedata API key not configured")
            return pd.DataFrame()

        td_interval = "1day" if interval in ("1d", "1day") else interval
        if td_interval not in ("1day",):
            logger.warning(
                "Twelvedata free plan only supports daily data; ignoring interval=%s for %s", interval, ticker
            )
            return pd.DataFrame()

        throttle = get_throttle("twelvedata")
        delay = throttle.get("current_delay", 0.0)
        if isinstance(delay, (int, float)) and delay > 0:
            time.sleep(delay)

        if not try_consume("twelvedata", "minute"):
            logger.warning("Twelvedata minute quota exhausted — waiting 60s")
            time.sleep(60)
            ensure_quota("twelvedata", "minute", _MINUTE_QUOTA)
            if not try_consume("twelvedata", "minute"):
                log_call("twelvedata", ticker=ticker, endpoint="time_series", status="rate_limited")
                return pd.DataFrame()

        if not try_consume("twelvedata", "daily"):
            logger.warning("Twelvedata daily quota exhausted for %s", ticker)
            log_call("twelvedata", ticker=ticker, endpoint="time_series", status="rate_limited")
            return pd.DataFrame()

        params = {
            "symbol": ticker,
            "interval": td_interval,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "outputsize": str(_MAX_OUTPUTSIZE),
            "order": "asc",
            "apikey": self._api_key,
        }

        try:
            resp = requests.get(f"{_API_BASE}/time_series", params=params, timeout=30)

            if resp.status_code == 429:
                record_rate_limit("twelvedata")
                log_call("twelvedata", ticker=ticker, endpoint="time_series", status="rate_limited")
                return pd.DataFrame()

            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            logger.error("Twelvedata request failed for %s: %s", ticker, exc)
            log_call("twelvedata", ticker=ticker, endpoint="time_series", status="error")
            return pd.DataFrame()

        if data.get("status") == "error" or "code" in data:
            logger.error("Twelvedata API error for %s: %s", ticker, data.get("message", data))
            log_call("twelvedata", ticker=ticker, endpoint="time_series", status="error")
            return pd.DataFrame()

        values = data.get("values")
        if not values:
            log_call("twelvedata", ticker=ticker, endpoint="time_series", status="ok")
            return pd.DataFrame()

        record_success("twelvedata")
        log_call("twelvedata", ticker=ticker, endpoint="time_series", status="ok")
        df = pd.DataFrame(values)
        return _normalize_twelvedata(df)


def _normalize_twelvedata(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    if "datetime" not in df.columns:
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

    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    available = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
    df = df[["datetime"] + available].copy()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.set_index("datetime")
    df.index.name = "Date"
    df.sort_index(inplace=True)
    df.dropna(how="all", inplace=True)

    return df if not df.empty else pd.DataFrame()
