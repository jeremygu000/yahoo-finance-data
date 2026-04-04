from unittest.mock import patch
import io

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from market_data.server import app

client = TestClient(app, raise_server_exceptions=False)


class TestExportOhlcv:
    def test_export_csv_success(self, sample_ohlcv: callable) -> None:
        df = sample_ohlcv(days=5)

        with patch("market_data.server.store.load", return_value=df):
            resp = client.get("/api/v1/export/AAPL?format=csv")

        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in resp.headers["content-disposition"]
        assert "AAPL_ohlcv.csv" in resp.headers["content-disposition"]

        csv_content = resp.text
        lines = csv_content.strip().split("\n")
        assert len(lines) == 6  # header + 5 data rows
        assert "Date,Open,High,Low,Close,Volume" in csv_content

    def test_export_csv_legacy_endpoint(self, sample_ohlcv: callable) -> None:
        df = sample_ohlcv(days=3)

        with patch("market_data.server.store.load", return_value=df):
            resp = client.get("/api/export/AAPL?format=csv")

        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/csv; charset=utf-8"
        assert "AAPL_ohlcv.csv" in resp.headers["content-disposition"]

    def test_export_csv_with_days_param(self, sample_ohlcv: callable) -> None:
        df = sample_ohlcv(days=10)

        with patch("market_data.server.store.load", return_value=df):
            resp = client.get("/api/v1/export/QQQ?format=csv&days=90")

        assert resp.status_code == 200
        csv_content = resp.text
        lines = csv_content.strip().split("\n")
        assert len(lines) == 11  # header + 10 data rows

    def test_export_csv_with_interval_param(self, sample_ohlcv: callable) -> None:
        df = sample_ohlcv(days=5)

        with patch("market_data.server.store.load", return_value=df):
            resp = client.get("/api/v1/export/SPY?format=csv&interval=1h")

        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/csv; charset=utf-8"

    def test_unsupported_format_returns_400(self) -> None:
        resp = client.get("/api/v1/export/AAPL?format=xlsx")

        assert resp.status_code == 400
        body = resp.json()
        assert "Unsupported format" in body["error"]
        assert "xlsx" in body["error"]

    def test_invalid_interval_returns_400(self) -> None:
        resp = client.get("/api/v1/export/AAPL?format=csv&interval=invalid")

        assert resp.status_code == 400
        body = resp.json()
        assert "Invalid interval" in body["error"]

    def test_no_data_found_returns_404(self) -> None:
        empty_df = pd.DataFrame()

        with patch("market_data.server.store.load", return_value=empty_df):
            resp = client.get("/api/v1/export/NONEXISTENT?format=csv")

        assert resp.status_code == 404
        body = resp.json()
        assert "No data found" in body["error"]
        assert "NONEXISTENT" in body["error"]

    def test_csv_content_has_correct_columns(self, sample_ohlcv: callable) -> None:
        df = sample_ohlcv(days=1)

        with patch("market_data.server.store.load", return_value=df):
            resp = client.get("/api/v1/export/XOM?format=csv")

        assert resp.status_code == 200
        csv_content = resp.text
        lines = csv_content.strip().split("\n")
        header = lines[0]
        assert "Date" in header
        assert "Open" in header
        assert "High" in header
        assert "Low" in header
        assert "Close" in header
        assert "Volume" in header

    def test_default_days_is_365(self, sample_ohlcv: callable) -> None:
        df = sample_ohlcv(days=5)

        with patch("market_data.server.store.load", return_value=df) as mock_load:
            resp = client.get("/api/v1/export/CRM?format=csv")

        assert resp.status_code == 200
        mock_load.assert_called_once()
        args, kwargs = mock_load.call_args
        assert args[1] == 365  # days argument

    def test_default_format_is_csv(self, sample_ohlcv: callable) -> None:
        df = sample_ohlcv(days=3)

        with patch("market_data.server.store.load", return_value=df):
            resp = client.get("/api/v1/export/TSLA")

        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/csv; charset=utf-8"

    def test_lowercase_ticker_in_filename(self, sample_ohlcv: callable) -> None:
        df = sample_ohlcv(days=2)

        with patch("market_data.server.store.load", return_value=df):
            resp = client.get("/api/v1/export/spy?format=csv")

        assert resp.status_code == 200
        assert "SPY_ohlcv.csv" in resp.headers["content-disposition"]
