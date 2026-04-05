from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta

import pandas as pd

from market_data.config import BATCH_SIZE, FETCH_CONCURRENCY
from market_data.providers import get_fallback_chain
from market_data.providers.base import MarketDataProvider

logger = logging.getLogger(__name__)


def _try_provider(
    provider: MarketDataProvider, tickers: list[str], start: date, end: date, interval: str
) -> dict[str, pd.DataFrame]:
    """Attempt a batch fetch from one provider (retry is handled by the provider)."""
    try:
        return provider.fetch_batch(tickers, start, end, interval=interval)
    except Exception:
        logger.exception("Provider %s failed for %d tickers", provider.name, len(tickers))
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

    result = _try_provider(primary, chunk, start, end, interval)

    missing = [t for t in chunk if t not in result]
    for provider in fallbacks:
        if not missing:
            break
        logger.info("Trying fallback %s for %d missing tickers", provider.name, len(missing))
        fallback_result = _try_provider(provider, missing, start, end, interval)
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

    max_workers = min(FETCH_CONCURRENCY, len(chunks))
    if max_workers <= 1:
        logger.info("Fetching %d tickers in 1 chunk", len(tickers))
        chunk_result = _fetch_chunk(chunks[0], start, end, interval, eligible)
        result.update(chunk_result)
    else:
        logger.info(
            "Fetching %d tickers in %d chunks (concurrency=%d)",
            len(tickers),
            len(chunks),
            max_workers,
        )
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {
                executor.submit(_fetch_chunk, chunk, start, end, interval, eligible): i
                for i, chunk in enumerate(chunks)
            }
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    chunk_result = future.result()
                    result.update(chunk_result)
                    logger.info(
                        "Chunk %d/%d complete: %d tickers fetched",
                        idx + 1,
                        len(chunks),
                        len(chunk_result),
                    )
                except Exception:
                    logger.exception("Chunk %d/%d failed", idx + 1, len(chunks))

    fetched = len(result)
    missing = [t for t in tickers if t not in result]
    logger.info("Fetched %d/%d tickers total", fetched, len(tickers))
    if missing:
        logger.warning("Still missing after all providers: %s", ", ".join(missing[:20]))

    return result
