from __future__ import annotations

from pathlib import Path

import pytest

import market_data.watchlist as wl_mod
from market_data.watchlist import Watchlist


@pytest.fixture(autouse=True)
def isolated_watchlist(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wl_mod, "WATCHLIST_PATH", tmp_path / "watchlist.json")


class TestLoadEmpty:
    def test_load_empty(self) -> None:
        result = wl_mod.load_watchlist()
        assert result.tickers == []


class TestAddTicker:
    def test_add_ticker(self) -> None:
        wl_mod.add_ticker("AAPL")
        assert "AAPL" in wl_mod.list_tickers()

    def test_add_duplicate(self) -> None:
        wl_mod.add_ticker("AAPL")
        wl_mod.add_ticker("AAPL")
        assert wl_mod.list_tickers().count("AAPL") == 1

    def test_add_lowercase(self) -> None:
        wl_mod.add_ticker("aapl")
        assert "AAPL" in wl_mod.list_tickers()
        assert "aapl" not in wl_mod.list_tickers()


class TestRemoveTicker:
    def test_remove_ticker(self) -> None:
        wl_mod.add_ticker("MSFT")
        wl_mod.remove_ticker("MSFT")
        assert "MSFT" not in wl_mod.list_tickers()

    def test_remove_nonexistent(self) -> None:
        wl_mod.remove_ticker("NONEXIST")
        assert wl_mod.list_tickers() == []


class TestSortedOrder:
    def test_sorted_order(self) -> None:
        wl_mod.add_ticker("ZZZ")
        wl_mod.add_ticker("AAA")
        wl_mod.add_ticker("MMM")
        tickers = wl_mod.list_tickers()
        assert tickers == sorted(tickers)


class TestPersistence:
    def test_persistence(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        wl_mod.add_ticker("GOOG")
        loaded = wl_mod.load_watchlist()
        assert "GOOG" in loaded.tickers


class TestWatchlistModel:
    def test_model_dedup_and_sort(self) -> None:
        wl = Watchlist(tickers=["MSFT", "AAPL", "AAPL", "msft"])
        assert wl.tickers == ["AAPL", "MSFT"]

    def test_model_uppercase(self) -> None:
        wl = Watchlist(tickers=["tsla"])
        assert wl.tickers == ["TSLA"]
