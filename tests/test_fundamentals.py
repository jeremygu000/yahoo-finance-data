from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from market_data.fundamentals import _cache, get_fundamentals, get_fundamentals_batch, invalidate_cache

_MOCK_INFO: dict[str, Any] = {
    "shortName": "Apple Inc.",
    "longName": "Apple Inc.",
    "sector": "Technology",
    "industry": "Consumer Electronics",
    "marketCap": 3_000_000_000_000,
    "trailingPE": 28.5,
    "forwardPE": 26.1,
    "trailingEps": 6.42,
    "forwardEps": 7.01,
    "dividendYield": 0.005,
    "totalRevenue": 383_000_000_000,
    "profitMargins": 0.26,
    "fiftyTwoWeekHigh": 199.62,
    "fiftyTwoWeekLow": 124.17,
    "averageVolume": 54_000_000,
    "beta": 1.29,
    "currency": "USD",
    "quoteType": "EQUITY",
}


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    _cache.clear()


class TestGetFundamentals:
    @patch("market_data.fundamentals.yf.Ticker")
    def test_returns_all_fields(self, mock_ticker_cls: MagicMock) -> None:
        mock_ticker_cls.return_value.info = _MOCK_INFO
        result = get_fundamentals("AAPL")

        assert result["ticker"] == "AAPL"
        assert result["shortName"] == "Apple Inc."
        assert result["sector"] == "Technology"
        assert result["marketCap"] == 3_000_000_000_000
        assert result["trailingPE"] == 28.5
        assert result["currency"] == "USD"
        assert result["quoteType"] == "EQUITY"

    @patch("market_data.fundamentals.yf.Ticker")
    def test_missing_fields_return_none(self, mock_ticker_cls: MagicMock) -> None:
        mock_ticker_cls.return_value.info = {"shortName": "BTC-USD"}
        result = get_fundamentals("BTC-USD")

        assert result["ticker"] == "BTC-USD"
        assert result["shortName"] == "BTC-USD"
        assert result["sector"] is None
        assert result["marketCap"] is None
        assert result["trailingPE"] is None

    @patch("market_data.fundamentals.yf.Ticker")
    def test_caches_result(self, mock_ticker_cls: MagicMock) -> None:
        mock_ticker_cls.return_value.info = _MOCK_INFO

        result1 = get_fundamentals("AAPL")
        result2 = get_fundamentals("AAPL")

        assert result1 == result2
        mock_ticker_cls.assert_called_once_with("AAPL")

    @patch("market_data.fundamentals.yf.Ticker")
    def test_exception_returns_empty_fields(self, mock_ticker_cls: MagicMock) -> None:
        mock_ticker_cls.return_value.info.__getitem__ = MagicMock(side_effect=Exception("network error"))
        mock_ticker_cls.side_effect = Exception("network error")

        result = get_fundamentals("FAIL")
        assert result["ticker"] == "FAIL"
        assert result["shortName"] is None

    @patch("market_data.fundamentals.yf.Ticker")
    def test_uppercases_ticker(self, mock_ticker_cls: MagicMock) -> None:
        mock_ticker_cls.return_value.info = _MOCK_INFO
        result = get_fundamentals("aapl")
        assert result["ticker"] == "AAPL"


class TestGetFundamentalsBatch:
    @patch("market_data.fundamentals.yf.Ticker")
    def test_returns_list(self, mock_ticker_cls: MagicMock) -> None:
        mock_ticker_cls.return_value.info = _MOCK_INFO
        results = get_fundamentals_batch(["AAPL", "MSFT"])
        assert len(results) == 2
        assert results[0]["ticker"] == "AAPL"
        assert results[1]["ticker"] == "MSFT"


class TestInvalidateCache:
    @patch("market_data.fundamentals.yf.Ticker")
    def test_invalidate_single(self, mock_ticker_cls: MagicMock) -> None:
        mock_ticker_cls.return_value.info = _MOCK_INFO
        get_fundamentals("AAPL")
        assert _cache.get("fundamentals:AAPL") is not None

        invalidate_cache("AAPL")
        assert _cache.get("fundamentals:AAPL") is None

    @patch("market_data.fundamentals.yf.Ticker")
    def test_invalidate_all(self, mock_ticker_cls: MagicMock) -> None:
        mock_ticker_cls.return_value.info = _MOCK_INFO
        get_fundamentals("AAPL")
        get_fundamentals("MSFT")

        invalidate_cache()
        assert _cache.get("fundamentals:AAPL") is None
        assert _cache.get("fundamentals:MSFT") is None


class TestAPIEndpoint:
    def test_fundamentals_endpoint(self) -> None:
        from unittest.mock import patch as _patch

        from starlette.testclient import TestClient

        from market_data.server import app

        mock_result: dict[str, Any] = {
            "ticker": "AAPL",
            "shortName": "Apple Inc.",
            "longName": "Apple Inc.",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "marketCap": 3_000_000_000_000,
            "trailingPE": 28.5,
            "forwardPE": 26.1,
            "trailingEps": 6.42,
            "forwardEps": 7.01,
            "dividendYield": 0.005,
            "totalRevenue": 383_000_000_000,
            "profitMargins": 0.26,
            "fiftyTwoWeekHigh": 199.62,
            "fiftyTwoWeekLow": 124.17,
            "averageVolume": 54_000_000,
            "beta": 1.29,
            "currency": "USD",
            "quoteType": "EQUITY",
        }

        with _patch("market_data.fundamentals.get_fundamentals", return_value=mock_result):
            client = TestClient(app)
            resp = client.get("/api/v1/fundamentals/AAPL?source=live")
            assert resp.status_code == 200
            data = resp.json()
            assert data["ticker"] == "AAPL"
            assert data["short_name"] == "Apple Inc."
            assert data["sector"] == "Technology"
            assert data["market_cap"] == 3_000_000_000_000
            assert data["trailing_pe"] == 28.5
            assert data["quote_type"] == "EQUITY"
