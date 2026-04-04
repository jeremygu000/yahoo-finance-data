from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from market_data import fundamentals_store as fs

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
    "priceToBook": 48.5,
    "priceToSalesTrailing12Months": 8.5,
    "pegRatio": 2.1,
    "enterpriseValue": 3_100_000_000_000,
    "enterpriseToEbitda": 24.3,
    "dividendYield": 0.005,
    "beta": 1.29,
    "regularMarketPrice": 178.50,
    "currentPrice": 178.50,
    "currency": "USD",
    "targetLowPrice": 150.0,
    "targetHighPrice": 220.0,
    "targetMeanPrice": 195.0,
    "targetMedianPrice": 198.0,
    "numberOfAnalystOpinions": 38,
    "recommendationKey": "buy",
    "recommendationMean": 2.1,
    "shortRatio": 1.5,
    "shortPercentOfFloat": 0.007,
    "sharesShort": 120_000_000,
    "totalRevenue": 383_000_000_000,
    "revenueGrowth": 0.05,
    "grossMargins": 0.45,
    "operatingMargins": 0.30,
    "profitMargins": 0.26,
    "earningsQuarterlyGrowth": 0.10,
    "earningsGrowth": 0.08,
    "returnOnEquity": 1.47,
    "debtToEquity": 176.3,
    "fiftyTwoWeekHigh": 199.62,
    "fiftyTwoWeekLow": 124.17,
    "averageVolume": 54_000_000,
    "quoteType": "EQUITY",
}


def _mock_recommendations() -> pd.DataFrame:
    idx = pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01"])
    return pd.DataFrame(
        {
            "period": ["0m", "-1m", "-2m"],
            "strongBuy": [10, 12, 8],
            "buy": [20, 18, 22],
            "hold": [5, 6, 4],
            "sell": [1, 0, 2],
            "strongSell": [0, 0, 1],
        },
        index=idx,
    )


def _mock_earnings_dates() -> pd.DataFrame:
    idx = pd.to_datetime(["2024-01-25", "2024-04-25"])
    return pd.DataFrame(
        {
            "EPS Estimate": [2.10, 1.95],
            "Reported EPS": [2.18, 2.01],
            "Surprise(%)": [3.8, 3.1],
        },
        index=idx,
    )


def _mock_upgrades_downgrades() -> pd.DataFrame:
    idx = pd.to_datetime(["2024-02-01", "2024-03-15"])
    return pd.DataFrame(
        {
            "Firm": ["Goldman Sachs", "Morgan Stanley"],
            "ToGrade": ["Buy", "Overweight"],
            "FromGrade": ["Neutral", "Equal-Weight"],
            "Action": ["upgrade", "upgrade"],
        },
        index=idx,
    )


class TestFetchAndSaveFundamentals:
    @patch("market_data.fundamentals_store.yf.Ticker")
    def test_saves_and_loads(self, mock_ticker_cls: MagicMock, tmp_path: Path) -> None:
        mock_ticker_cls.return_value.info = _MOCK_INFO.copy()

        result = fs.fetch_and_save_fundamentals("AAPL", data_dir=tmp_path)

        assert result["ticker"] == "AAPL"
        assert result["marketCap"] == 3_000_000_000_000
        assert "fetched_at" in result

        path = tmp_path / "AAPL_fundamentals.parquet"
        assert path.exists()

        loaded = fs.load_fundamentals("AAPL", data_dir=tmp_path)
        assert loaded is not None
        assert loaded["ticker"] == "AAPL"
        assert loaded["marketCap"] == 3_000_000_000_000
        assert loaded["sector"] == "Technology"

    @patch("market_data.fundamentals_store.yf.Ticker")
    def test_dedup_by_day(self, mock_ticker_cls: MagicMock, tmp_path: Path) -> None:
        mock_ticker_cls.return_value.info = _MOCK_INFO.copy()

        fs.fetch_and_save_fundamentals("AAPL", data_dir=tmp_path)
        fs.fetch_and_save_fundamentals("AAPL", data_dir=tmp_path)

        df = pd.read_parquet(tmp_path / "AAPL_fundamentals.parquet")
        assert len(df) == 1

    @patch("market_data.fundamentals_store.yf.Ticker")
    def test_missing_keys_stored_as_none(self, mock_ticker_cls: MagicMock, tmp_path: Path) -> None:
        mock_ticker_cls.return_value.info = {"shortName": "BTC"}

        fs.fetch_and_save_fundamentals("BTC-USD", data_dir=tmp_path)

        loaded = fs.load_fundamentals("BTC-USD", data_dir=tmp_path)
        assert loaded is not None
        assert loaded["shortName"] == "BTC"
        assert loaded["marketCap"] is None
        assert loaded["sector"] is None

    @patch("market_data.fundamentals_store.yf.Ticker")
    def test_yfinance_error_returns_empty(self, mock_ticker_cls: MagicMock, tmp_path: Path) -> None:
        mock_ticker_cls.side_effect = Exception("network error")

        result = fs.fetch_and_save_fundamentals("FAIL", data_dir=tmp_path)
        assert result == {}

    def test_load_missing_returns_none(self, tmp_path: Path) -> None:
        loaded = fs.load_fundamentals("NONEXISTENT", data_dir=tmp_path)
        assert loaded is None


class TestFetchAndSaveRecommendations:
    @patch("market_data.fundamentals_store.yf.Ticker")
    def test_saves_and_loads(self, mock_ticker_cls: MagicMock, tmp_path: Path) -> None:
        mock_ticker_cls.return_value.recommendations = _mock_recommendations()

        count = fs.fetch_and_save_recommendations("AAPL", data_dir=tmp_path)
        assert count == 3

        loaded = fs.load_recommendations("AAPL", data_dir=tmp_path)
        assert not loaded.empty
        assert len(loaded) == 3
        assert "strongBuy" in loaded.columns

    @patch("market_data.fundamentals_store.yf.Ticker")
    def test_merge_dedup(self, mock_ticker_cls: MagicMock, tmp_path: Path) -> None:
        mock_ticker_cls.return_value.recommendations = _mock_recommendations()

        fs.fetch_and_save_recommendations("AAPL", data_dir=tmp_path)
        fs.fetch_and_save_recommendations("AAPL", data_dir=tmp_path)

        loaded = fs.load_recommendations("AAPL", data_dir=tmp_path)
        assert len(loaded) == 3

    @patch("market_data.fundamentals_store.yf.Ticker")
    def test_none_returns_zero(self, mock_ticker_cls: MagicMock, tmp_path: Path) -> None:
        mock_ticker_cls.return_value.recommendations = None
        assert fs.fetch_and_save_recommendations("AAPL", data_dir=tmp_path) == 0

    def test_load_missing_returns_empty(self, tmp_path: Path) -> None:
        loaded = fs.load_recommendations("NONEXISTENT", data_dir=tmp_path)
        assert loaded.empty


class TestFetchAndSaveEarningsDates:
    @patch("market_data.fundamentals_store.yf.Ticker")
    def test_saves_and_loads(self, mock_ticker_cls: MagicMock, tmp_path: Path) -> None:
        mock_ticker_cls.return_value.earnings_dates = _mock_earnings_dates()

        count = fs.fetch_and_save_earnings_dates("AAPL", data_dir=tmp_path)
        assert count == 2

        loaded = fs.load_earnings_dates("AAPL", data_dir=tmp_path)
        assert not loaded.empty
        assert len(loaded) == 2
        assert "EPS Estimate" in loaded.columns

    @patch("market_data.fundamentals_store.yf.Ticker")
    def test_none_returns_zero(self, mock_ticker_cls: MagicMock, tmp_path: Path) -> None:
        mock_ticker_cls.return_value.earnings_dates = None
        assert fs.fetch_and_save_earnings_dates("AAPL", data_dir=tmp_path) == 0

    def test_load_missing_returns_empty(self, tmp_path: Path) -> None:
        loaded = fs.load_earnings_dates("NONEXISTENT", data_dir=tmp_path)
        assert loaded.empty


class TestFetchAndSaveUpgradesDowngrades:
    @patch("market_data.fundamentals_store.yf.Ticker")
    def test_saves_and_loads(self, mock_ticker_cls: MagicMock, tmp_path: Path) -> None:
        mock_ticker_cls.return_value.upgrades_downgrades = _mock_upgrades_downgrades()

        count = fs.fetch_and_save_upgrades_downgrades("AAPL", data_dir=tmp_path)
        assert count == 2

        loaded = fs.load_upgrades_downgrades("AAPL", data_dir=tmp_path)
        assert not loaded.empty
        assert len(loaded) == 2
        assert "Firm" in loaded.columns

    @patch("market_data.fundamentals_store.yf.Ticker")
    def test_none_returns_zero(self, mock_ticker_cls: MagicMock, tmp_path: Path) -> None:
        mock_ticker_cls.return_value.upgrades_downgrades = None
        assert fs.fetch_and_save_upgrades_downgrades("AAPL", data_dir=tmp_path) == 0

    def test_load_missing_returns_empty(self, tmp_path: Path) -> None:
        loaded = fs.load_upgrades_downgrades("NONEXISTENT", data_dir=tmp_path)
        assert loaded.empty


class TestFetchAllFundamentalData:
    @patch("market_data.fundamentals_store.yf.Ticker")
    @patch("market_data.fundamentals_store.time.sleep")
    def test_fetches_all_types(self, mock_sleep: MagicMock, mock_ticker_cls: MagicMock, tmp_path: Path) -> None:
        inst = mock_ticker_cls.return_value
        inst.info = _MOCK_INFO.copy()
        inst.recommendations = _mock_recommendations()
        inst.earnings_dates = _mock_earnings_dates()
        inst.upgrades_downgrades = _mock_upgrades_downgrades()

        result = fs.fetch_all_fundamental_data("AAPL", data_dir=tmp_path, delay=0)
        assert result["ticker"] == "AAPL"
        assert result["fundamentals"] is True
        assert result["recommendations"] == 3
        assert result["earnings_dates"] == 2
        assert result["upgrades_downgrades"] == 2

        assert (tmp_path / "AAPL_fundamentals.parquet").exists()
        assert (tmp_path / "AAPL_recommendations.parquet").exists()
        assert (tmp_path / "AAPL_earnings_dates.parquet").exists()
        assert (tmp_path / "AAPL_upgrades_downgrades.parquet").exists()


class TestFundamentalsAPI:
    def _client(self) -> Any:
        from starlette.testclient import TestClient

        from market_data.server import app

        return TestClient(app)

    def test_fundamentals_source_live(self) -> None:
        mock_result: dict[str, Any] = {
            "ticker": "AAPL",
            **{k: _MOCK_INFO.get(k) for k in fs._ALL_INFO_KEYS},
        }
        with patch("market_data.fundamentals.get_fundamentals", return_value=mock_result):
            resp = self._client().get("/api/v1/fundamentals/AAPL?source=live")
            assert resp.status_code == 200
            data = resp.json()
            assert data["ticker"] == "AAPL"
            assert data["source"] == "live"
            assert data["market_cap"] == 3_000_000_000_000
            assert data["trailing_pe"] == 28.5
            assert data["sector"] == "Technology"
            assert data["return_on_equity"] == 1.47
            assert data["debt_to_equity"] == 176.3

    def test_fundamentals_source_local_404(self) -> None:
        with patch("market_data.fundamentals_store.load_fundamentals", return_value=None):
            resp = self._client().get("/api/v1/fundamentals/AAPL?source=local")
            assert resp.status_code == 404

    def test_fundamentals_source_local_ok(self) -> None:
        local_data: dict[str, Any] = {
            "ticker": "AAPL",
            "fetched_at": "2024-01-01 00:00:00+00:00",
            **{k: _MOCK_INFO.get(k) for k in fs._ALL_INFO_KEYS},
        }
        with patch("market_data.fundamentals_store.load_fundamentals", return_value=local_data):
            resp = self._client().get("/api/v1/fundamentals/AAPL?source=local")
            assert resp.status_code == 200
            data = resp.json()
            assert data["source"] == "local"
            assert data["market_cap"] == 3_000_000_000_000

    def test_fundamentals_source_auto_fallback(self) -> None:
        mock_live: dict[str, Any] = {
            "ticker": "AAPL",
            **{k: _MOCK_INFO.get(k) for k in fs._ALL_INFO_KEYS},
        }
        with (
            patch("market_data.fundamentals_store.load_fundamentals", return_value=None),
            patch("market_data.fundamentals.get_fundamentals", return_value=mock_live),
        ):
            resp = self._client().get("/api/v1/fundamentals/AAPL?source=auto")
            assert resp.status_code == 200
            data = resp.json()
            assert data["source"] == "live"

    def test_recommendations_endpoint_404(self) -> None:
        with patch("market_data.fundamentals_store.load_recommendations", return_value=pd.DataFrame()):
            resp = self._client().get("/api/v1/fundamentals/AAPL/recommendations")
            assert resp.status_code == 404

    def test_recommendations_endpoint_ok(self) -> None:
        with patch("market_data.fundamentals_store.load_recommendations", return_value=_mock_recommendations()):
            resp = self._client().get("/api/v1/fundamentals/AAPL/recommendations")
            assert resp.status_code == 200
            data = resp.json()
            assert data["ticker"] == "AAPL"
            assert data["count"] == 3
            assert len(data["items"]) == 3
            assert data["items"][0]["strong_buy"] == 10

    def test_earnings_endpoint_404(self) -> None:
        with patch("market_data.fundamentals_store.load_earnings_dates", return_value=pd.DataFrame()):
            resp = self._client().get("/api/v1/fundamentals/AAPL/earnings")
            assert resp.status_code == 404

    def test_earnings_endpoint_ok(self) -> None:
        with patch("market_data.fundamentals_store.load_earnings_dates", return_value=_mock_earnings_dates()):
            resp = self._client().get("/api/v1/fundamentals/AAPL/earnings")
            assert resp.status_code == 200
            data = resp.json()
            assert data["ticker"] == "AAPL"
            assert data["count"] == 2
            assert data["items"][0]["eps_estimate"] == 2.10
            assert data["items"][0]["reported_eps"] == 2.18

    def test_upgrades_endpoint_404(self) -> None:
        with patch("market_data.fundamentals_store.load_upgrades_downgrades", return_value=pd.DataFrame()):
            resp = self._client().get("/api/v1/fundamentals/AAPL/upgrades")
            assert resp.status_code == 404

    def test_upgrades_endpoint_ok(self) -> None:
        with patch("market_data.fundamentals_store.load_upgrades_downgrades", return_value=_mock_upgrades_downgrades()):
            resp = self._client().get("/api/v1/fundamentals/AAPL/upgrades")
            assert resp.status_code == 200
            data = resp.json()
            assert data["ticker"] == "AAPL"
            assert data["count"] == 2
            assert data["items"][0]["firm"] == "Goldman Sachs"
            assert data["items"][0]["to_grade"] == "Buy"
            assert data["items"][0]["action"] == "upgrade"


class TestCLI:
    @patch("market_data.fundamentals_store.yf.Ticker")
    @patch("market_data.fundamentals_store.time.sleep")
    def test_cmd_fetch_fundamentals(self, mock_sleep: MagicMock, mock_ticker_cls: MagicMock, tmp_path: Path) -> None:
        import argparse

        from market_data.cli import cmd_fetch_fundamentals

        inst = mock_ticker_cls.return_value
        inst.info = _MOCK_INFO.copy()
        inst.recommendations = _mock_recommendations()
        inst.earnings_dates = _mock_earnings_dates()
        inst.upgrades_downgrades = _mock_upgrades_downgrades()

        args = argparse.Namespace(tickers="AAPL,MSFT")
        cmd_fetch_fundamentals(args)

        assert mock_ticker_cls.call_count >= 2

    @patch("market_data.cli._fetch_fundamentals_for")
    @patch("market_data.cli.fetch_batch")
    @patch("market_data.cli._filter_stale")
    def test_skip_fundamentals_flag(
        self,
        mock_filter: MagicMock,
        mock_fetch_batch: MagicMock,
        mock_fund: MagicMock,
    ) -> None:
        import argparse

        from market_data.cli import cmd_fetch

        mock_filter.return_value = ([], ["AAPL"])

        args = argparse.Namespace(tickers="AAPL", full=False, skip_fundamentals=True)
        cmd_fetch(args)

        mock_fund.assert_not_called()

    @patch("market_data.cli._fetch_fundamentals_for")
    @patch("market_data.cli._filter_stale")
    def test_fetch_calls_fundamentals_by_default(
        self,
        mock_filter: MagicMock,
        mock_fund: MagicMock,
    ) -> None:
        import argparse

        from market_data.cli import cmd_fetch

        mock_filter.return_value = ([], ["AAPL"])

        args = argparse.Namespace(tickers="AAPL", full=False, skip_fundamentals=False)
        cmd_fetch(args)

        mock_fund.assert_called_once()
