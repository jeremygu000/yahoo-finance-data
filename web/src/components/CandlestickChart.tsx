"use client";

import { useEffect, useRef, useState } from "react";
import {
  createChart,
  CandlestickSeries,
  HistogramSeries,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
  ColorType,
} from "lightweight-charts";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Alert from "@mui/material/Alert";
import CircularProgress from "@mui/material/CircularProgress";
import { fetchOHLCV } from "@/lib/api";
import type { OHLCVBar } from "@/lib/types";
import { useThemeMode } from "./ThemeProvider";
import ExportButton from "./ExportButton";
import useTickers from "@/lib/useTickers";
import { VolumeProfilePlugin, type VolumeBar } from "./plugins/VolumeProfilePlugin";

type KLineInterval = "daily" | "weekly" | "monthly";

const INTERVAL_OPTIONS: { value: KLineInterval; label: string }[] = [
  { value: "daily", label: "日K" },
  { value: "weekly", label: "周K" },
  { value: "monthly", label: "月K" },
];

const FULL_HISTORY_DAYS = 3650;

const CHART_THEMES = {
  light: {
    background: { type: ColorType.Solid, color: "#ffffff" },
    textColor: "#627183",
    grid: { vertLines: { color: "#f0f2f5" }, horzLines: { color: "#f0f2f5" } },
    crosshair: { vertLine: { color: "#c5cdd8" }, horzLine: { color: "#c5cdd8" } },
    borderColor: "#e5e9ef",
    loadingBg: "rgba(255,255,255,0.8)",
  },
  dark: {
    background: { type: ColorType.Solid, color: "#111827" },
    textColor: "#8899aa",
    grid: { vertLines: { color: "#1e2a3a" }, horzLines: { color: "#1e2a3a" } },
    crosshair: { vertLine: { color: "#2d3748" }, horzLine: { color: "#2d3748" } },
    borderColor: "#1e2a3a",
    loadingBg: "rgba(17,24,39,0.8)",
  },
} as const;

function getMondayDateString(d: Date): string {
  const day = d.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  const monday = new Date(d);
  monday.setDate(d.getDate() + diff);
  const y = monday.getFullYear();
  const m = String(monday.getMonth() + 1).padStart(2, "0");
  const dd = String(monday.getDate()).padStart(2, "0");
  return `${y}-${m}-${dd}`;
}

function aggregateWeekly(bars: OHLCVBar[]): OHLCVBar[] {
  const weekMap = new Map<string, OHLCVBar>();
  for (const bar of bars) {
    const d = new Date(bar.date);
    const weekKey = getMondayDateString(d);
    const existing = weekMap.get(weekKey);
    if (!existing) {
      weekMap.set(weekKey, { ...bar, date: weekKey });
    } else {
      existing.high = Math.max(existing.high, bar.high);
      existing.low = Math.min(existing.low, bar.low);
      existing.close = bar.close;
      existing.volume += bar.volume;
    }
  }
  return Array.from(weekMap.values()).toSorted((a, b) => a.time - b.time);
}

function aggregateMonthly(bars: OHLCVBar[]): OHLCVBar[] {
  const monthMap = new Map<string, OHLCVBar>();
  for (const bar of bars) {
    const monthKey = bar.date.substring(0, 7);
    const existing = monthMap.get(monthKey);
    if (!existing) {
      monthMap.set(monthKey, { ...bar });
    } else {
      existing.high = Math.max(existing.high, bar.high);
      existing.low = Math.min(existing.low, bar.low);
      existing.close = bar.close;
      existing.volume += bar.volume;
    }
  }
  return Array.from(monthMap.values()).toSorted((a, b) => a.time - b.time);
}

export default function CandlestickChart() {
  const containerRef = useRef<HTMLDivElement>(null);
  const volumeContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const volumeChartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeRef = useRef<ISeriesApi<"Histogram"> | null>(null);

  const { tickers } = useTickers();
  const [ticker, setTicker] = useState<string>("");
  const [interval, setInterval] = useState<KLineInterval>("daily");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rawBars, setRawBars] = useState<OHLCVBar[]>([]);
  const [showVP, setShowVP] = useState(false);
  const vpPluginRef = useRef<VolumeProfilePlugin | null>(null);

  const { mode } = useThemeMode();

  useEffect(() => {
    if (tickers.length > 0 && !ticker) setTicker(tickers[0]);
  }, [tickers, ticker]);

  useEffect(() => {
    if (!containerRef.current || !volumeContainerRef.current) return;

    const theme = CHART_THEMES[mode];

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 340,
      layout: theme,
      grid: theme.grid,
      crosshair: theme.crosshair,
      rightPriceScale: { borderColor: theme.borderColor },
      timeScale: { borderColor: theme.borderColor, timeVisible: false },
    });
    chartRef.current = chart;

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#36bb80",
      downColor: "#ff7134",
      borderUpColor: "#36bb80",
      borderDownColor: "#ff7134",
      wickUpColor: "#2a9264",
      wickDownColor: "#d95620",
    });
    candleRef.current = candleSeries;

    const volumeChart = createChart(volumeContainerRef.current, {
      width: volumeContainerRef.current.clientWidth,
      height: 80,
      layout: theme,
      grid: theme.grid,
      rightPriceScale: { borderColor: theme.borderColor },
      timeScale: { borderColor: theme.borderColor, timeVisible: false },
    });
    volumeChartRef.current = volumeChart;

    const volumeSeries = volumeChart.addSeries(HistogramSeries, {
      priceFormat: { type: "volume" },
      priceScaleId: "",
    });
    volumeRef.current = volumeSeries;

    const ro = new ResizeObserver(() => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
      if (volumeContainerRef.current) {
        volumeChart.applyOptions({
          width: volumeContainerRef.current.clientWidth,
        });
      }
    });
    if (containerRef.current) ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      chart.remove();
      volumeChart.remove();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const theme = CHART_THEMES[mode];
    chartRef.current?.applyOptions({
      layout: theme,
      grid: theme.grid,
      crosshair: theme.crosshair,
      rightPriceScale: { borderColor: theme.borderColor },
      timeScale: { borderColor: theme.borderColor },
    });
    volumeChartRef.current?.applyOptions({
      layout: theme,
      grid: theme.grid,
      rightPriceScale: { borderColor: theme.borderColor },
      timeScale: { borderColor: theme.borderColor },
    });
  }, [mode]);

  useEffect(() => {
    if (!ticker) return;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const bars = await fetchOHLCV(ticker, FULL_HISTORY_DAYS);
        setRawBars(bars);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [ticker]);

  useEffect(() => {
    if (!candleRef.current || !volumeRef.current || rawBars.length === 0) return;

    const displayBars: OHLCVBar[] =
      interval === "weekly"
        ? aggregateWeekly(rawBars)
        : interval === "monthly"
          ? aggregateMonthly(rawBars)
          : rawBars;

    const seen = new Set<number>();
    const candles: { time: UTCTimestamp; open: number; high: number; low: number; close: number }[] = [];
    const volumes: { time: UTCTimestamp; value: number; color: string }[] = [];

    for (const b of displayBars) {
      const t = b.time as UTCTimestamp;
      if (!seen.has(t)) {
        seen.add(t);
        candles.push({ time: t, open: b.open, high: b.high, low: b.low, close: b.close });
        volumes.push({
          time: t,
          value: b.volume,
          color: b.close >= b.open ? "rgba(54,187,128,0.4)" : "rgba(255,113,52,0.4)",
        });
      }
    }

    candles.sort((a, b) => (a.time as number) - (b.time as number));
    volumes.sort((a, b) => (a.time as number) - (b.time as number));

    candleRef.current.setData(candles);
    volumeRef.current.setData(volumes);
    chartRef.current?.timeScale().fitContent();
    volumeChartRef.current?.timeScale().fitContent();
  }, [rawBars, interval]);

  useEffect(() => {
    if (!candleRef.current) return;

    if (showVP) {
      const displayBars: OHLCVBar[] =
        interval === "weekly"
          ? aggregateWeekly(rawBars)
          : interval === "monthly"
            ? aggregateMonthly(rawBars)
            : rawBars;

      const vpBars: VolumeBar[] = displayBars.map((b) => ({
        time: b.time,
        open: b.open,
        close: b.close,
        high: b.high,
        low: b.low,
        volume: b.volume,
      }));

      if (!vpPluginRef.current) {
        const plugin = new VolumeProfilePlugin();
        plugin.setData(vpBars);
        candleRef.current.attachPrimitive(plugin);
        vpPluginRef.current = plugin;
      } else {
        vpPluginRef.current.setData(vpBars);
      }
    } else if (vpPluginRef.current) {
      candleRef.current.detachPrimitive(vpPluginRef.current);
      vpPluginRef.current = null;
    }
  }, [showVP, rawBars, interval]);

  const displayBarsForLatest: OHLCVBar[] =
    interval === "weekly"
      ? aggregateWeekly(rawBars)
      : interval === "monthly"
        ? aggregateMonthly(rawBars)
        : rawBars;

  const latest = displayBarsForLatest[displayBarsForLatest.length - 1];

  return (
    <Card>
      <CardContent sx={{ p: 3 }}>
        <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 2, mb: 3 }}>
          <FormControl size="small" sx={{ minWidth: 100 }}>
            <InputLabel>Ticker</InputLabel>
            <Select value={ticker} label="Ticker" onChange={(e) => setTicker(e.target.value)}>
              {tickers.map((t) => (
                <MenuItem key={t} value={t}>
                  {t}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <ToggleButtonGroup
            value={interval}
            exclusive
            onChange={(_, v) => {
              if (v !== null) setInterval(v as KLineInterval);
            }}
            size="small"
          >
            {INTERVAL_OPTIONS.map((opt) => (
              <ToggleButton key={opt.value} value={opt.value}>
                {opt.label}
              </ToggleButton>
            ))}
          </ToggleButtonGroup>

          <ToggleButton
            value="vp"
            selected={showVP}
            onChange={() => setShowVP((v) => !v)}
            size="small"
            sx={{
              fontFamily: "var(--font-geist-mono)",
              fontSize: "0.75rem",
              fontWeight: 600,
            }}
          >
            VP
          </ToggleButton>

          <ExportButton ticker={ticker} days={FULL_HISTORY_DAYS} />

          {latest && (
            <Box sx={{ ml: "auto", display: "flex", gap: 3 }}>
              {(["O", "H", "L", "C"] as const).map((label, i) => {
                const val = [latest.open, latest.high, latest.low, latest.close][i];
                return (
                  <Box key={label}>
                    <Typography
                      variant="caption"
                      sx={{ color: "text.disabled", display: "block", fontSize: "0.65rem" }}
                    >
                      {label}
                    </Typography>
                    <Typography
                      sx={{
                        fontFamily: "var(--font-geist-mono)",
                        fontSize: "0.8rem",
                        fontWeight: 600,
                        color: "text.primary",
                      }}
                    >
                      {val.toFixed(2)}
                    </Typography>
                  </Box>
                );
              })}
            </Box>
          )}
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Box
          sx={{
            position: "relative",
            borderRadius: "8px",
            overflow: "hidden",
            border: "1px solid",
            borderColor: "divider",
          }}
        >
          {loading && (
            <Box
              sx={{
                position: "absolute",
                inset: 0,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                bgcolor: CHART_THEMES[mode].loadingBg,
                zIndex: 10,
              }}
            >
              <CircularProgress size={28} />
            </Box>
          )}
          <div ref={containerRef} style={{ width: "100%" }} />
        </Box>

        <Box
          sx={{
            position: "relative",
            mt: 1,
            borderRadius: "8px",
            overflow: "hidden",
            border: "1px solid",
            borderColor: "divider",
          }}
        >
          <Typography
            variant="caption"
            sx={{
              position: "absolute",
              top: 6,
              left: 10,
              color: "text.disabled",
              fontSize: "0.65rem",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              zIndex: 5,
            }}
          >
            Volume
          </Typography>
          <div ref={volumeContainerRef} style={{ width: "100%" }} />
        </Box>
      </CardContent>
    </Card>
  );
}
