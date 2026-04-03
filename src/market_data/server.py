"""FastAPI server – run: uv run uvicorn market_data.server:app --reload --port 8100"""

from __future__ import annotations

import asyncio
import collections
import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import pandas as pd
from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.responses import Response

from fastapi.routing import APIRouter

from market_data import store
from market_data.config import CORS_ORIGINS
from market_data.exceptions import (
    InvalidTickerError,
    MarketDataError,
    TickerNotFoundError,
)

logger = logging.getLogger(__name__)

RATE_LIMIT_REQUESTS = 60
RATE_LIMIT_WINDOW = 60
_request_log: dict[str, collections.deque[float]] = {}


def _is_rate_limited(client_ip: str) -> bool:
    now = time.monotonic()
    if client_ip not in _request_log:
        _request_log[client_ip] = collections.deque()
    dq = _request_log[client_ip]
    while dq and dq[0] <= now - RATE_LIMIT_WINDOW:
        dq.popleft()
    if len(dq) >= RATE_LIMIT_REQUESTS:
        return True
    dq.append(now)
    return False


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    from market_data.config import DATA_DIR

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Market Data API starting — data_dir=%s", DATA_DIR)
    yield
    store.invalidate_cache()
    _request_log.clear()
    logger.info("Market Data API shutting down")


app = FastAPI(title="Market Data API", version="0.1.0", lifespan=lifespan)
v1 = APIRouter(prefix="/api/v1", tags=["v1"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.middleware("http")
async def logging_and_error_middleware(request: Request, call_next: Any) -> Response:
    request_id = uuid.uuid4().hex[:8]
    start = time.monotonic()

    client_ip = request.client.host if request.client else "unknown"
    if _is_rate_limited(client_ip):
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded"},
            headers={"Retry-After": str(RATE_LIMIT_WINDOW), "X-Request-ID": request_id},
        )

    try:
        response: Response = await call_next(request)
        elapsed_ms = (time.monotonic() - start) * 1000
        logger.info(
            "%s %s -> %d (%.1fms) [%s]",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            request_id,
        )
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception:
        elapsed_ms = (time.monotonic() - start) * 1000
        logger.exception(
            "%s %s -> 500 (%.1fms) [%s] unhandled error",
            request.method,
            request.url.path,
            elapsed_ms,
            request_id,
        )
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "request_id": request_id},
        )


@app.exception_handler(InvalidTickerError)
async def invalid_ticker_handler(_request: Request, exc: InvalidTickerError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error": str(exc)})


@app.exception_handler(TickerNotFoundError)
async def ticker_not_found_handler(_request: Request, exc: TickerNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"error": str(exc)})


@app.exception_handler(MarketDataError)
async def market_data_error_handler(_request: Request, exc: MarketDataError) -> JSONResponse:
    logger.error("MarketDataError: %s", exc)
    return JSONResponse(status_code=500, content={"error": str(exc)})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, object]:
    from market_data.config import DATA_DIR

    data_ok = DATA_DIR.exists()
    tickers = store.list_tickers() if data_ok else []
    return {
        "status": "ready" if data_ok else "not_ready",
        "data_dir_exists": data_ok,
        "ticker_count": len(tickers),
    }


def _ohlcv_records(df: pd.DataFrame) -> list[dict[str, object]]:
    if df.empty:
        return []

    ts_index = pd.DatetimeIndex(df.index)
    dates = [d.isoformat() for d in ts_index.date]
    unix_ts = (ts_index.astype("int64") // 10**9).tolist()
    opens = df["Open"].round(4).tolist()
    highs = df["High"].round(4).tolist()
    lows = df["Low"].round(4).tolist()
    closes = df["Close"].round(4).tolist()
    volumes = df["Volume"].astype(int).tolist()

    return [
        {
            "date": dates[i],
            "time": unix_ts[i],
            "open": float(opens[i]),
            "high": float(highs[i]),
            "low": float(lows[i]),
            "close": float(closes[i]),
            "volume": volumes[i],
        }
        for i in range(len(df))
    ]


def _close_records(df: pd.DataFrame) -> list[dict[str, object]]:
    if df.empty:
        return []

    ts_index = pd.DatetimeIndex(df.index)
    dates = ts_index.date
    unix_ts = (ts_index.astype("int64") // 10**9).tolist()
    closes = df["Close"].round(4).tolist()

    return [
        {
            "date": dates[i].isoformat(),
            "time": unix_ts[i],
            "close": float(closes[i]),
        }
        for i in range(len(df))
    ]


@v1.get("/tickers")
async def get_tickers() -> list[dict[str, object]]:
    return await asyncio.to_thread(store.status)


@v1.get("/ohlcv/{ticker}")
async def get_ohlcv(
    ticker: str,
    days: int = Query(default=365, ge=1, le=3650),
    limit: int = Query(default=0, ge=0, le=10000),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, object]]:
    df = await asyncio.to_thread(store.load, ticker, days)
    records = _ohlcv_records(df)
    if offset:
        records = records[offset:]
    if limit:
        records = records[:limit]
    return records


@v1.get("/latest/{ticker}")
async def get_latest(ticker: str) -> dict[str, object] | None:
    from market_data.api import get_latest as _get_latest

    return await asyncio.to_thread(_get_latest, ticker)


@v1.get("/compare")
async def get_compare(
    tickers: str = Query(description="Comma-separated tickers, e.g. QQQ,XOM,CRM"),
    days: int = Query(default=90, ge=1, le=3650),
) -> dict[str, list[dict[str, object]]]:
    result: dict[str, list[dict[str, object]]] = {}
    for t in tickers.split(","):
        t = t.strip()
        if not t:
            continue
        df = await asyncio.to_thread(store.load, t, days)
        result[t] = _close_records(df)
    return result


app.include_router(v1)
# Backward-compatible aliases: /api/* -> same handlers as /api/v1/*
legacy = APIRouter(prefix="/api", tags=["legacy"])
legacy.add_api_route("/tickers", get_tickers, methods=["GET"])
legacy.add_api_route("/ohlcv/{ticker}", get_ohlcv, methods=["GET"])
legacy.add_api_route("/latest/{ticker}", get_latest, methods=["GET"])
legacy.add_api_route("/compare", get_compare, methods=["GET"])
app.include_router(legacy)
