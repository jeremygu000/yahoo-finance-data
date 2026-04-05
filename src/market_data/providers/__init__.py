from __future__ import annotations

import logging
import os

from market_data.providers.base import MarketDataProvider, OHLCV_COLUMNS
from market_data.providers.fmp import FMPProvider
from market_data.providers.tiingo import TiingoProvider
from market_data.providers.twelvedata import TwelvedataProvider
from market_data.providers.yfinance import YFinanceProvider

__all__ = ["get_provider", "get_fallback_chain", "MarketDataProvider", "OHLCV_COLUMNS"]

logger = logging.getLogger(__name__)

_PROVIDERS: dict[str, type[MarketDataProvider]] = {
    "yfinance": YFinanceProvider,
    "tiingo": TiingoProvider,
    "fmp": FMPProvider,
    "twelvedata": TwelvedataProvider,
}

_DEFAULT_CHAIN = ["yfinance", "tiingo", "fmp", "twelvedata"]


def get_provider(name: str | None = None) -> MarketDataProvider:
    provider_name = name or os.environ.get("MARKET_DATA_PROVIDER", "yfinance")
    cls = _PROVIDERS.get(provider_name)
    if cls is None:
        raise ValueError(f"Unknown provider: {provider_name!r}. Available: {list(_PROVIDERS.keys())}")
    return cls()


def get_fallback_chain() -> list[MarketDataProvider]:
    chain_str = os.environ.get("MARKET_DATA_FALLBACK_CHAIN", "")
    if chain_str:
        names = [n.strip() for n in chain_str.split(",") if n.strip()]
    else:
        names = _DEFAULT_CHAIN

    chain: list[MarketDataProvider] = []
    for name in names:
        cls = _PROVIDERS.get(name)
        if cls is None:
            logger.warning("Unknown provider in fallback chain: %s", name)
            continue
        provider = cls()
        if provider.is_available():
            chain.append(provider)
        else:
            logger.debug("Provider %s not available, skipping", name)

    return chain
