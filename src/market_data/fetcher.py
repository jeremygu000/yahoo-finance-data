"""Batch fetcher with provider fallback chain."""

from __future__ import annotations

import logging
from datetime import date, timedelta

import pandas as pd

from market_data.providers import get_fallback_chain

logger = logging.getLogger(__name__)


def fetch_batch(
    tickers: list[str],
    start: date | None = None,
    end: date | None = None,
    period: str | None = None,
) -> dict[str, pd.DataFrame]:
    if not tickers:
        return {}

    if start is None:
        start = date.today() - timedelta(days=365)
    if end is None:
        end = date.today()

    chain = get_fallback_chain()
    if not chain:
        logger.error("No providers available in fallback chain")
        return {}

    primary = chain[0]
    fallbacks = chain[1:]

    result = primary.fetch_batch(tickers, start, end)
    logger.info("Primary provider %s returned %d/%d tickers", primary.name, len(result), len(tickers))

    missing = [t for t in tickers if t not in result]
    for provider in fallbacks:
        if not missing:
            break
        logger.info("Trying fallback %s for %d missing tickers", provider.name, len(missing))
        fallback_result = provider.fetch_batch(missing, start, end)
        for ticker, df in fallback_result.items():
            result[ticker] = df
        missing = [t for t in missing if t not in fallback_result]

    if missing:
        logger.warning("Still missing after all providers: %s", ", ".join(missing))

    return result
