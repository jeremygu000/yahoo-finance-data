"""Fetch ticker news from Yahoo Finance via yfinance."""

from __future__ import annotations

import logging
import time
from typing import Any

import yfinance as yf

from market_data.cache import InMemoryCache
from market_data.config import CACHE_TTL_SECONDS

logger = logging.getLogger(__name__)

_NEWS_TTL = max(CACHE_TTL_SECONDS, 600)  # 10 min minimum for news
_cache = InMemoryCache(ttl_seconds=_NEWS_TTL, max_entries=256)

_ARTICLE_KEYS: list[str] = [
    "uuid",
    "title",
    "link",
    "publisher",
    "providerPublishTime",
    "type",
    "relatedTickers",
]


def _extract_thumbnail(raw: dict[str, Any]) -> str | None:
    """Extract the best thumbnail URL from a news item."""
    thumb = raw.get("thumbnail")
    if not isinstance(thumb, dict):
        return None
    resolutions = thumb.get("resolutions")
    if not isinstance(resolutions, list) or not resolutions:
        return None
    # Prefer 'original' tag, fall back to last (largest) resolution
    for res in resolutions:
        if isinstance(res, dict) and res.get("tag") == "original":
            url = res.get("url")
            if isinstance(url, str):
                return url
    last = resolutions[-1]
    if isinstance(last, dict):
        url = last.get("url")
        if isinstance(url, str):
            return url
    return None


def _normalize_article(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize a raw yfinance news dict into a clean article dict."""
    article: dict[str, Any] = {}
    for key in _ARTICLE_KEYS:
        article[key] = raw.get(key)
    article["thumbnail_url"] = _extract_thumbnail(raw)
    return article


def get_news(ticker: str, count: int = 10) -> dict[str, Any]:
    """Fetch news for a single ticker.

    Returns a dict with keys: ticker, articles, fetched_at.
    """
    cache_key = f"news:{ticker.upper()}:{count}"
    cached: dict[str, Any] | None = _cache.get(cache_key)
    if cached is not None:
        return cached

    start = time.monotonic()
    try:
        t = yf.Ticker(ticker)
        raw_news: list[dict[str, Any]] = t.get_news(count=count)
    except Exception:
        logger.warning("news fetch failed for %s", ticker, exc_info=True)
        raw_news = []

    articles = [_normalize_article(item) for item in raw_news]
    elapsed_ms = round((time.monotonic() - start) * 1000)
    logger.info(
        "news fetched for %s: %d articles in %dms",
        ticker,
        len(articles),
        elapsed_ms,
    )

    result: dict[str, Any] = {
        "ticker": ticker.upper(),
        "count": len(articles),
        "articles": articles,
    }
    _cache.set(cache_key, result)
    return result


def invalidate_cache(ticker: str | None = None) -> None:
    """Clear news cache. If ticker is given, only clear that ticker's entries."""
    if ticker is None:
        _cache.clear()
    else:
        # Clear all count variants for this ticker
        prefix = f"news:{ticker.upper()}:"
        keys_to_delete = [k for k in _cache._store if k.startswith(prefix)]
        for k in keys_to_delete:
            _cache.delete(k)
