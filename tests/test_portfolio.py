from __future__ import annotations

import json
from pathlib import Path

import pytest

import market_data.portfolio as portfolio_mod
from market_data.portfolio import (
    Holding,
    Portfolio,
    add_holding,
    list_holdings,
    load_portfolio,
    remove_holding,
    save_portfolio,
    update_holding,
)


@pytest.fixture(autouse=True)
def isolated_portfolio(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(portfolio_mod, "PORTFOLIO_PATH", tmp_path / "portfolio.json")


class TestLoadEmpty:
    def test_load_empty(self) -> None:
        result = load_portfolio()
        assert result.holdings == []

    def test_list_empty(self) -> None:
        assert list_holdings() == []


class TestAddHolding:
    def test_add_holding(self) -> None:
        add_holding("AAPL", 10.0, 150.0)
        holdings = list_holdings()
        assert len(holdings) == 1
        assert holdings[0].ticker == "AAPL"
        assert holdings[0].shares == 10.0
        assert holdings[0].avg_cost == 150.0

    def test_add_normalises_ticker(self) -> None:
        add_holding("aapl", 5.0, 100.0)
        holdings = list_holdings()
        assert holdings[0].ticker == "AAPL"

    def test_add_multiple(self) -> None:
        add_holding("AAPL", 10.0, 150.0)
        add_holding("MSFT", 5.0, 300.0)
        holdings = list_holdings()
        assert len(holdings) == 2

    def test_add_replaces_existing(self) -> None:
        add_holding("AAPL", 10.0, 150.0)
        add_holding("AAPL", 20.0, 160.0)
        holdings = list_holdings()
        assert len(holdings) == 1
        assert holdings[0].shares == 20.0
        assert holdings[0].avg_cost == 160.0

    def test_add_sorted_order(self) -> None:
        add_holding("ZZZ", 1.0, 10.0)
        add_holding("AAA", 1.0, 10.0)
        add_holding("MMM", 1.0, 10.0)
        tickers = [h.ticker for h in list_holdings()]
        assert tickers == sorted(tickers)

    def test_added_at_populated(self) -> None:
        add_holding("AAPL", 10.0, 150.0)
        holdings = list_holdings()
        assert holdings[0].added_at != ""


class TestRemoveHolding:
    def test_remove_holding(self) -> None:
        add_holding("AAPL", 10.0, 150.0)
        remove_holding("AAPL")
        assert list_holdings() == []

    def test_remove_nonexistent(self) -> None:
        remove_holding("NONEXIST")
        assert list_holdings() == []

    def test_remove_one_of_many(self) -> None:
        add_holding("AAPL", 10.0, 150.0)
        add_holding("MSFT", 5.0, 300.0)
        remove_holding("AAPL")
        holdings = list_holdings()
        assert len(holdings) == 1
        assert holdings[0].ticker == "MSFT"

    def test_remove_case_insensitive(self) -> None:
        add_holding("AAPL", 10.0, 150.0)
        remove_holding("aapl")
        assert list_holdings() == []


class TestUpdateHolding:
    def test_update_shares(self) -> None:
        add_holding("AAPL", 10.0, 150.0)
        p = update_holding("AAPL", shares=25.0)
        assert p is not None
        holding = next(h for h in p.holdings if h.ticker == "AAPL")
        assert holding.shares == 25.0
        assert holding.avg_cost == 150.0

    def test_update_avg_cost(self) -> None:
        add_holding("AAPL", 10.0, 150.0)
        p = update_holding("AAPL", avg_cost=175.0)
        assert p is not None
        holding = next(h for h in p.holdings if h.ticker == "AAPL")
        assert holding.avg_cost == 175.0
        assert holding.shares == 10.0

    def test_update_both(self) -> None:
        add_holding("AAPL", 10.0, 150.0)
        p = update_holding("AAPL", shares=20.0, avg_cost=200.0)
        assert p is not None
        holding = next(h for h in p.holdings if h.ticker == "AAPL")
        assert holding.shares == 20.0
        assert holding.avg_cost == 200.0

    def test_update_nonexistent_returns_none(self) -> None:
        result = update_holding("NONEXIST", shares=10.0)
        assert result is None

    def test_update_case_insensitive(self) -> None:
        add_holding("AAPL", 10.0, 150.0)
        p = update_holding("aapl", shares=50.0)
        assert p is not None
        holding = next(h for h in p.holdings if h.ticker == "AAPL")
        assert holding.shares == 50.0


class TestPersistence:
    def test_save_and_load(self) -> None:
        p = Portfolio(holdings=[Holding(ticker="AAPL", shares=10.0, avg_cost=150.0)])
        save_portfolio(p)
        loaded = load_portfolio()
        assert len(loaded.holdings) == 1
        assert loaded.holdings[0].ticker == "AAPL"
        assert loaded.holdings[0].shares == 10.0

    def test_atomic_write(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        path = tmp_path / "sub" / "portfolio.json"
        monkeypatch.setattr(portfolio_mod, "PORTFOLIO_PATH", path)
        p = Portfolio(holdings=[Holding(ticker="GOOG", shares=2.0, avg_cost=100.0)])
        save_portfolio(p)
        assert path.exists()
        data = json.loads(path.read_text())
        assert len(data["holdings"]) == 1
        assert data["holdings"][0]["ticker"] == "GOOG"

    def test_corrupted_file_returns_empty(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        path = tmp_path / "portfolio.json"
        path.write_text("not valid json{{")
        monkeypatch.setattr(portfolio_mod, "PORTFOLIO_PATH", path)
        result = load_portfolio()
        assert result.holdings == []


class TestHoldingModel:
    def test_added_at_auto_set(self) -> None:
        h = Holding(ticker="AAPL", shares=10.0, avg_cost=150.0)
        assert h.added_at != ""

    def test_ticker_normalised(self) -> None:
        h = Holding(ticker="msft", shares=5.0, avg_cost=300.0)
        assert h.ticker == "MSFT"
