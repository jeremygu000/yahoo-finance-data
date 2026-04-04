from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from market_data.server import app

client = TestClient(app, raise_server_exceptions=False)


class TestSearchTickers:
    def test_search_returns_matching_tickers(self) -> None:
        """Test that search returns matching tickers."""
        with patch("market_data.server.store.list_tickers", return_value=["AAPL", "MSFT", "GOOGL", "AMZN"]):
            resp = client.get("/api/v1/search?q=AA")
            assert resp.status_code == 200
            data = resp.json()
            assert data["query"] == "AA"
            assert len(data["results"]) == 1
            assert data["results"][0]["ticker"] == "AAPL"
            assert data["results"][0]["has_data"] is True

    def test_search_is_case_insensitive(self) -> None:
        """Test that search is case-insensitive."""
        with patch("market_data.server.store.list_tickers", return_value=["AAPL", "MSFT", "GOOGL"]):
            resp = client.get("/api/v1/search?q=aa")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["results"]) == 1
            assert data["results"][0]["ticker"] == "AAPL"

    def test_search_empty_query_returns_empty(self) -> None:
        """Test that empty query returns empty results."""
        with patch("market_data.server.store.list_tickers", return_value=["AAPL", "MSFT", "GOOGL"]):
            resp = client.get("/api/v1/search?q=")
            assert resp.status_code == 200
            data = resp.json()
            assert data["query"] == ""
            assert data["results"] == []

    def test_search_limit_parameter(self) -> None:
        """Test that limit parameter works."""
        with patch("market_data.server.store.list_tickers", return_value=["AAPL", "AMD", "AMZN", "AVGO", "ASML"]):
            resp = client.get("/api/v1/search?q=A&limit=3")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["results"]) == 3
            assert data["results"][0]["ticker"] == "AAPL"
            assert data["results"][1]["ticker"] == "AMD"
            assert data["results"][2]["ticker"] == "AMZN"

    def test_search_partial_match(self) -> None:
        """Test that partial match works (e.g., 'AA' matches 'AAPL')."""
        with patch("market_data.server.store.list_tickers", return_value=["AAPL", "MSFT", "GOOGL", "AMZN"]):
            resp = client.get("/api/v1/search?q=AA")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["results"]) == 1
            assert data["results"][0]["ticker"] == "AAPL"

    def test_search_multiple_matches_sorted(self) -> None:
        """Test that multiple matches are sorted alphabetically."""
        with patch("market_data.server.store.list_tickers", return_value=["AAPL", "ASML", "AMZN", "AMD"]):
            resp = client.get("/api/v1/search?q=A")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["results"]) == 4
            tickers = [r["ticker"] for r in data["results"]]
            assert tickers == ["AAPL", "AMD", "AMZN", "ASML"]

    def test_search_no_matches(self) -> None:
        """Test that search with no matches returns empty results."""
        with patch("market_data.server.store.list_tickers", return_value=["AAPL", "MSFT", "GOOGL"]):
            resp = client.get("/api/v1/search?q=XYZ")
            assert resp.status_code == 200
            data = resp.json()
            assert data["results"] == []

    def test_search_legacy_endpoint(self) -> None:
        """Test that legacy /api/search endpoint works."""
        with patch("market_data.server.store.list_tickers", return_value=["AAPL", "MSFT", "GOOGL"]):
            resp = client.get("/api/search?q=MS")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["results"]) == 1
            assert data["results"][0]["ticker"] == "MSFT"

    def test_search_limit_max_50(self) -> None:
        """Test that limit parameter is capped at 50."""
        tickers = [f"T{i:02d}" for i in range(100)]
        with patch("market_data.server.store.list_tickers", return_value=tickers):
            resp = client.get("/api/v1/search?q=T&limit=50")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["results"]) == 50

    def test_search_limit_min_1(self) -> None:
        """Test that limit parameter minimum is 1."""
        with patch("market_data.server.store.list_tickers", return_value=["AAPL", "MSFT"]):
            resp = client.get("/api/v1/search?q=&limit=0")
            assert resp.status_code == 422  # validation error
