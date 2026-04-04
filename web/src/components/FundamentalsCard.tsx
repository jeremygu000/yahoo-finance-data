"use client";

import { useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
import Autocomplete from "@mui/material/Autocomplete";
import TextField from "@mui/material/TextField";
import Skeleton from "@mui/material/Skeleton";
import Alert from "@mui/material/Alert";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import { fetchFundamentals } from "@/lib/api";
import type { FundamentalsResponse } from "@/lib/types";
import useTickers from "@/lib/useTickers";

function formatLargeNumber(n: number | null): string {
  if (n === null) return "—";
  if (n >= 1_000_000_000_000) return `$${(n / 1_000_000_000_000).toFixed(2)}T`;
  if (n >= 1_000_000_000) return `$${(n / 1_000_000_000).toFixed(2)}B`;
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(1)}K`;
  return `$${n.toFixed(2)}`;
}

function formatVolume(n: number | null): string {
  if (n === null) return "—";
  if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(2)}B`;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}

function formatPct(n: number | null): string {
  if (n === null) return "—";
  return `${(n * 100).toFixed(2)}%`;
}

function formatNum(n: number | null, decimals = 2): string {
  if (n === null) return "—";
  return n.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

interface MetricTileProps {
  label: string;
  value: string;
}

function MetricTile({ label, value }: MetricTileProps) {
  return (
    <Box
      sx={{
        p: 1.5,
        borderRadius: "8px",
        border: "1px solid",
        borderColor: "divider",
        bgcolor: "rgba(255,255,255,0.02)",
      }}
    >
      <Typography variant="caption" sx={{ color: "text.disabled", display: "block", mb: 0.5, letterSpacing: "0.05em", textTransform: "uppercase", fontSize: "0.65rem" }}>
        {label}
      </Typography>
      <Typography variant="body2" sx={{ fontFamily: "var(--font-geist-mono)", fontWeight: 600, color: "text.primary" }}>
        {value}
      </Typography>
    </Box>
  );
}

const SKELETON_TILES = Array.from({ length: 12 }, (_, i) => `sk-${String(i)}`);

export default function FundamentalsCard() {
  const { tickers } = useTickers();
  const [ticker, setTicker] = useState<string>("");
  const [data, setData] = useState<FundamentalsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (tickers.length > 0 && !ticker) setTicker(tickers[0]);
  }, [tickers, ticker]);

  useEffect(() => {
    if (!ticker) return;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const result = await fetchFundamentals(ticker);
        setData(result);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [ticker]);

  const displayName = data?.short_name ?? data?.long_name ?? ticker;

  const metrics: { label: string; value: string }[] = data
    ? [
        { label: "Market Cap", value: formatLargeNumber(data.market_cap) },
        { label: "P/E Ratio", value: formatNum(data.trailing_pe) },
        { label: "Forward P/E", value: formatNum(data.forward_pe) },
        { label: "EPS", value: data.trailing_eps !== null ? `$${formatNum(data.trailing_eps)}` : "—" },
        { label: "Forward EPS", value: data.forward_eps !== null ? `$${formatNum(data.forward_eps)}` : "—" },
        { label: "Dividend Yield", value: formatPct(data.dividend_yield) },
        { label: "Revenue", value: formatLargeNumber(data.total_revenue) },
        { label: "Profit Margin", value: formatPct(data.profit_margins) },
        { label: "Avg Volume", value: formatVolume(data.average_volume) },
        { label: "Beta", value: formatNum(data.beta) },
        { label: "Currency", value: data.currency ?? "—" },
        { label: "Quote Type", value: data.quote_type ?? "—" },
      ]
    : [];

  const hasRange = data && (data.fifty_two_week_low !== null || data.fifty_two_week_high !== null);
  const rangeText =
    data && hasRange
      ? `$${formatNum(data.fifty_two_week_low)} – $${formatNum(data.fifty_two_week_high)}`
      : "—";

  return (
    <Card>
      <CardContent sx={{ p: 3 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 3 }}>
          <Autocomplete
            size="small"
            options={tickers}
            value={ticker}
            onChange={(_, v) => { if (v) setTicker(v); }}
            disableClearable
            sx={{ minWidth: 140 }}
            renderInput={(params) => <TextField {...params} label="Ticker" />}
          />
          <Typography variant="caption" sx={{ ml: "auto", color: "text.disabled", fontFamily: "var(--font-geist-mono)" }}>
            Fundamentals
          </Typography>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {loading ? (
          <>
            <Box sx={{ mb: 2 }}>
              <Skeleton variant="text" width="40%" height={32} />
              <Box sx={{ display: "flex", gap: 1, mt: 1 }}>
                <Skeleton variant="rounded" width={80} height={24} />
                <Skeleton variant="rounded" width={120} height={24} />
              </Box>
            </Box>
            <Divider sx={{ mb: 2 }} />
            <Box sx={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))", gap: 1.5 }}>
              {SKELETON_TILES.map((k) => (
                <Skeleton key={k} variant="rounded" height={60} />
              ))}
            </Box>
          </>
        ) : data ? (
          <>
            <Box sx={{ mb: 2 }}>
              <Typography variant="h6" sx={{ fontWeight: 700, lineHeight: 1.2, mb: 0.75 }}>
                {displayName}
              </Typography>
              <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75 }}>
                {data.sector && (
                  <Chip
                    label={data.sector}
                    size="small"
                    sx={{ bgcolor: "rgba(59,137,255,0.12)", color: "#3b89ff", borderRadius: "6px", fontSize: "0.7rem", fontWeight: 600 }}
                  />
                )}
                {data.industry && (
                  <Chip
                    label={data.industry}
                    size="small"
                    sx={{ bgcolor: "rgba(255,255,255,0.06)", color: "text.secondary", borderRadius: "6px", fontSize: "0.7rem" }}
                  />
                )}
              </Box>
            </Box>

            <Divider sx={{ mb: 2 }} />

            <Box sx={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))", gap: 1.5, mb: 1.5 }}>
              {metrics.map((m) => (
                <MetricTile key={m.label} label={m.label} value={m.value} />
              ))}
            </Box>

            <Box
              sx={{
                p: 1.5,
                borderRadius: "8px",
                border: "1px solid",
                borderColor: "divider",
                bgcolor: "rgba(255,255,255,0.02)",
              }}
            >
              <Typography variant="caption" sx={{ color: "text.disabled", display: "block", mb: 0.5, letterSpacing: "0.05em", textTransform: "uppercase", fontSize: "0.65rem" }}>
                52-Week Range
              </Typography>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                <Typography variant="body2" sx={{ fontFamily: "var(--font-geist-mono)", fontWeight: 600, color: "text.primary" }}>
                  {rangeText}
                </Typography>
                {data.fifty_two_week_low !== null && data.fifty_two_week_high !== null && data.fifty_two_week_high > data.fifty_two_week_low && (
                  <Box sx={{ flex: 1, position: "relative", height: 6, borderRadius: "3px", bgcolor: "divider", overflow: "hidden" }}>
                    <Box
                      sx={{
                        position: "absolute",
                        left: 0,
                        top: 0,
                        height: "100%",
                        borderRadius: "3px",
                        bgcolor: "#3b89ff",
                        width: "100%",
                        background: "linear-gradient(90deg, #ff7134 0%, #ffd700 50%, #36bb80 100%)",
                      }}
                    />
                  </Box>
                )}
              </Box>
            </Box>
          </>
        ) : null}
      </CardContent>
    </Card>
  );
}
