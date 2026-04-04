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


class WSSubscribeRequest(BaseModel):
    action: str  # "subscribe" | "unsubscribe"
    tickers: list[str]


class WSSubscriptionAck(BaseModel):
    type: str  # "subscribed" | "unsubscribed"
    tickers: list[str]


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


class TickerOverviewItem(BaseModel):
    ticker: str
    interval: str = "1d"
    rows: int
    first_date: str
    last_date: str
    size_kb: float
    latest: LatestQuote | None = None
    change: float | None = None
    change_pct: float | None = None


class TickerOverviewResponse(BaseModel):
    items: list[TickerOverviewItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    tickers: list[str] = []
    days: int = 30


class FundamentalsResponse(BaseModel):
    ticker: str
    fetched_at: str | None = None
    source: str | None = None
    short_name: str | None = None
    long_name: str | None = None
    sector: str | None = None
    industry: str | None = None
    market_cap: float | None = None
    trailing_pe: float | None = None
    forward_pe: float | None = None
    trailing_eps: float | None = None
    forward_eps: float | None = None
    price_to_book: float | None = None
    price_to_sales_trailing_12_months: float | None = None
    peg_ratio: float | None = None
    enterprise_value: float | None = None
    enterprise_to_ebitda: float | None = None
    dividend_yield: float | None = None
    beta: float | None = None
    regular_market_price: float | None = None
    current_price: float | None = None
    currency: str | None = None
    target_low_price: float | None = None
    target_high_price: float | None = None
    target_mean_price: float | None = None
    target_median_price: float | None = None
    number_of_analyst_opinions: float | None = None
    recommendation_key: str | None = None
    recommendation_mean: float | None = None
    short_ratio: float | None = None
    short_percent_of_float: float | None = None
    shares_short: float | None = None
    total_revenue: float | None = None
    revenue_growth: float | None = None
    gross_margins: float | None = None
    operating_margins: float | None = None
    profit_margins: float | None = None
    earnings_quarterly_growth: float | None = None
    earnings_growth: float | None = None
    return_on_equity: float | None = None
    debt_to_equity: float | None = None
    fifty_two_week_high: float | None = None
    fifty_two_week_low: float | None = None
    average_volume: float | None = None
    quote_type: str | None = None


class RecommendationItem(BaseModel):
    date: str
    period: str | None = None
    strong_buy: int | None = None
    buy: int | None = None
    hold: int | None = None
    sell: int | None = None
    strong_sell: int | None = None


class RecommendationsResponse(BaseModel):
    ticker: str
    count: int
    items: list[RecommendationItem]


class EarningsDateItem(BaseModel):
    date: str
    eps_estimate: float | None = None
    reported_eps: float | None = None
    surprise_pct: float | None = None


class EarningsDatesResponse(BaseModel):
    ticker: str
    count: int
    items: list[EarningsDateItem]


class UpgradeDowngradeItem(BaseModel):
    date: str
    firm: str | None = None
    to_grade: str | None = None
    from_grade: str | None = None
    action: str | None = None


class UpgradesDowngradesResponse(BaseModel):
    ticker: str
    count: int
    items: list[UpgradeDowngradeItem]


class NewsArticle(BaseModel):
    uuid: str | None = None
    title: str | None = None
    link: str | None = None
    publisher: str | None = None
    provider_publish_time: int | None = None
    type: str | None = None
    related_tickers: list[str] | None = None
    thumbnail_url: str | None = None


class NewsResponse(BaseModel):
    ticker: str
    count: int
    articles: list[NewsArticle]


# --- Data Management ---


class StorageSummary(BaseModel):
    total_files: int
    total_size_kb: float
    total_rows: int
    ticker_count: int
    oldest_date: str | None = None
    newest_date: str | None = None


class CleanRequest(BaseModel):
    keep_days: int = 365


class CleanResponse(BaseModel):
    removed: dict[str, int]
    total_removed: int


class DeleteTickerResponse(BaseModel):
    ticker: str
    files_removed: int


class AnomalyItem(BaseModel):
    ticker: str
    issue: str
    count: int
    detail: str = ""


class TickerQualityItem(BaseModel):
    ticker: str
    interval: str
    rows: int
    first_date: str
    last_date: str
    days_stale: int
    completeness_pct: float
    nan_pct: float
    anomalies: list[AnomalyItem] = []
    outliers: int = 0


class QualityReportResponse(BaseModel):
    scan_date: str
    total_files: int
    total_rows: int
    tickers: list[TickerQualityItem] = []
    anomalies: list[AnomalyItem] = []
