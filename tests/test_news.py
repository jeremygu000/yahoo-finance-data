from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from market_data.news import _cache, get_news, invalidate_cache

_MOCK_NEWS: list[dict[str, Any]] = [
    {
        "id": "abc-123",
        "content": {
            "id": "abc-123",
            "contentType": "STORY",
            "title": "Apple Reports Record Revenue",
            "pubDate": "2024-06-03T08:24:00Z",
            "thumbnail": {
                "originalUrl": "https://img.original.jpg",
                "resolutions": [
                    {"height": 140, "tag": "140x140", "url": "https://img.small.jpg"},
                    {"height": 933, "tag": "original", "url": "https://img.original.jpg"},
                ],
            },
            "provider": {"displayName": "Reuters", "url": "http://reuters.com/"},
            "canonicalUrl": {
                "url": "https://finance.yahoo.com/news/apple-record",
                "site": "finance",
            },
        },
    },
    {
        "id": "def-456",
        "content": {
            "id": "def-456",
            "contentType": "STORY",
            "title": "Tech Stocks Rally",
            "pubDate": "2024-06-02T08:24:00Z",
            "provider": {"displayName": "Motley Fool", "url": "http://fool.com/"},
            "canonicalUrl": {
                "url": "https://finance.yahoo.com/news/tech-rally",
                "site": "finance",
            },
        },
    },
]

_MOCK_NEWS_LEGACY: list[dict[str, Any]] = [
    {
        "uuid": "legacy-1",
        "title": "Legacy Article",
        "link": "https://example.com/legacy",
        "publisher": "OldPub",
        "providerPublishTime": 1717391040,
        "type": "STORY",
        "thumbnail": {
            "resolutions": [
                {"height": 933, "tag": "original", "url": "https://img.legacy.jpg"},
            ]
        },
        "relatedTickers": ["AAPL"],
    },
]


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    _cache.clear()


class TestGetNews:
    @patch("market_data.news.yf.Ticker")
    def test_returns_articles(self, mock_ticker_cls: MagicMock) -> None:
        mock_ticker_cls.return_value.get_news.return_value = _MOCK_NEWS
        result = get_news("AAPL")

        assert result["ticker"] == "AAPL"
        assert result["count"] == 2
        assert len(result["articles"]) == 2
        assert result["articles"][0]["title"] == "Apple Reports Record Revenue"
        assert result["articles"][0]["publisher"] == "Reuters"
        assert result["articles"][0]["uuid"] == "abc-123"
        assert result["articles"][0]["link"] == "https://finance.yahoo.com/news/apple-record"
        assert result["articles"][0]["type"] == "STORY"
        assert result["articles"][0]["providerPublishTime"] is not None

    @patch("market_data.news.yf.Ticker")
    def test_extracts_thumbnail_original_url(self, mock_ticker_cls: MagicMock) -> None:
        mock_ticker_cls.return_value.get_news.return_value = _MOCK_NEWS
        result = get_news("AAPL")

        assert result["articles"][0]["thumbnail_url"] == "https://img.original.jpg"

    @patch("market_data.news.yf.Ticker")
    def test_no_thumbnail_returns_none(self, mock_ticker_cls: MagicMock) -> None:
        mock_ticker_cls.return_value.get_news.return_value = _MOCK_NEWS
        result = get_news("AAPL")

        assert result["articles"][1]["thumbnail_url"] is None

    @patch("market_data.news.yf.Ticker")
    def test_legacy_flat_structure(self, mock_ticker_cls: MagicMock) -> None:
        mock_ticker_cls.return_value.get_news.return_value = _MOCK_NEWS_LEGACY
        result = get_news("AAPL")

        assert result["count"] == 1
        art = result["articles"][0]
        assert art["uuid"] == "legacy-1"
        assert art["title"] == "Legacy Article"
        assert art["publisher"] == "OldPub"
        assert art["link"] == "https://example.com/legacy"
        assert art["thumbnail_url"] == "https://img.legacy.jpg"

    @patch("market_data.news.yf.Ticker")
    def test_caches_result(self, mock_ticker_cls: MagicMock) -> None:
        mock_ticker_cls.return_value.get_news.return_value = _MOCK_NEWS

        result1 = get_news("AAPL")
        result2 = get_news("AAPL")

        assert result1 == result2
        mock_ticker_cls.assert_called_once_with("AAPL")

    @patch("market_data.news.yf.Ticker")
    def test_exception_returns_empty(self, mock_ticker_cls: MagicMock) -> None:
        mock_ticker_cls.side_effect = Exception("network error")
        result = get_news("FAIL")

        assert result["ticker"] == "FAIL"
        assert result["count"] == 0
        assert result["articles"] == []

    @patch("market_data.news.yf.Ticker")
    def test_uppercases_ticker(self, mock_ticker_cls: MagicMock) -> None:
        mock_ticker_cls.return_value.get_news.return_value = []
        result = get_news("aapl")
        assert result["ticker"] == "AAPL"

    @patch("market_data.news.yf.Ticker")
    def test_count_parameter(self, mock_ticker_cls: MagicMock) -> None:
        mock_ticker_cls.return_value.get_news.return_value = _MOCK_NEWS
        get_news("AAPL", count=5)
        mock_ticker_cls.return_value.get_news.assert_called_once_with(count=5)


class TestInvalidateCache:
    @patch("market_data.news.yf.Ticker")
    def test_invalidate_single(self, mock_ticker_cls: MagicMock) -> None:
        mock_ticker_cls.return_value.get_news.return_value = _MOCK_NEWS
        get_news("AAPL")
        assert _cache.get("news:AAPL:10") is not None

        invalidate_cache("AAPL")
        assert _cache.get("news:AAPL:10") is None

    @patch("market_data.news.yf.Ticker")
    def test_invalidate_all(self, mock_ticker_cls: MagicMock) -> None:
        mock_ticker_cls.return_value.get_news.return_value = _MOCK_NEWS
        get_news("AAPL")
        get_news("MSFT")

        invalidate_cache()
        assert _cache.get("news:AAPL:10") is None
        assert _cache.get("news:MSFT:10") is None


class TestAPIEndpoint:
    def test_news_endpoint(self) -> None:
        from unittest.mock import patch as _patch

        from starlette.testclient import TestClient

        from market_data.server import app

        mock_result: dict[str, Any] = {
            "ticker": "AAPL",
            "count": 2,
            "articles": [
                {
                    "uuid": "abc-123",
                    "title": "Apple Reports Record Revenue",
                    "link": "https://finance.yahoo.com/news/apple-record",
                    "publisher": "Reuters",
                    "providerPublishTime": 1717391040,
                    "type": "STORY",
                    "relatedTickers": ["AAPL"],
                    "thumbnail_url": "https://img.original.jpg",
                },
            ],
        }

        with _patch("market_data.news.get_news", return_value=mock_result):
            client = TestClient(app)
            resp = client.get("/api/v1/news/AAPL")
            assert resp.status_code == 200
            data = resp.json()
            assert data["ticker"] == "AAPL"
            assert data["count"] == 2
            assert len(data["articles"]) == 1
            assert data["articles"][0]["title"] == "Apple Reports Record Revenue"
            assert data["articles"][0]["provider_publish_time"] == 1717391040
            assert data["articles"][0]["thumbnail_url"] == "https://img.original.jpg"
