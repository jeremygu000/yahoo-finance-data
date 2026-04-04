import type {
  TickerInfo,
  TickerOverviewResponse,
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
  AlertResponse,
  AlertCreateRequest,
  AlertListResponse,
  SummaryRequest,
  SummaryResponse,
  ChatRequest,
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

export async function fetchTickerNames(): Promise<string[]> {
  return fetcher<string[]>("/api/v1/tickers/names");
}

export async function fetchTickerOverview(
  page = 1,
  pageSize = 24,
  search = "",
): Promise<TickerOverviewResponse> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (search) params.set("search", search);
  return fetcher<TickerOverviewResponse>(`/api/v1/tickers/overview?${params.toString()}`);
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

export async function fetchAlerts(ticker?: string): Promise<AlertListResponse> {
  const params = ticker ? `?ticker=${encodeURIComponent(ticker)}` : "";
  return fetcher<AlertListResponse>(`/api/v1/alerts${params}`);
}

export async function createAlert(data: AlertCreateRequest): Promise<AlertResponse> {
  const res = await fetch(`${BASE_URL}/api/v1/alerts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`API error ${res.status}: POST /api/v1/alerts`);
  return res.json() as Promise<AlertResponse>;
}

export async function deleteAlert(alertId: string): Promise<AlertListResponse> {
  const res = await fetch(`${BASE_URL}/api/v1/alerts/${alertId}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`API error ${res.status}: DELETE /api/v1/alerts/${alertId}`);
  return res.json() as Promise<AlertListResponse>;
}

export async function fetchAlertChannels(): Promise<string[]> {
  const data = await fetcher<{ channels: string[] }>("/api/v1/alerts/channels");
  return data.channels;
}

export async function testAlertNotification(alertId: string): Promise<{ status: string; results?: Record<string, boolean> }> {
  const res = await fetch(`${BASE_URL}/api/v1/alerts/test/${alertId}`, { method: "POST" });
  if (!res.ok) throw new Error(`API error ${res.status}: POST /api/v1/alerts/test/${alertId}`);
  return res.json() as Promise<{ status: string; results?: Record<string, boolean> }>;
}

export async function fetchAiHealth(): Promise<{ available: boolean }> {
  return fetcher<{ available: boolean }>("/api/v1/ai/health");
}

export async function fetchAiSummary(req: SummaryRequest): Promise<SummaryResponse> {
  const res = await fetch(`${BASE_URL}/api/v1/ai/summary`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`API error ${res.status}: POST /api/v1/ai/summary`);
  return res.json() as Promise<SummaryResponse>;
}

export async function streamAiSummary(
  req: SummaryRequest,
  onToken: (token: string) => void,
  onDone: () => void,
): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/v1/ai/summary/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`API error ${res.status}: POST /api/v1/ai/summary/stream`);
  if (!res.body) throw new Error("No response body for streaming");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finished = false;

  async function readNext(): Promise<void> {
    const { done, value } = await reader.read();
    if (done) {
      onDone();
      return;
    }
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const token = line.slice(6);
        if (token === "[DONE]") {
          finished = true;
          onDone();
          return;
        }
        onToken(token);
      }
    }
    if (!finished) {
      return readNext();
    }
  }

  return readNext();
}

export async function streamAiChat(
  req: ChatRequest,
  onSessionId: (sessionId: string) => void,
  onToken: (token: string) => void,
  onDone: () => void,
): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/v1/ai/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`API error ${res.status}: POST /api/v1/ai/chat`);
  if (!res.body) throw new Error("No response body for streaming");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finished = false;
  let firstDataReceived = false;

  async function readNext(): Promise<void> {
    const { done, value } = await reader.read();
    if (done) {
      onDone();
      return;
    }
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const payload = line.slice(6);
        if (payload === "[DONE]") {
          finished = true;
          onDone();
          return;
        }
        if (!firstDataReceived) {
          firstDataReceived = true;
          try {
            const parsed = JSON.parse(payload) as { session_id: string };
            onSessionId(parsed.session_id);
          } catch {
            onToken(payload);
          }
        } else {
          onToken(payload);
        }
      }
    }
    if (!finished) {
      return readNext();
    }
  }

  return readNext();
}
