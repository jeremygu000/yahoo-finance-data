"""FastAPI server – run: uv run uvicorn market_data.server:app --reload --port 8100"""

from __future__ import annotations

import asyncio
import collections
import io
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
from starlette.responses import Response, StreamingResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from fastapi.routing import APIRouter

from market_data import store, watchlist
from market_data import alerts as alerts_mod
from market_data import ai_summary as ai_mod
from market_data import indicators as indicators_mod
from market_data import notifications as notif_mod
from market_data import portfolio as portfolio_mod
from market_data.config import API_KEY, CORS_ORIGINS, DATA_DIR, DEFAULT_INTERVAL, VALID_INTERVALS, WS_POLL_INTERVAL
from market_data.exceptions import (
    InvalidTickerError,
    MarketDataError,
    TickerNotFoundError,
)
from market_data.schemas import (
    AlertCreateRequest,
    AlertListResponse,
    AlertResponse,
    AlertTriggered,
    ClosePoint,
    ErrorResponse,
    HealthResponse,
    HoldingResponse,
    IndicatorPoint,
    LatestQuote,
    OHLCVBar,
    PortfolioAddRequest,
    PortfolioResponse,
    PortfolioSummaryItem,
    PortfolioSummaryResponse,
    PortfolioUpdateRequest,
    PriceUpdate,
    ReadyResponse,
    SearchResponse,
    SearchResult,
    SummaryRequest,
    SummaryResponse,
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


class _WSCORSBypass:
    """Let WebSocket connections bypass CORSMiddleware which rejects them with 403."""

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "websocket":
            headers = dict(scope.get("headers", []))
            origin = headers.get(b"origin", b"").decode()
            if not origin or origin in CORS_ORIGINS:
                await self._app(scope, receive, send)
                return
            await send({"type": "websocket.close", "code": 1008})
            return
        await self._app(scope, receive, send)


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
app.add_middleware(_WSCORSBypass)


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

    # Check API key auth if configured
    if API_KEY is not None:
        # Skip auth for these paths
        skip_auth_paths = {"/health", "/ready", "/docs", "/openapi.json", "/ws/prices"}
        if request.url.path not in skip_auth_paths:
            provided_key = request.headers.get("X-API-Key")
            if provided_key != API_KEY:
                return JSONResponse(
                    status_code=401,
                    content={"error": "Invalid or missing API key"},
                    headers={"X-Request-ID": request_id},
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
            alert_store = await asyncio.to_thread(alerts_mod.load_alerts)
            fired = await asyncio.to_thread(alerts_mod.evaluate_alerts, updates, alert_store)
            if fired:
                triggered_msgs = [
                    AlertTriggered(
                        alert_id=item["alert"].id,
                        ticker=item["alert"].ticker,
                        condition=item["alert"].condition.value,
                        threshold=item["alert"].threshold,
                        current_price=item["price"].close,
                        message=item["message"],
                    )
                    for item in fired
                ]
                await _broadcast(WSMessage(type="alert_triggered", data=triggered_msgs))
                dispatcher = notif_mod.get_dispatcher()
                for item in fired:
                    alert: alerts_mod.Alert = item["alert"]
                    if alert.channels:
                        subject, body = notif_mod.build_alert_message(item)
                        recipient_map: dict[str, str] = {
                            "telegram": alert.telegram_chat_id,
                            "email": alert.email,
                        }
                        await dispatcher.dispatch(alert.channels, recipient_map, subject, body)


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
async def get_compare(
    tickers: str = Query(description="Comma-separated tickers, e.g. QQQ,XOM,CRM"),
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


def _alert_to_response(a: alerts_mod.Alert) -> AlertResponse:
    return AlertResponse(
        id=a.id,
        ticker=a.ticker,
        condition=a.condition.value,
        threshold=a.threshold,
        enabled=a.enabled,
        cooldown_seconds=a.cooldown_seconds,
        last_triggered=a.last_triggered,
        created_at=a.created_at,
        channels=a.channels,
        telegram_chat_id=a.telegram_chat_id,
        email=a.email,
    )


@v1.get("/alerts", response_model=AlertListResponse)
async def get_alerts(ticker: str | None = Query(default=None)) -> AlertListResponse:
    items = await asyncio.to_thread(alerts_mod.list_alerts, ticker)
    return AlertListResponse(alerts=[_alert_to_response(a) for a in items])


@v1.post("/alerts", response_model=AlertResponse)
async def create_alert(body: AlertCreateRequest) -> AlertResponse:
    alert = alerts_mod.Alert(
        ticker=body.ticker,
        condition=alerts_mod.AlertCondition(body.condition.value),
        threshold=body.threshold,
        cooldown_seconds=body.cooldown_seconds,
        channels=body.channels,
        telegram_chat_id=body.telegram_chat_id,
        email=body.email,
    )
    await asyncio.to_thread(alerts_mod.add_alert, alert)
    return _alert_to_response(alert)


@v1.delete("/alerts/{alert_id}", response_model=AlertListResponse)
async def delete_alert(alert_id: str) -> AlertListResponse:
    store_after = await asyncio.to_thread(alerts_mod.remove_alert, alert_id)
    return AlertListResponse(alerts=[_alert_to_response(a) for a in store_after.alerts])


@v1.get("/alerts/channels")
async def get_notification_channels() -> dict[str, list[str]]:
    dispatcher = notif_mod.get_dispatcher()
    return {"channels": dispatcher.available_channels}


@v1.post("/alerts/test/{alert_id}")
async def test_alert_notification(alert_id: str) -> dict[str, object]:
    items = await asyncio.to_thread(alerts_mod.list_alerts)
    alert = next((a for a in items if a.id == alert_id), None)
    if alert is None:
        return JSONResponse(status_code=404, content={"error": f"Alert {alert_id} not found"})  # type: ignore[return-value]
    if not alert.channels:
        return {"status": "skipped", "reason": "no channels configured"}
    subject = f"[TEST] Alert: {alert.ticker} — {alert.condition.value} {alert.threshold}"
    body = f"This is a test notification for your {alert.ticker} alert."
    recipient_map: dict[str, str] = {
        "telegram": alert.telegram_chat_id,
        "email": alert.email,
    }
    dispatcher = notif_mod.get_dispatcher()
    results = await dispatcher.dispatch(alert.channels, recipient_map, subject, body)
    return {"status": "sent", "results": results}


_INDICATOR_COLUMNS: dict[str, list[str]] = {
    "sma": [],
    "ema": [],
    "rsi": [],
    "macd": ["MACD", "Signal", "Histogram"],
    "bollinger": ["BB_Upper", "BB_Middle", "BB_Lower"],
}

_VALID_INDICATORS = set(_INDICATOR_COLUMNS)


def _indicator_records(result_df: pd.DataFrame) -> list[IndicatorPoint]:
    if result_df.empty:
        return []
    ts_index = pd.DatetimeIndex(result_df.index)
    dates = [d.isoformat() for d in ts_index.date]
    unix_ts = (ts_index.astype("int64") // 10**9).tolist()
    cols = result_df.columns.tolist()
    rows: list[IndicatorPoint] = []
    for i in range(len(result_df)):
        raw_row = result_df.iloc[i]
        values: dict[str, float | None] = {}
        for c in cols:
            v = raw_row[c]
            values[c] = None if pd.isna(v) else float(v)
        rows.append(IndicatorPoint(date=dates[i], time=unix_ts[i], values=values))
    return rows


@v1.get("/indicators/{ticker}", response_model=list[IndicatorPoint])
async def get_indicators(
    ticker: str,
    indicator: str = Query(description="One of: sma, ema, rsi, macd, bollinger"),
    period: int = Query(default=20, ge=1, le=500),
    fast: int = Query(default=12, ge=1, le=500),
    slow: int = Query(default=26, ge=1, le=500),
    signal: int = Query(default=9, ge=1, le=500),
    std_dev: float = Query(default=2.0, ge=0.1, le=10.0),
    column: str = Query(default="Close"),
    days: int = Query(default=365, ge=1, le=3650),
    interval: str = Query(default=DEFAULT_INTERVAL),
) -> list[IndicatorPoint]:
    indicator = indicator.lower()
    if indicator not in _VALID_INDICATORS:
        return JSONResponse(  # type: ignore[return-value]
            status_code=400,
            content={"error": f"Invalid indicator {indicator!r}. Valid: {sorted(_VALID_INDICATORS)}"},
        )
    if interval not in VALID_INTERVALS:
        return JSONResponse(  # type: ignore[return-value]
            status_code=400,
            content={"error": f"Invalid interval {interval!r}. Valid: {VALID_INTERVALS}"},
        )
    df = await asyncio.to_thread(store.load, ticker, days, DATA_DIR, interval)
    if indicator == "sma":
        result_df = await asyncio.to_thread(indicators_mod.sma, df, column, period)
    elif indicator == "ema":
        result_df = await asyncio.to_thread(indicators_mod.ema, df, column, period)
    elif indicator == "rsi":
        result_df = await asyncio.to_thread(indicators_mod.rsi, df, column, period)
    elif indicator == "macd":
        result_df = await asyncio.to_thread(indicators_mod.macd, df, column, fast, slow, signal)
    else:
        result_df = await asyncio.to_thread(indicators_mod.bollinger_bands, df, column, period, std_dev)
    return _indicator_records(result_df)


@v1.get("/portfolio", response_model=PortfolioResponse)
async def get_portfolio() -> PortfolioResponse:
    holdings = await asyncio.to_thread(portfolio_mod.list_holdings)
    return PortfolioResponse(
        holdings=[
            HoldingResponse(ticker=h.ticker, shares=h.shares, avg_cost=h.avg_cost, added_at=h.added_at)
            for h in holdings
        ]
    )


@v1.post("/portfolio", response_model=PortfolioResponse)
async def add_to_portfolio(body: PortfolioAddRequest) -> PortfolioResponse:
    p = await asyncio.to_thread(portfolio_mod.add_holding, body.ticker, body.shares, body.avg_cost)
    return PortfolioResponse(
        holdings=[
            HoldingResponse(ticker=h.ticker, shares=h.shares, avg_cost=h.avg_cost, added_at=h.added_at)
            for h in p.holdings
        ]
    )


@v1.put("/portfolio/{ticker}", response_model=PortfolioResponse)
async def update_portfolio_holding(ticker: str, body: PortfolioUpdateRequest) -> PortfolioResponse:
    p = await asyncio.to_thread(portfolio_mod.update_holding, ticker, body.shares, body.avg_cost)
    if p is None:
        return JSONResponse(status_code=404, content={"error": f"Holding {ticker.upper()} not found"})  # type: ignore[return-value]
    return PortfolioResponse(
        holdings=[
            HoldingResponse(ticker=h.ticker, shares=h.shares, avg_cost=h.avg_cost, added_at=h.added_at)
            for h in p.holdings
        ]
    )


@v1.delete("/portfolio/{ticker}", response_model=PortfolioResponse)
async def delete_from_portfolio(ticker: str) -> PortfolioResponse:
    p = await asyncio.to_thread(portfolio_mod.remove_holding, ticker)
    return PortfolioResponse(
        holdings=[
            HoldingResponse(ticker=h.ticker, shares=h.shares, avg_cost=h.avg_cost, added_at=h.added_at)
            for h in p.holdings
        ]
    )


@v1.get("/portfolio/summary", response_model=PortfolioSummaryResponse)
async def get_portfolio_summary() -> PortfolioSummaryResponse:
    from market_data.api import get_latest as _get_latest

    holdings = await asyncio.to_thread(portfolio_mod.list_holdings)
    items: list[PortfolioSummaryItem] = []
    for h in holdings:
        row = await asyncio.to_thread(_get_latest, h.ticker)
        current_price: float | None = None
        market_value: float | None = None
        total_gain: float | None = None
        gain_pct: float | None = None
        if row is not None:
            current_price = float(str(row["close"]))
            market_value = round(current_price * h.shares, 4)
            cost_basis = h.avg_cost * h.shares
            total_gain = round(market_value - cost_basis, 4)
            gain_pct = round((total_gain / cost_basis) * 100, 4) if cost_basis != 0 else None
        items.append(
            PortfolioSummaryItem(
                ticker=h.ticker,
                shares=h.shares,
                avg_cost=h.avg_cost,
                current_price=current_price,
                market_value=market_value,
                total_gain=total_gain,
                gain_pct=gain_pct,
            )
        )
    return PortfolioSummaryResponse(holdings=items)


@v1.get("/export/{ticker}")
async def export_ohlcv(
    ticker: str,
    format: str = Query(default="csv", description="Export format (csv only)"),
    days: int = Query(default=365, ge=1, le=3650),
    interval: str = Query(default=DEFAULT_INTERVAL),
) -> StreamingResponse:
    if format != "csv":
        return JSONResponse(  # type: ignore[return-value]
            status_code=400,
            content={"error": f"Unsupported format {format!r}. Supported: csv"},
        )
    if interval not in VALID_INTERVALS:
        return JSONResponse(  # type: ignore[return-value]
            status_code=400,
            content={"error": f"Invalid interval {interval!r}. Valid: {VALID_INTERVALS}"},
        )
    df = await asyncio.to_thread(store.load, ticker, days, DATA_DIR, interval)
    if df.empty:
        return JSONResponse(  # type: ignore[return-value]
            status_code=404,
            content={"error": f"No data found for ticker {ticker!r}"},
        )

    # Convert DataFrame to CSV
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index_label="Date")
    csv_content = csv_buffer.getvalue()

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{ticker.upper()}_ohlcv.csv"'},
    )


@v1.get("/search", response_model=SearchResponse)
async def search_tickers(
    q: str = Query(description="Search query for ticker symbol"),
    limit: int = Query(default=10, ge=1, le=50),
) -> SearchResponse:
    if not q or q.strip() == "":
        return SearchResponse(results=[], query=q)

    all_tickers = await asyncio.to_thread(store.list_tickers)
    search_term = q.upper().strip()
    matching_tickers = [t for t in all_tickers if search_term in t]
    matching_tickers.sort()
    matched_limited = matching_tickers[:limit]

    results = [SearchResult(ticker=t, has_data=True) for t in matched_limited]
    return SearchResponse(results=results, query=q)


@v1.get("/ai/health")
async def ai_health() -> dict[str, bool]:
    ok = await ai_mod.health_check()
    return {"available": ok}


@v1.post("/ai/summary", response_model=SummaryResponse)
async def ai_summary(req: SummaryRequest) -> SummaryResponse:
    tickers = req.tickers or await asyncio.to_thread(store.list_tickers)
    if not tickers:
        return SummaryResponse(
            summary="No tickers available for analysis.",
            model="",
            total_duration_ms=0,
            eval_count=0,
            tickers=[],
            days=req.days,
        )
    result = await ai_mod.generate_summary(tickers, days=req.days)
    return SummaryResponse(
        summary=result["response"],
        model=result["model"],
        total_duration_ms=result["total_duration_ms"],
        eval_count=result["eval_count"],
        tickers=tickers,
        days=req.days,
    )


@v1.post("/ai/summary/stream")
async def ai_summary_stream(req: SummaryRequest) -> StreamingResponse:
    tickers = req.tickers or await asyncio.to_thread(store.list_tickers)

    async def event_stream() -> AsyncIterator[str]:
        async for token in ai_mod.generate_summary_stream(tickers, days=req.days):
            yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


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
legacy.add_api_route("/alerts", get_alerts, methods=["GET"])
legacy.add_api_route("/alerts", create_alert, methods=["POST"])
legacy.add_api_route("/alerts/{alert_id}", delete_alert, methods=["DELETE"])
legacy.add_api_route("/alerts/channels", get_notification_channels, methods=["GET"])
legacy.add_api_route("/alerts/test/{alert_id}", test_alert_notification, methods=["POST"])
legacy.add_api_route("/indicators/{ticker}", get_indicators, methods=["GET"])
legacy.add_api_route("/export/{ticker}", export_ohlcv, methods=["GET"])
legacy.add_api_route("/portfolio", get_portfolio, methods=["GET"])
legacy.add_api_route("/portfolio", add_to_portfolio, methods=["POST"])
legacy.add_api_route("/portfolio/{ticker}", update_portfolio_holding, methods=["PUT"])
legacy.add_api_route("/portfolio/{ticker}", delete_from_portfolio, methods=["DELETE"])
legacy.add_api_route("/portfolio/summary", get_portfolio_summary, methods=["GET"])
legacy.add_api_route("/search", search_tickers, methods=["GET"])
legacy.add_api_route("/ai/health", ai_health, methods=["GET"])
legacy.add_api_route("/ai/summary", ai_summary, methods=["POST"])
legacy.add_api_route("/ai/summary/stream", ai_summary_stream, methods=["POST"])
app.include_router(legacy)
