from __future__ import annotations

from datetime import date
from unittest.mock import patch, MagicMock

import pandas as pd

from market_data.fetcher import fetch_batch
from market_data.providers.base import MarketDataProvider


def _make_ohlcv(rows: int = 2) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Open": [100.0 + i for i in range(rows)],
            "High": [102.0 + i for i in range(rows)],
            "Low": [99.0 + i for i in range(rows)],
            "Close": [101.0 + i for i in range(rows)],
            "Volume": [1000000 + i * 100000 for i in range(rows)],
        },
        index=pd.date_range("2024-01-01", periods=rows),
    )


class _FakeProvider(MarketDataProvider):
    def __init__(
        self,
        name: str,
        available: bool,
        data: dict[str, pd.DataFrame] | None = None,
        intervals: list[str] | None = None,
    ) -> None:
        self._name = name
        self._available = available
        self._data = data or {}
        self._intervals = intervals if intervals is not None else ["1d"]
        self._last_interval: str | None = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def supported_intervals(self) -> list[str]:
        return self._intervals

    def is_available(self) -> bool:
        return self._available

    def fetch_ohlcv(self, ticker: str, start: date, end: date, interval: str = "1d") -> pd.DataFrame:
        self._last_interval = interval
        return self._data.get(ticker, pd.DataFrame())

    def fetch_batch(self, tickers: list[str], start: date, end: date, interval: str = "1d") -> dict[str, pd.DataFrame]:
        self._last_interval = interval
        return {t: self._data[t] for t in tickers if t in self._data}


class TestFetchBatch:
    def test_empty_tickers(self) -> None:
        assert fetch_batch([]) == {}

    @patch("market_data.fetcher.get_fallback_chain")
    def test_primary_returns_all(self, mock_chain: MagicMock) -> None:
        primary = _FakeProvider("test", True, {"AAPL": _make_ohlcv(), "GOOG": _make_ohlcv()})
        mock_chain.return_value = [primary]

        result = fetch_batch(["AAPL", "GOOG"], start=date(2024, 1, 1), end=date(2024, 12, 31))

        assert set(result.keys()) == {"AAPL", "GOOG"}
        assert len(result["AAPL"]) == 2

    @patch("market_data.fetcher.get_fallback_chain")
    def test_fallback_fills_missing(self, mock_chain: MagicMock) -> None:
        primary = _FakeProvider("primary", True, {"AAPL": _make_ohlcv()})
        fallback = _FakeProvider("fallback", True, {"GOOG": _make_ohlcv()})
        mock_chain.return_value = [primary, fallback]

        result = fetch_batch(["AAPL", "GOOG"], start=date(2024, 1, 1), end=date(2024, 12, 31))

        assert set(result.keys()) == {"AAPL", "GOOG"}

    @patch("market_data.fetcher.get_fallback_chain")
    def test_no_providers_available(self, mock_chain: MagicMock) -> None:
        mock_chain.return_value = []

        result = fetch_batch(["AAPL"], start=date(2024, 1, 1), end=date(2024, 12, 31))

        assert result == {}

    @patch("market_data.fetcher.get_fallback_chain")
    def test_all_providers_miss_ticker(self, mock_chain: MagicMock) -> None:
        primary = _FakeProvider("primary", True, {})
        fallback = _FakeProvider("fallback", True, {})
        mock_chain.return_value = [primary, fallback]

        result = fetch_batch(["MISSING"], start=date(2024, 1, 1), end=date(2024, 12, 31))

        assert result == {}

    @patch("market_data.fetcher.get_fallback_chain")
    def test_defaults_start_end_when_none(self, mock_chain: MagicMock) -> None:
        primary = _FakeProvider("test", True, {"AAPL": _make_ohlcv()})
        mock_chain.return_value = [primary]

        result = fetch_batch(["AAPL"])

        assert "AAPL" in result

    @patch("market_data.fetcher.get_fallback_chain")
    def test_interval_passed_through(self, mock_chain: MagicMock) -> None:
        primary = _FakeProvider("test", True, {"AAPL": _make_ohlcv()}, intervals=["1d", "1h"])
        mock_chain.return_value = [primary]

        fetch_batch(["AAPL"], start=date(2024, 1, 1), end=date(2024, 12, 31), interval="1h")

        assert primary._last_interval == "1h"

    @patch("market_data.fetcher.get_fallback_chain")
    def test_unsupported_interval_skips_provider(self, mock_chain: MagicMock) -> None:
        daily_only = _FakeProvider("daily_only", True, {"AAPL": _make_ohlcv()}, intervals=["1d"])
        full_support = _FakeProvider("full", True, {"AAPL": _make_ohlcv()}, intervals=["1d", "1h"])
        mock_chain.return_value = [daily_only, full_support]

        result = fetch_batch(["AAPL"], start=date(2024, 1, 1), end=date(2024, 12, 31), interval="1h")

        assert "AAPL" in result
        assert daily_only._last_interval is None
        assert full_support._last_interval == "1h"

    @patch("market_data.fetcher.get_fallback_chain")
    def test_no_provider_supports_interval(self, mock_chain: MagicMock) -> None:
        daily_only = _FakeProvider("daily_only", True, {"AAPL": _make_ohlcv()}, intervals=["1d"])
        mock_chain.return_value = [daily_only]

        result = fetch_batch(["AAPL"], start=date(2024, 1, 1), end=date(2024, 12, 31), interval="1h")

        assert result == {}
