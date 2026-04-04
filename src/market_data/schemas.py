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


class AlertCreateRequest(BaseModel):
    ticker: str
    condition: AlertConditionEnum
    threshold: float
    cooldown_seconds: int = 300


class AlertListResponse(BaseModel):
    alerts: list[AlertResponse]


class AlertTriggered(BaseModel):
    alert_id: str
    ticker: str
    condition: str
    threshold: float
    current_price: float
    message: str
