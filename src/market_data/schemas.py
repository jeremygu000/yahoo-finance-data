from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class OHLCVBar(BaseModel):
    date: str
    time: int
    open: float
    high: float
    low: float
    close: float
    volume: int


class ClosePoint(BaseModel):
    date: str
    time: int
    close: float


class TickerStatus(BaseModel):
    ticker: str
    interval: str = "1d"
    rows: int
    first_date: str
    last_date: str
    size_kb: float


class LatestQuote(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class HealthResponse(BaseModel):
    status: str


class ReadyResponse(BaseModel):
    status: str
    data_dir_exists: bool
    ticker_count: int


class ErrorResponse(BaseModel):
    error: str
    request_id: str | None = None


class PriceUpdate(BaseModel):
    ticker: str
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class WSMessage(BaseModel):
    type: str
    data: list[PriceUpdate] | list[AlertTriggered] | str


class WatchlistResponse(BaseModel):
    tickers: list[str]


class WatchlistAddRequest(BaseModel):
    ticker: str


class AlertConditionEnum(str, Enum):
    above = "above"
    below = "below"
    percent_change_above = "percent_change_above"
    percent_change_below = "percent_change_below"


class AlertResponse(BaseModel):
    id: str
    ticker: str
    condition: str
    threshold: float
    enabled: bool
    cooldown_seconds: int
    last_triggered: str | None
    created_at: str
    channels: list[str]
    telegram_chat_id: str
    email: str


class AlertCreateRequest(BaseModel):
    ticker: str
    condition: AlertConditionEnum
    threshold: float
    cooldown_seconds: int = 300
    channels: list[str] = []
    telegram_chat_id: str = ""
    email: str = ""


class AlertListResponse(BaseModel):
    alerts: list[AlertResponse]


class AlertTriggered(BaseModel):
    alert_id: str
    ticker: str
    condition: str
    threshold: float
    current_price: float
    message: str


class IndicatorPoint(BaseModel):
    date: str
    time: int
    values: dict[str, float | None]


class HoldingResponse(BaseModel):
    ticker: str
    shares: float
    avg_cost: float
    added_at: str


class PortfolioResponse(BaseModel):
    holdings: list[HoldingResponse]


class PortfolioAddRequest(BaseModel):
    ticker: str
    shares: float
    avg_cost: float


class PortfolioUpdateRequest(BaseModel):
    shares: float | None = None
    avg_cost: float | None = None


class PortfolioSummaryItem(BaseModel):
    ticker: str
    shares: float
    avg_cost: float
    current_price: float | None
    market_value: float | None
    total_gain: float | None
    gain_pct: float | None


class PortfolioSummaryResponse(BaseModel):
    holdings: list[PortfolioSummaryItem]


class SearchResult(BaseModel):
    ticker: str
    has_data: bool


class SearchResponse(BaseModel):
    results: list[SearchResult]
    query: str


class SummaryRequest(BaseModel):
    tickers: list[str] = []
    days: int = 30


class SummaryResponse(BaseModel):
    summary: str
    model: str
    total_duration_ms: int
    eval_count: int
    tickers: list[str]
    days: int
