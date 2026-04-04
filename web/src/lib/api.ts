import type {
  TickerInfo,
  OHLCVBar,
  LatestQuote,
  CompareData,
  IndicatorPoint,
  IndicatorType,
  SearchResponse,
  PortfolioResponse,
  PortfolioAddRequest,
  PortfolioUpdateRequest,
  PortfolioSummaryResponse,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8100";

async function fetcher<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    next: { revalidate: 0 },
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${path}`);
  }
  return res.json() as Promise<T>;
}

export async function fetchTickers(): Promise<TickerInfo[]> {
  return fetcher<TickerInfo[]>("/api/tickers");
}

export async function fetchOHLCV(ticker: string, days = 365): Promise<OHLCVBar[]> {
  return fetcher<OHLCVBar[]>(`/api/ohlcv/${ticker}?days=${days}`);
}

export async function fetchLatest(ticker: string): Promise<LatestQuote | null> {
  return fetcher<LatestQuote | null>(`/api/latest/${ticker}`);
}

export async function fetchCompare(tickers: string[], days = 90): Promise<CompareData> {
  return fetcher<CompareData>(`/api/compare?tickers=${tickers.join(",")}&days=${days}`);
}

export async function fetchIndicators(
  ticker: string,
  indicator: IndicatorType,
  options: { period?: number; days?: number; fast?: number; slow?: number; signal?: number; stdDev?: number } = {},
): Promise<IndicatorPoint[]> {
  const params = new URLSearchParams({ indicator });
  if (options.period !== undefined) params.set("period", String(options.period));
  if (options.days !== undefined) params.set("days", String(options.days));
  if (options.fast !== undefined) params.set("fast", String(options.fast));
  if (options.slow !== undefined) params.set("slow", String(options.slow));
  if (options.signal !== undefined) params.set("signal", String(options.signal));
  if (options.stdDev !== undefined) params.set("std_dev", String(options.stdDev));
  return fetcher<IndicatorPoint[]>(`/api/v1/indicators/${ticker}?${params.toString()}`);
}

export async function searchTickers(query: string, limit = 10): Promise<SearchResponse> {
  return fetcher<SearchResponse>(`/api/v1/search?q=${encodeURIComponent(query)}&limit=${limit}`);
}

export function getExportUrl(ticker: string, days = 365): string {
  return `${BASE_URL}/api/v1/export/${ticker}?format=csv&days=${days}`;
}

export async function fetchPortfolio(): Promise<PortfolioResponse> {
  return fetcher<PortfolioResponse>("/api/v1/portfolio");
}

export async function addHolding(data: PortfolioAddRequest): Promise<PortfolioResponse> {
  const res = await fetch(`${BASE_URL}/api/v1/portfolio`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`API error ${res.status}: POST /api/v1/portfolio`);
  return res.json() as Promise<PortfolioResponse>;
}

export async function updateHolding(ticker: string, data: PortfolioUpdateRequest): Promise<PortfolioResponse> {
  const res = await fetch(`${BASE_URL}/api/v1/portfolio/${ticker}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`API error ${res.status}: PUT /api/v1/portfolio/${ticker}`);
  return res.json() as Promise<PortfolioResponse>;
}

export async function deleteHolding(ticker: string): Promise<PortfolioResponse> {
  const res = await fetch(`${BASE_URL}/api/v1/portfolio/${ticker}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`API error ${res.status}: DELETE /api/v1/portfolio/${ticker}`);
  return res.json() as Promise<PortfolioResponse>;
}

export async function fetchPortfolioSummary(): Promise<PortfolioSummaryResponse> {
  return fetcher<PortfolioSummaryResponse>("/api/v1/portfolio/summary");
}
