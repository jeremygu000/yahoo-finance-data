from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, field_validator

from market_data.config import DATA_DIR

PORTFOLIO_PATH = DATA_DIR.parent / "portfolio.json"

_portfolio_lock = threading.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Holding(BaseModel):
    ticker: str
    shares: float
    avg_cost: float
    added_at: str = ""

    def model_post_init(self, __context: Any) -> None:
        if not self.added_at:
            object.__setattr__(self, "added_at", _now_iso())

    @field_validator("ticker", mode="before")
    @classmethod
    def normalise_ticker(cls, v: str) -> str:
        return v.upper()


class Portfolio(BaseModel):
    holdings: list[Holding] = []


def load_portfolio() -> Portfolio:
    with _portfolio_lock:
        path = PORTFOLIO_PATH
        if not path.exists():
            return Portfolio()
        try:
            data = json.loads(path.read_text())
            return Portfolio.model_validate(data)
        except Exception:
            return Portfolio()


def save_portfolio(portfolio: Portfolio) -> None:
    with _portfolio_lock:
        path = PORTFOLIO_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(portfolio.model_dump_json())
        os.replace(tmp, path)


def add_holding(ticker: str, shares: float, avg_cost: float) -> Portfolio:
    with _portfolio_lock:
        path = PORTFOLIO_PATH
        if path.exists():
            try:
                data = json.loads(path.read_text())
                portfolio = Portfolio.model_validate(data)
            except Exception:
                portfolio = Portfolio()
        else:
            portfolio = Portfolio()

        ticker = ticker.upper()
        existing = next((h for h in portfolio.holdings if h.ticker == ticker), None)
        if existing is not None:
            portfolio.holdings = [h for h in portfolio.holdings if h.ticker != ticker]

        portfolio.holdings.append(Holding(ticker=ticker, shares=shares, avg_cost=avg_cost))
        portfolio.holdings.sort(key=lambda h: h.ticker)

        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(portfolio.model_dump_json())
        os.replace(tmp, path)
        return portfolio


def remove_holding(ticker: str) -> Portfolio:
    with _portfolio_lock:
        path = PORTFOLIO_PATH
        if path.exists():
            try:
                data = json.loads(path.read_text())
                portfolio = Portfolio.model_validate(data)
            except Exception:
                portfolio = Portfolio()
        else:
            portfolio = Portfolio()

        ticker = ticker.upper()
        portfolio.holdings = [h for h in portfolio.holdings if h.ticker != ticker]

        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(portfolio.model_dump_json())
        os.replace(tmp, path)
        return portfolio


def update_holding(ticker: str, shares: float | None = None, avg_cost: float | None = None) -> Portfolio | None:
    """Update shares and/or avg_cost for an existing holding.

    Returns None if the ticker is not found.
    """
    with _portfolio_lock:
        path = PORTFOLIO_PATH
        if path.exists():
            try:
                data = json.loads(path.read_text())
                portfolio = Portfolio.model_validate(data)
            except Exception:
                portfolio = Portfolio()
        else:
            portfolio = Portfolio()

        ticker = ticker.upper()
        holding = next((h for h in portfolio.holdings if h.ticker == ticker), None)
        if holding is None:
            return None

        if shares is not None:
            object.__setattr__(holding, "shares", shares)
        if avg_cost is not None:
            object.__setattr__(holding, "avg_cost", avg_cost)

        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(portfolio.model_dump_json())
        os.replace(tmp, path)
        return portfolio


def list_holdings() -> list[Holding]:
    with _portfolio_lock:
        path = PORTFOLIO_PATH
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text())
            portfolio = Portfolio.model_validate(data)
            return portfolio.holdings
        except Exception:
            return []
