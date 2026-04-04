from unittest.mock import patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from market_data.exceptions import InvalidTickerError, TickerNotFoundError
from market_data.server import app
import market_data.watchlist as wl_mod
import market_data.alerts as alerts_mod

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
            with patch("market_data.server.DATA_DIR", tmp_path):
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
        mock_load.assert_called_once()
        args, kwargs = mock_load.call_args
        assert args[0] == "SPY"
        assert args[1] == 30

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

        with patch("market_data.server.duckdb_reader.compare_close", return_value={"AAPL": df, "GOOG": df}):
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


class TestGetOhlcvInterval:
    def test_ohlcv_with_interval(self, sample_ohlcv) -> None:
        df = sample_ohlcv(days=5)

        with patch("market_data.server.store.load", return_value=df):
            resp = client.get("/api/v1/ohlcv/AAPL", params={"interval": "1h"})

        assert resp.status_code == 200

    def test_ohlcv_invalid_interval(self) -> None:
        resp = client.get("/api/v1/ohlcv/AAPL", params={"interval": "3m"})
        assert resp.status_code == 400
        assert "error" in resp.json()

    def test_compare_with_interval(self, sample_ohlcv) -> None:
        df = sample_ohlcv(days=5)

        with patch("market_data.server.duckdb_reader.compare_close", return_value={"AAPL": df, "GOOG": df}):
            resp = client.get("/api/v1/compare", params={"tickers": "AAPL,GOOG", "interval": "1h"})

        assert resp.status_code == 200

    def test_compare_invalid_interval(self) -> None:
        resp = client.get("/api/v1/compare", params={"tickers": "AAPL", "interval": "3m"})
        assert resp.status_code == 400
        assert "error" in resp.json()


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
                from market_data.server import _ws_subscriptions, _broadcast, WSMessage, PriceUpdate

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

    def test_ws_subscribe(self) -> None:
        with client.websocket_connect("/ws/prices") as ws:
            ws.send_json({"action": "subscribe", "tickers": ["AAPL", "MSFT"]})
            ack = ws.receive_json()
            assert ack["type"] == "subscribed"
            assert "AAPL" in ack["tickers"]
            assert "MSFT" in ack["tickers"]

    def test_ws_unsubscribe(self) -> None:
        with client.websocket_connect("/ws/prices") as ws:
            ws.send_json({"action": "subscribe", "tickers": ["AAPL", "MSFT", "GOOGL"]})
            ws.receive_json()
            ws.send_json({"action": "unsubscribe", "tickers": ["MSFT"]})
            ack = ws.receive_json()
            assert ack["type"] == "unsubscribed"
            assert "MSFT" not in ack["tickers"]
            assert "AAPL" in ack["tickers"]
            assert "GOOGL" in ack["tickers"]

    def test_ws_heartbeat_pong(self) -> None:
        with client.websocket_connect("/ws/prices") as ws:
            import asyncio
            from market_data.server import _heartbeat, _ws_subscriptions

            loop = asyncio.new_event_loop()
            task = loop.create_task(_heartbeat())
            loop.run_until_complete(asyncio.sleep(0.01))
            task.cancel()
            try:
                loop.run_until_complete(task)
            except asyncio.CancelledError:
                pass
            loop.close()

    def test_ws_filtered_broadcast(self) -> None:
        import asyncio
        from market_data.server import _ws_subscriptions, _broadcast, WSMessage, PriceUpdate

        with client.websocket_connect("/ws/prices") as ws:
            ws.send_json({"action": "subscribe", "tickers": ["AAPL"]})
            ws.receive_json()

            aapl = PriceUpdate(
                ticker="AAPL", date="2025-01-01", open=100.0, high=105.0, low=99.0, close=104.0, volume=1000
            )
            msft = PriceUpdate(
                ticker="MSFT", date="2025-01-01", open=200.0, high=210.0, low=199.0, close=208.0, volume=2000
            )
            msg = WSMessage(type="price_update", data=[aapl, msft])
            loop = asyncio.new_event_loop()
            loop.run_until_complete(_broadcast(msg, filter_tickers=["AAPL", "MSFT"]))
            loop.close()

            data = ws.receive_json()
            assert data["type"] == "price_update"
            tickers_received = [d["ticker"] for d in data["data"]]
            assert "AAPL" in tickers_received
            assert "MSFT" not in tickers_received


class TestWatchlist:
    @pytest.fixture(autouse=True)
    def isolated_watchlist(self, tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(wl_mod, "WATCHLIST_PATH", tmp_path / "watchlist.json")

    def test_get_empty_watchlist(self) -> None:
        resp = client.get("/api/v1/watchlist")
        assert resp.status_code == 200
        assert resp.json() == {"tickers": []}

    def test_add_to_watchlist(self) -> None:
        resp = client.post("/api/v1/watchlist", json={"ticker": "AAPL"})
        assert resp.status_code == 200
        assert "AAPL" in resp.json()["tickers"]

    def test_delete_from_watchlist(self) -> None:
        client.post("/api/v1/watchlist", json={"ticker": "MSFT"})
        resp = client.delete("/api/v1/watchlist/MSFT")
        assert resp.status_code == 200
        assert "MSFT" not in resp.json()["tickers"]

    def test_add_duplicate_watchlist(self) -> None:
        client.post("/api/v1/watchlist", json={"ticker": "GOOG"})
        client.post("/api/v1/watchlist", json={"ticker": "GOOG"})
        resp = client.get("/api/v1/watchlist")
        assert resp.json()["tickers"].count("GOOG") == 1


class TestAlerts:
    @pytest.fixture(autouse=True)
    def isolated_alerts(self, tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(alerts_mod, "ALERTS_PATH", tmp_path / "alerts.json")

    def test_get_empty_alerts(self) -> None:
        resp = client.get("/api/v1/alerts")
        assert resp.status_code == 200
        assert resp.json() == {"alerts": []}

    def test_create_alert(self) -> None:
        resp = client.post(
            "/api/v1/alerts",
            json={"ticker": "AAPL", "condition": "above", "threshold": 200.0},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ticker"] == "AAPL"
        assert body["condition"] == "above"
        assert body["threshold"] == 200.0
        assert "id" in body

    def test_get_alerts_after_create(self) -> None:
        client.post("/api/v1/alerts", json={"ticker": "AAPL", "condition": "above", "threshold": 200.0})
        resp = client.get("/api/v1/alerts")
        assert resp.status_code == 200
        assert len(resp.json()["alerts"]) == 1

    def test_get_alerts_with_ticker_filter(self) -> None:
        client.post("/api/v1/alerts", json={"ticker": "AAPL", "condition": "above", "threshold": 200.0})
        client.post("/api/v1/alerts", json={"ticker": "MSFT", "condition": "below", "threshold": 50.0})
        resp = client.get("/api/v1/alerts", params={"ticker": "AAPL"})
        assert resp.status_code == 200
        alerts = resp.json()["alerts"]
        assert len(alerts) == 1
        assert alerts[0]["ticker"] == "AAPL"

    def test_delete_alert(self) -> None:
        create_resp = client.post(
            "/api/v1/alerts",
            json={"ticker": "AAPL", "condition": "above", "threshold": 200.0},
        )
        alert_id = create_resp.json()["id"]
        resp = client.delete(f"/api/v1/alerts/{alert_id}")
        assert resp.status_code == 200
        assert resp.json() == {"alerts": []}

    def test_create_alert_lowercase_ticker(self) -> None:
        resp = client.post(
            "/api/v1/alerts",
            json={"ticker": "aapl", "condition": "above", "threshold": 200.0},
        )
        assert resp.status_code == 200
        assert resp.json()["ticker"] == "AAPL"

    def test_create_alert_with_cooldown(self) -> None:
        resp = client.post(
            "/api/v1/alerts",
            json={"ticker": "AAPL", "condition": "percent_change_above", "threshold": 5.0, "cooldown_seconds": 600},
        )
        assert resp.status_code == 200
        assert resp.json()["cooldown_seconds"] == 600
