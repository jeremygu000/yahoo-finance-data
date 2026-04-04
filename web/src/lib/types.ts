export interface TickerInfo {
  ticker: string;
  rows: number;
  first_date: string;
  last_date: string;
  size_kb: number;
}

export interface TickerOverviewItem {
  ticker: string;
  interval: string;
  rows: number;
  first_date: string;
  last_date: string;
  size_kb: number;
  latest: LatestQuote | null;
  change: number | null;
  change_pct: number | null;
}

export interface TickerOverviewResponse {
  items: TickerOverviewItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface HeatmapItem {
  ticker: string;
  close: number;
  change_pct: number | null;
  volume: number;
}

export interface OHLCVBar {
  date: string;
  time: number; // Unix timestamp (seconds)
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface LatestQuote {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface ComparePoint {
  date: string;
  time: number;
  close: number;
}

export type CompareData = Record<string, ComparePoint[]>;

export interface PriceUpdate {
  ticker: string;
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface AlertTriggered {
  alert_id: string;
  ticker: string;
  condition: string;
  threshold: number;
  current_price: number;
  message: string;
}

export interface WSMessage {
  type: "price_update" | "alert_triggered" | "ping" | "subscribed" | "unsubscribed" | "error";
  data?: PriceUpdate[] | AlertTriggered[] | string;
  tickers?: string[];
}

export interface WSSubscribeMessage {
  action: "subscribe" | "unsubscribe";
  tickers: string[];
}

export type SortDirection = "asc" | "desc";

export type SortColumn = "date" | "open" | "high" | "low" | "close" | "volume";

const TICKER_PALETTE = [
  "#00d4ff",
  "#ff6b35",
  "#ffd700",
  "#00ff88",
  "#ff4d8d",
  "#a78bfa",
  "#3b89ff",
  "#36bb80",
  "#ec4899",
  "#fdbc2a",
  "#6366f1",
  "#14b8a6",
  "#f97316",
  "#06b6d4",
  "#8b5cf6",
  "#ef4444",
  "#22c55e",
  "#eab308",
  "#0ea5e9",
  "#d946ef",
  "#64748b",
  "#f43f5e",
  "#84cc16",
  "#a3e635",
  "#fb923c",
  "#38bdf8",
  "#c084fc",
  "#4ade80",
  "#fbbf24",
];

export function getTickerColor(ticker: string, allTickers: string[]): string {
  const idx = allTickers.indexOf(ticker);
  return TICKER_PALETTE[idx >= 0 ? idx % TICKER_PALETTE.length : 0];
}

export type VixZone = "low" | "normal" | "elevated" | "extreme";

export function getVixZone(value: number): VixZone {
  if (value < 15) return "low";
  if (value < 25) return "normal";
  if (value < 35) return "elevated";
  return "extreme";
}

// --- Indicator Types ---

export type IndicatorType = "sma" | "ema" | "rsi" | "macd" | "bollinger" | "vwap" | "atr" | "stochastic" | "obv" | "adx";

export interface IndicatorPoint {
  date: string;
  time: number;
  values: Record<string, number | null>;
}

// --- Search Types ---

export interface SearchResult {
  ticker: string;
  has_data: boolean;
}

export interface SearchResponse {
  results: SearchResult[];
  query: string;
}

// --- Portfolio Types ---

export interface HoldingResponse {
  ticker: string;
  shares: number;
  avg_cost: number;
  added_at: string;
}

export interface PortfolioResponse {
  holdings: HoldingResponse[];
}

export interface PortfolioAddRequest {
  ticker: string;
  shares: number;
  avg_cost: number;
}

export interface PortfolioUpdateRequest {
  shares?: number;
  avg_cost?: number;
}

export interface PortfolioSummaryItem {
  ticker: string;
  shares: number;
  avg_cost: number;
  current_price: number | null;
  market_value: number | null;
  total_gain: number | null;
  gain_pct: number | null;
}

export interface PortfolioSummaryResponse {
  holdings: PortfolioSummaryItem[];
}

// --- Alert Types ---

export type AlertCondition = "above" | "below" | "percent_change_above" | "percent_change_below";

export interface AlertResponse {
  id: string;
  ticker: string;
  condition: string;
  threshold: number;
  enabled: boolean;
  cooldown_seconds: number;
  last_triggered: string | null;
  created_at: string;
  channels: string[];
  telegram_chat_id: string;
  email: string;
}

export interface AlertCreateRequest {
  ticker: string;
  condition: AlertCondition;
  threshold: number;
  cooldown_seconds?: number;
  channels?: string[];
  telegram_chat_id?: string;
  email?: string;
}

export interface AlertListResponse {
  alerts: AlertResponse[];
}

export interface SummaryRequest {
  tickers?: string[];
  days?: number;
}

export interface SummaryResponse {
  summary: string;
  model: string;
  total_duration_ms: number;
  eval_count: number;
  tickers: string[];
  days: number;
}

export interface ChatRequest {
  message: string;
  session_id?: string;
  tickers?: string[];
  days?: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
}

// --- Fundamentals Types ---

export interface FundamentalsResponse {
  ticker: string;
  short_name: string | null;
  long_name: string | null;
  sector: string | null;
  industry: string | null;
  market_cap: number | null;
  trailing_pe: number | null;
  forward_pe: number | null;
  trailing_eps: number | null;
  forward_eps: number | null;
  dividend_yield: number | null;
  total_revenue: number | null;
  profit_margins: number | null;
  fifty_two_week_high: number | null;
  fifty_two_week_low: number | null;
  average_volume: number | null;
  beta: number | null;
  currency: string | null;
  quote_type: string | null;
}

// --- News Types ---
export interface NewsArticle {
  uuid: string | null;
  title: string | null;
  link: string | null;
  publisher: string | null;
  provider_publish_time: number | null;
  type: string | null;
  related_tickers: string[] | null;
  thumbnail_url: string | null;
}

export interface NewsResponse {
  ticker: string;
  count: number;
  articles: NewsArticle[];
}

export const INDICATOR_COLORS: Record<string, string> = {
  SMA: "#3b89ff",
  EMA: "#ff6b35",
  RSI: "#a78bfa",
  MACD: "#36bb80",
  Signal: "#ff4d8d",
  Histogram: "#fdbc2a",
  BB_Upper: "#00d4ff",
  BB_Middle: "#3b89ff",
  BB_Lower: "#00d4ff",
  VWAP: "#06b6d4",
  ATR: "#f97316",
  Stoch_K: "#8b5cf6",
  Stoch_D: "#ec4899",
  OBV: "#22c55e",
  ADX: "#eab308",
  Plus_DI: "#36bb80",
  Minus_DI: "#ff4d8d",
};

export const VIX_ZONE_CONFIG: Record<VixZone, { label: string; color: string; bg: string; border: string }> = {
  low: {
    label: "Low Volatility",
    color: "#00ff88",
    bg: "rgba(0,255,136,0.08)",
    border: "rgba(0,255,136,0.3)",
  },
  normal: {
    label: "Normal",
    color: "#ffd700",
    bg: "rgba(255,215,0,0.08)",
    border: "rgba(255,215,0,0.3)",
  },
  elevated: {
    label: "Elevated",
    color: "#ff6b35",
    bg: "rgba(255,107,53,0.08)",
    border: "rgba(255,107,53,0.3)",
  },
  extreme: {
    label: "Extreme Fear",
    color: "#ff3366",
    bg: "rgba(255,51,102,0.08)",
    border: "rgba(255,51,102,0.3)",
  },
};
