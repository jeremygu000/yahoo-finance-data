from __future__ import annotations

import logging
import time
from typing import Any

import yfinance as yf

from market_data.cache import InMemoryCache
from market_data.config import CACHE_TTL_SECONDS

logger = logging.getLogger(__name__)

_FUNDAMENTALS_TTL = max(CACHE_TTL_SECONDS, 300)
_cache = InMemoryCache(ttl_seconds=_FUNDAMENTALS_TTL, max_entries=512)

_INFO_KEYS: list[str] = [
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


def get_fundamentals(ticker: str) -> dict[str, Any]:
    cache_key = f"fundamentals:{ticker.upper()}"
    cached: dict[str, Any] | None = _cache.get(cache_key)
    if cached is not None:
        return cached

    start = time.monotonic()
    try:
        t = yf.Ticker(ticker)
        info: dict[str, Any] = t.info or {}
    except Exception:
        logger.warning("fundamentals fetch failed for %s", ticker, exc_info=True)
        info = {}

    result: dict[str, Any] = {"ticker": ticker.upper()}
    for key in _INFO_KEYS:
        result[key] = info.get(key)

    elapsed_ms = round((time.monotonic() - start) * 1000)
    logger.info("fundamentals fetched for %s in %dms", ticker, elapsed_ms)

    _cache.set(cache_key, result)
    return result


def get_fundamentals_batch(tickers: list[str]) -> list[dict[str, Any]]:
    return [get_fundamentals(t) for t in tickers]


def invalidate_cache(ticker: str | None = None) -> None:
    if ticker is None:
        _cache.clear()
    else:
        _cache.delete(f"fundamentals:{ticker.upper()}")
