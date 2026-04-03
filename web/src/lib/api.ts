import type { TickerInfo, OHLCVBar, LatestQuote, CompareData } from "./types";

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
