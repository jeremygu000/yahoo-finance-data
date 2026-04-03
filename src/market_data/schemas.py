from __future__ import annotations

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
    data: list[PriceUpdate] | str
