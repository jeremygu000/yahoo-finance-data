"""FastAPI server exposing market data as REST JSON endpoints.

Run: uv run uvicorn market_data.server:app --reload --port 8100
"""

from __future__ import annotations

from typing import cast

import pandas as pd
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from market_data import store

app = FastAPI(title="Market Data API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/tickers")
def get_tickers() -> list[dict[str, object]]:
    """All tickers with status info: ticker, rows, first_date, last_date, size_kb."""
    return store.status()


@app.get("/api/ohlcv/{ticker}")
def get_ohlcv(ticker: str, days: int = Query(default=365, ge=1, le=3650)) -> list[dict[str, object]]:
    """OHLCV data for a single ticker. Returns list of {date, open, high, low, close, volume}."""
    df = store.load(ticker, days=days)
    if df.empty:
        return []

    records: list[dict[str, object]] = []
    for idx, row in df.iterrows():
        ts = pd.Timestamp(str(idx))
        records.append(
            {
                "date": ts.date().isoformat(),
                "time": int(ts.timestamp()),
                "open": round(float(row["Open"]), 4),
                "high": round(float(row["High"]), 4),
                "low": round(float(row["Low"]), 4),
                "close": round(float(row["Close"]), 4),
                "volume": int(row["Volume"]),
            }
        )
    return records


@app.get("/api/latest/{ticker}")
def get_latest(ticker: str) -> dict[str, object] | None:
    """Latest data point for a ticker."""
    from market_data.api import get_latest as _get_latest

    return _get_latest(ticker)


@app.get("/api/compare")
def get_compare(
    tickers: str = Query(description="Comma-separated tickers, e.g. QQQ,XOM,CRM"),
    days: int = Query(default=90, ge=1, le=3650),
) -> dict[str, list[dict[str, object]]]:
    """Closing prices for multiple tickers (for overlay line chart).

    Returns {ticker: [{date, close}, ...]}.
    """
    result: dict[str, list[dict[str, object]]] = {}
    for t in tickers.split(","):
        t = t.strip()
        if not t:
            continue
        df = store.load(t, days=days)
        if df.empty:
            result[t] = []
            continue
        result[t] = [
            {
                "date": pd.Timestamp(str(idx)).date().isoformat(),
                "time": int(pd.Timestamp(str(idx)).timestamp()),
                "close": round(float(row["Close"]), 4),
            }
            for idx, row in df.iterrows()
        ]
    return result
