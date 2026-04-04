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
from fastapi import FastAPI, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.responses import Response

from fastapi.routing import APIRouter

from market_data import store, watchlist
from market_data.config import CORS_ORIGINS, DATA_DIR, DEFAULT_INTERVAL, VALID_INTERVALS, WS_POLL_INTERVAL
from market_data.exceptions import (
    InvalidTickerError,
    MarketDataError,
    TickerNotFoundError,
)
from market_data.schemas import (
    ClosePoint,
    ErrorResponse,
    HealthResponse,
    LatestQuote,
    OHLCVBar,
    PriceUpdate,
    ReadyResponse,
    TickerStatus,
    WatchlistAddRequest,
    WatchlistResponse,
    WSMessage,
)

logger = logging.getLogger(__name__)

RATE_LIMIT_REQUESTS = 60
RATE_LIMIT_WINDOW = 60
_request_log: dict[str, collections.deque[float]] = {}
_ws_clients: set[WebSocket] = set()
_price_task: asyncio.Task[None] | None = None


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
    global _price_task
    from market_data.logging_config import setup_logging

    setup_logging()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("server starting", extra={"path": str(DATA_DIR)})
    _price_task = asyncio.create_task(_poll_prices())
    yield
    if _price_task is not None:
        _price_task.cancel()
        try:
            await _price_task
        except asyncio.CancelledError:
            pass
    for ws in list(_ws_clients):
        await ws.close()
    _ws_clients.clear()
    store.invalidate_cache()
    _request_log.clear()
    logger.info("server shutting down")


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
            "%s %s -> %d",
            request.method,
            request.url.path,
            response.status_code,
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "latency_ms": round(elapsed_ms, 1),
                "client_ip": client_ip,
            },
        )
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception:
        elapsed_ms = (time.monotonic() - start) * 1000
        logger.exception(
            "%s %s -> 500 unhandled error",
            request.method,
            request.url.path,
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": 500,
                "latency_ms": round(elapsed_ms, 1),
                "client_ip": client_ip,
                "error_type": "unhandled",
            },
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
    logger.error("MarketDataError: %s", exc, extra={"error_type": type(exc).__name__})
    return JSONResponse(status_code=500, content={"error": str(exc)})


async def _broadcast(msg: WSMessage) -> None:
    payload = msg.model_dump_json()
    dead: list[WebSocket] = []
    for ws in _ws_clients:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _ws_clients.discard(ws)


async def _poll_prices() -> None:
    from market_data.api import get_latest as _get_latest

    while True:
        await asyncio.sleep(WS_POLL_INTERVAL)
        if not _ws_clients:
            continue
        tickers = await asyncio.to_thread(store.list_tickers)
        if not tickers:
            continue
        updates: list[PriceUpdate] = []
        for t in tickers:
            row = await asyncio.to_thread(_get_latest, t)
            if row:
                row["ticker"] = t
                updates.append(PriceUpdate.model_validate(row))
        if updates:
            await _broadcast(WSMessage(type="price_update", data=updates))


@app.websocket("/ws/prices")
async def ws_prices(ws: WebSocket) -> None:
    await ws.accept()
    _ws_clients.add(ws)
    logger.info("ws client connected", extra={"client_ip": ws.client.host if ws.client else "unknown"})
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _ws_clients.discard(ws)
        logger.info("ws client disconnected")


@app.get("/health", response_model=HealthResponse)
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready", response_model=ReadyResponse)
def ready() -> dict[str, object]:
    data_ok = DATA_DIR.exists()
    tickers = store.list_tickers() if data_ok else []
    return {
        "status": "ready" if data_ok else "not_ready",
        "data_dir_exists": data_ok,
        "ticker_count": len(tickers),
    }


def _ohlcv_records(df: pd.DataFrame) -> list[OHLCVBar]:
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
        OHLCVBar(
            date=dates[i],
            time=unix_ts[i],
            open=float(opens[i]),
            high=float(highs[i]),
            low=float(lows[i]),
            close=float(closes[i]),
            volume=volumes[i],
        )
        for i in range(len(df))
    ]


def _close_records(df: pd.DataFrame) -> list[ClosePoint]:
    if df.empty:
        return []

    ts_index = pd.DatetimeIndex(df.index)
    dates = ts_index.date
    unix_ts = (ts_index.astype("int64") // 10**9).tolist()
    closes = df["Close"].round(4).tolist()

    return [
        ClosePoint(
            date=dates[i].isoformat(),
            time=unix_ts[i],
            close=float(closes[i]),
        )
        for i in range(len(df))
    ]


@v1.get("/tickers", response_model=list[TickerStatus])
async def get_tickers() -> list[dict[str, object]]:
    return await asyncio.to_thread(store.status)


@v1.get("/ohlcv/{ticker}", response_model=list[OHLCVBar])
async def get_ohlcv(
    ticker: str,
    days: int = Query(default=365, ge=1, le=3650),
    limit: int = Query(default=0, ge=0, le=10000),
    offset: int = Query(default=0, ge=0),
    interval: str = Query(default=DEFAULT_INTERVAL),
) -> list[OHLCVBar]:
    if interval not in VALID_INTERVALS:
        return JSONResponse(  # type: ignore[return-value]
            status_code=400,
            content={"error": f"Invalid interval {interval!r}. Valid: {VALID_INTERVALS}"},
        )
    df = await asyncio.to_thread(store.load, ticker, days, DATA_DIR, interval)
    records = _ohlcv_records(df)
    if offset:
        records = records[offset:]
    if limit:
        records = records[:limit]
    return records


@v1.get("/latest/{ticker}", response_model=LatestQuote | None)
async def get_latest(ticker: str) -> dict[str, object] | None:
    from market_data.api import get_latest as _get_latest

    return await asyncio.to_thread(_get_latest, ticker)


@v1.get("/compare", response_model=dict[str, list[ClosePoint]])
async def get_compare(    tickers: str = Query(description="Comma-separated tickers, e.g. QQQ,XOM,CRM"),
    days: int = Query(default=90, ge=1, le=3650),
    interval: str = Query(default=DEFAULT_INTERVAL),
) -> dict[str, list[ClosePoint]]:
    if interval not in VALID_INTERVALS:
        return JSONResponse(  # type: ignore[return-value]
            status_code=400,
            content={"error": f"Invalid interval {interval!r}. Valid: {VALID_INTERVALS}"},
        )
    result: dict[str, list[ClosePoint]] = {}
    for t in tickers.split(","):
        t = t.strip()
        if not t:
            continue
        df = await asyncio.to_thread(store.load, t, days, DATA_DIR, interval)
        result[t] = _close_records(df)
    return result


@v1.get("/watchlist", response_model=WatchlistResponse)
async def get_watchlist() -> dict[str, list[str]]:
    tickers = await asyncio.to_thread(watchlist.list_tickers)
    return {"tickers": tickers}


@v1.post("/watchlist", response_model=WatchlistResponse)
async def add_to_watchlist(body: WatchlistAddRequest) -> WatchlistResponse:
    wl = await asyncio.to_thread(watchlist.add_ticker, body.ticker)
    return WatchlistResponse(tickers=wl.tickers)


@v1.delete("/watchlist/{ticker}", response_model=WatchlistResponse)
async def delete_from_watchlist(ticker: str) -> WatchlistResponse:
    wl = await asyncio.to_thread(watchlist.remove_ticker, ticker)
    return WatchlistResponse(tickers=wl.tickers)


app.include_router(v1)
# Backward-compatible aliases: /api/* -> same handlers as /api/v1/*
legacy = APIRouter(prefix="/api", tags=["legacy"])
legacy.add_api_route("/tickers", get_tickers, methods=["GET"])
legacy.add_api_route("/ohlcv/{ticker}", get_ohlcv, methods=["GET"])
legacy.add_api_route("/latest/{ticker}", get_latest, methods=["GET"])
legacy.add_api_route("/compare", get_compare, methods=["GET"])
legacy.add_api_route("/watchlist", get_watchlist, methods=["GET"])
legacy.add_api_route("/watchlist", add_to_watchlist, methods=["POST"])
legacy.add_api_route("/watchlist/{ticker}", delete_from_watchlist, methods=["DELETE"])
app.include_router(legacy)
