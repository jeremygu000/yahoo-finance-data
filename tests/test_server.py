from unittest.mock import patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from market_data.exceptions import InvalidTickerError, TickerNotFoundError
from market_data.server import app

client = TestClient(app, raise_server_exceptions=False)


class TestHealth:
    def test_health(self) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
        assert "x-request-id" in resp.headers

    def test_ready_dir_exists(self, tmp_path, sample_ohlcv) -> None:
        from market_data import store

        df = sample_ohlcv(days=3)
        store.save("SPY", df, data_dir=tmp_path)

        with patch("market_data.server.store.list_tickers", return_value=["SPY"]):
            with patch("market_data.config.DATA_DIR", tmp_path):
                resp = client.get("/ready")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ready"
        assert body["data_dir_exists"] is True
        assert body["ticker_count"] == 1


_MOCK_TICKER_STATUS = {
    "ticker": "AAPL",
    "rows": 5,
    "first_date": "2025-01-01",
    "last_date": "2025-01-05",
    "size_kb": 1.2,
}


class TestGetTickers:
    def test_returns_list(self, tmp_path, sample_ohlcv) -> None:
        from market_data import store

        df = sample_ohlcv(days=5)
        store.save("AAPL", df, data_dir=tmp_path)

        with patch("market_data.server.store.status", return_value=[_MOCK_TICKER_STATUS]):
            resp = client.get("/api/tickers")

        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert data[0]["ticker"] == "AAPL"

    def test_v1_returns_list(self, tmp_path, sample_ohlcv) -> None:
        from market_data import store

        df = sample_ohlcv(days=5)
        store.save("AAPL", df, data_dir=tmp_path)

        with patch("market_data.server.store.status", return_value=[_MOCK_TICKER_STATUS]):
            resp = client.get("/api/v1/tickers")

        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert data[0]["ticker"] == "AAPL"


class TestGetOhlcv:
    def test_success(self, sample_ohlcv) -> None:
        df = sample_ohlcv(days=5)

        with patch("market_data.server.store.load", return_value=df):
            resp = client.get("/api/ohlcv/AAPL")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 5
        assert set(data[0].keys()) == {"date", "time", "open", "high", "low", "close", "volume"}

    def test_v1_success(self, sample_ohlcv) -> None:
        df = sample_ohlcv(days=5)

        with patch("market_data.server.store.load", return_value=df):
            resp = client.get("/api/v1/ohlcv/AAPL")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 5
        assert set(data[0].keys()) == {"date", "time", "open", "high", "low", "close", "volume"}

    def test_empty(self) -> None:
        with patch("market_data.server.store.load", return_value=pd.DataFrame()):
            resp = client.get("/api/ohlcv/AAPL")

        assert resp.status_code == 200
        assert resp.json() == []

    def test_days_param(self, sample_ohlcv) -> None:
        df = sample_ohlcv(days=10)

        with patch("market_data.server.store.load", return_value=df) as mock_load:
            resp = client.get("/api/ohlcv/SPY", params={"days": 30})

        assert resp.status_code == 200
        mock_load.assert_called_once_with("SPY", 30)

    def test_days_validation(self) -> None:
        resp = client.get("/api/ohlcv/SPY", params={"days": 0})
        assert resp.status_code == 422

        resp = client.get("/api/ohlcv/SPY", params={"days": 9999})
        assert resp.status_code == 422

    def test_pagination_limit(self, sample_ohlcv) -> None:
        df = sample_ohlcv(days=10)

        with patch("market_data.server.store.load", return_value=df):
            resp = client.get("/api/ohlcv/SPY", params={"limit": 3})

        assert resp.status_code == 200
        assert len(resp.json()) == 3

    def test_pagination_offset(self, sample_ohlcv) -> None:
        df = sample_ohlcv(days=10)

        with patch("market_data.server.store.load", return_value=df):
            all_resp = client.get("/api/ohlcv/SPY")
            offset_resp = client.get("/api/ohlcv/SPY", params={"offset": 5})

        all_data = all_resp.json()
        offset_data = offset_resp.json()
        assert len(offset_data) == 5
        assert offset_data[0] == all_data[5]

    def test_pagination_limit_and_offset(self, sample_ohlcv) -> None:
        df = sample_ohlcv(days=10)

        with patch("market_data.server.store.load", return_value=df):
            resp = client.get("/api/ohlcv/SPY", params={"limit": 2, "offset": 3})

        assert resp.status_code == 200
        assert len(resp.json()) == 2


class TestGetLatest:
    def test_success(self) -> None:
        latest = {"date": "2025-01-01", "close": 100.0}

        with patch("market_data.api.get_latest", return_value=latest):
            resp = client.get("/api/latest/AAPL")

        assert resp.status_code == 200
        assert resp.json() == latest

    def test_missing(self) -> None:
        with patch("market_data.api.get_latest", return_value=None):
            resp = client.get("/api/latest/NONEXIST")

        assert resp.status_code == 200
        assert resp.json() is None


class TestCompare:
    def test_multiple_tickers(self, sample_ohlcv) -> None:
        df = sample_ohlcv(days=5)

        with patch("market_data.server.store.load", return_value=df):
            resp = client.get("/api/compare", params={"tickers": "AAPL,GOOG"})

        assert resp.status_code == 200
        data = resp.json()
        assert "AAPL" in data
        assert "GOOG" in data
        assert len(data["AAPL"]) == 5
        assert set(data["AAPL"][0].keys()) == {"date", "time", "close"}


class TestExceptionHandlers:
    def test_invalid_ticker_returns_400(self) -> None:
        with patch(
            "market_data.server.store.load",
            side_effect=InvalidTickerError("BAD!", "invalid chars"),
        ):
            resp = client.get("/api/ohlcv/BAD!")

        assert resp.status_code == 400
        assert "error" in resp.json()

    def test_ticker_not_found_returns_404(self) -> None:
        with patch(
            "market_data.server.store.load",
            side_effect=TickerNotFoundError("MISSING"),
        ):
            resp = client.get("/api/ohlcv/MISSING")

        assert resp.status_code == 404
        assert "MISSING" in resp.json()["error"]

    def test_unhandled_error_returns_500(self) -> None:
        with patch(
            "market_data.server.store.load",
            side_effect=RuntimeError("kaboom"),
        ):
            resp = client.get("/api/ohlcv/AAPL")

        assert resp.status_code == 500
        body = resp.json()
        assert "error" in body
        assert "request_id" in body


class TestRateLimit:
    def test_rate_limit_exceeded(self) -> None:
        from market_data.server import RATE_LIMIT_REQUESTS, _request_log

        _request_log.clear()
        for _ in range(RATE_LIMIT_REQUESTS):
            resp = client.get("/health")
            assert resp.status_code == 200

        resp = client.get("/health")
        assert resp.status_code == 429
        assert resp.json()["error"] == "Rate limit exceeded"
        assert "retry-after" in resp.headers
        _request_log.clear()


class TestWebSocket:
    def test_ws_connect_and_disconnect(self) -> None:
        with client.websocket_connect("/ws/prices") as ws:
            assert ws is not None

    def test_ws_receives_price_update(self) -> None:
        import json

        mock_latest = {
            "date": "2025-01-01",
            "open": 100.0,
            "high": 105.0,
            "low": 99.0,
            "close": 104.0,
            "volume": 1000,
        }

        with client.websocket_connect("/ws/prices") as ws:
            with (
                patch("market_data.server.store.list_tickers", return_value=["AAPL"]),
                patch("market_data.api.get_latest", return_value=mock_latest),
            ):
                from market_data.server import _ws_clients, _broadcast, WSMessage, PriceUpdate

                import asyncio

                update = PriceUpdate(
                    ticker="AAPL", date="2025-01-01", open=100.0, high=105.0, low=99.0, close=104.0, volume=1000
                )
                msg = WSMessage(type="price_update", data=[update])
                loop = asyncio.new_event_loop()
                loop.run_until_complete(_broadcast(msg))
                loop.close()

            data = ws.receive_json()
            assert data["type"] == "price_update"
            assert len(data["data"]) == 1
            assert data["data"][0]["ticker"] == "AAPL"
            assert data["data"][0]["close"] == 104.0
