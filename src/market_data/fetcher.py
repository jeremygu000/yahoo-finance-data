from __future__ import annotations

import logging
import random
import time
from datetime import date, timedelta

import pandas as pd

from market_data.config import BATCH_SIZE, MAX_RETRIES, RETRY_DELAY_RANGE
from market_data.providers import get_fallback_chain
from market_data.providers.base import MarketDataProvider

logger = logging.getLogger(__name__)


def _fetch_with_retry(
    provider: MarketDataProvider, tickers: list[str], start: date, end: date, interval: str
) -> dict[str, pd.DataFrame]:
    """Fetch data from provider with exponential backoff + jitter retry logic."""
    for attempt in range(MAX_RETRIES + 1):
        try:
            return provider.fetch_batch(tickers, start, end, interval=interval)
        except Exception as e:
            if attempt < MAX_RETRIES:
                # Exponential backoff with jitter
                base_delay = RETRY_DELAY_RANGE[0] * (2**attempt)
                jitter = random.uniform(0, RETRY_DELAY_RANGE[1] - RETRY_DELAY_RANGE[0])
                delay = base_delay + jitter
                logger.warning(
                    "Provider %s failed (attempt %d/%d): %s. Retrying in %.2fs",
                    provider.name,
                    attempt + 1,
                    MAX_RETRIES,
                    str(e),
                    delay,
                )
                time.sleep(delay)
            else:
                logger.error(
                    "Provider %s failed after %d attempts: %s",
                    provider.name,
                    MAX_RETRIES + 1,
                    str(e),
                )
                return {}
    return {}


def _chunked(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def _fetch_chunk(
    chunk: list[str],
    start: date,
    end: date,
    interval: str,
    eligible: list[MarketDataProvider],
) -> dict[str, pd.DataFrame]:
    primary = eligible[0]
    fallbacks = eligible[1:]

    result = _fetch_with_retry(primary, chunk, start, end, interval)

    missing = [t for t in chunk if t not in result]
    for provider in fallbacks:
        if not missing:
            break
        logger.info("Trying fallback %s for %d missing tickers", provider.name, len(missing))
        fallback_result = _fetch_with_retry(provider, missing, start, end, interval)
        for ticker, df in fallback_result.items():
            result[ticker] = df
        missing = [t for t in missing if t not in fallback_result]

    return result


def fetch_batch(
    tickers: list[str],
    start: date | None = None,
    end: date | None = None,
    period: str | None = None,
    interval: str = "1d",
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

    eligible = [p for p in chain if interval in p.supported_intervals]
    skipped = [p for p in chain if interval not in p.supported_intervals]
    for p in skipped:
        logger.info("Skipping provider %s: does not support interval=%s", p.name, interval)

    if not eligible:
        logger.error("No providers support interval=%s", interval)
        return {}

    chunks = _chunked(tickers, BATCH_SIZE)
    result: dict[str, pd.DataFrame] = {}

    for i, chunk in enumerate(chunks):
        if i > 0:
            delay = random.uniform(*RETRY_DELAY_RANGE)
            logger.info("Chunk %d/%d: sleeping %.1fs before next batch", i + 1, len(chunks), delay)
            time.sleep(delay)

        logger.info("Chunk %d/%d: fetching %d tickers", i + 1, len(chunks), len(chunk))
        chunk_result = _fetch_chunk(chunk, start, end, interval, eligible)
        result.update(chunk_result)

    fetched = len(result)
    missing = [t for t in tickers if t not in result]
    logger.info("Fetched %d/%d tickers total", fetched, len(tickers))
    if missing:
        logger.warning("Still missing after all providers: %s", ", ".join(missing[:20]))

    return result
