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
import { TICKERS } from "@/lib/types";
import { useThemeMode } from "./ThemeProvider";

const DAYS_OPTIONS = [30, 90, 180, 365] as const;
type Days = (typeof DAYS_OPTIONS)[number];

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

export default function CandlestickChart() {
  const containerRef = useRef<HTMLDivElement>(null);
  const volumeContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const volumeChartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeRef = useRef<ISeriesApi<"Histogram"> | null>(null);

  const [ticker, setTicker] = useState<string>("QQQ");
  const [days, setDays] = useState<Days>(365);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<OHLCVBar[]>([]);

  const { mode } = useThemeMode();

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
      timeScale: { borderColor: theme.borderColor, timeVisible: true },
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
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const bars = await fetchOHLCV(ticker, days);
        setData(bars);
        if (candleRef.current && volumeRef.current) {
          const candles = bars.map((b) => ({
            time: b.time as UTCTimestamp,
            open: b.open,
            high: b.high,
            low: b.low,
            close: b.close,
          }));
          const volumes = bars.map((b) => ({
            time: b.time as UTCTimestamp,
            value: b.volume,
            color: b.close >= b.open ? "rgba(54,187,128,0.4)" : "rgba(255,113,52,0.4)",
          }));
          candleRef.current.setData(candles);
          volumeRef.current.setData(volumes);
          chartRef.current?.timeScale().fitContent();
          volumeChartRef.current?.timeScale().fitContent();
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [ticker, days]);

  const latest = data[data.length - 1];

  return (
    <Card>
      <CardContent sx={{ p: 3 }}>
        <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 2, mb: 3 }}>
          <FormControl size="small" sx={{ minWidth: 100 }}>
            <InputLabel>Ticker</InputLabel>
            <Select value={ticker} label="Ticker" onChange={(e) => setTicker(e.target.value)}>
              {TICKERS.map((t) => (
                <MenuItem key={t} value={t}>
                  {t}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <ToggleButtonGroup
            value={days}
            exclusive
            onChange={(_, v) => {
              if (v !== null) setDays(v as Days);
            }}
            size="small"
          >
            {DAYS_OPTIONS.map((d) => (
              <ToggleButton key={d} value={d}>
                {d}d
              </ToggleButton>
            ))}
          </ToggleButtonGroup>

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
