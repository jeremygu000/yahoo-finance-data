export interface TickerInfo {
  ticker: string;
  rows: number;
  first_date: string;
  last_date: string;
  size_kb: number;
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
  type: "price_update" | "alert_triggered" | "error";
  data: PriceUpdate[] | AlertTriggered[] | string;
}

export type SortDirection = "asc" | "desc";

export type SortColumn = "date" | "open" | "high" | "low" | "close" | "volume";

export const TICKERS = ["QQQ", "VIX", "USO", "XOM", "XLE", "CRM"] as const;
export type Ticker = (typeof TICKERS)[number];

export const TICKER_COLORS: Record<Ticker, string> = {
  QQQ: "#00d4ff",
  VIX: "#ff6b35",
  USO: "#ffd700",
  XOM: "#00ff88",
  XLE: "#ff4d8d",
  CRM: "#a78bfa",
};

export type VixZone = "low" | "normal" | "elevated" | "extreme";

export function getVixZone(value: number): VixZone {
  if (value < 15) return "low";
  if (value < 25) return "normal";
  if (value < 35) return "elevated";
  return "extreme";
}

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
