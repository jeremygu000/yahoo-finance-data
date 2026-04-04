"use client";

import { useEffect, useRef, useState } from "react";
import {
  createChart,
  LineSeries,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
  ColorType,
} from "lightweight-charts";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Alert from "@mui/material/Alert";
import CircularProgress from "@mui/material/CircularProgress";
import { fetchCompare } from "@/lib/api";
import type { CompareData } from "@/lib/types";
import { getTickerColor } from "@/lib/types";
import { useThemeMode } from "./ThemeProvider";
import useTickers from "@/lib/useTickers";

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

export default function PriceComparison() {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesMap = useRef<Map<string, ISeriesApi<"Line">>>(new Map());

  const { tickers } = useTickers();
  const [days, setDays] = useState<Days>(90);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [data, setData] = useState<CompareData>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { mode } = useThemeMode();

  useEffect(() => {
    if (tickers.length > 0 && selected.size === 0) {
      setSelected(new Set(tickers.slice(0, 3)));
    }
  }, [tickers, selected.size]);

  useEffect(() => {
    if (!containerRef.current) return;

    const theme = CHART_THEMES[mode];

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 380,
      layout: theme,
      grid: theme.grid,
      crosshair: theme.crosshair,
      rightPriceScale: { borderColor: theme.borderColor },
      timeScale: { borderColor: theme.borderColor, timeVisible: true },
    });
    chartRef.current = chart;

    const ro = new ResizeObserver(() => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    });
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      chart.remove();
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
  }, [mode]);

  useEffect(() => {
    async function load() {
      if (selected.size === 0) return;
      setLoading(true);
      setError(null);
      try {
        const result = await fetchCompare(Array.from(selected), days);
        setData(result);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [selected, days]);

  useEffect(() => {
    if (!chartRef.current) return;
    const chart = chartRef.current;

    const existingTickers = new Set(seriesMap.current.keys());
    const activeTickers = new Set(Object.keys(data));

    for (const t of existingTickers) {
      if (!activeTickers.has(t)) {
        const s = seriesMap.current.get(t);
        if (s) {
          chart.removeSeries(s);
          seriesMap.current.delete(t);
        }
      }
    }

    for (const [t, points] of Object.entries(data)) {
      const color = getTickerColor(t, tickers);
      let series = seriesMap.current.get(t);
      if (!series) {
        series = chart.addSeries(LineSeries, { color, lineWidth: 2 });
        seriesMap.current.set(t, series);
      }
      const seen = new Set<number>();
      const lineData: { time: UTCTimestamp; value: number }[] = [];
      for (const p of points) {
        const t = p.time as UTCTimestamp;
        if (!seen.has(t)) {
          seen.add(t);
          lineData.push({ time: t, value: p.close });
        }
      }
      lineData.sort((a, b) => (a.time as number) - (b.time as number));
      series.setData(lineData);
    }

    chart.timeScale().fitContent();
  }, [data, tickers]);

  function toggleTicker(t: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(t)) {
        if (next.size === 1) return prev;
        next.delete(t);
      } else {
        next.add(t);
      }
      return next;
    });
  }

  return (
    <Card>
      <CardContent sx={{ p: 3 }}>
        <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 2, mb: 3 }}>
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
            {tickers.map((t) => {
              const active = selected.has(t);
              const color = getTickerColor(t, tickers);
              return (
                <Chip
                  key={t}
                  label={t}
                  onClick={() => toggleTicker(t)}
                  size="small"
                  sx={{
                    fontFamily: "var(--font-geist-mono)",
                    fontWeight: 600,
                    fontSize: "0.75rem",
                    cursor: "pointer",
                    bgcolor: active ? `${color}22` : "transparent",
                    color: active ? color : "text.disabled",
                    border: "1px solid",
                    borderColor: active ? `${color}55` : "divider",
                    "&:hover": {
                      bgcolor: active ? `${color}33` : "action.hover",
                    },
                  }}
                  icon={
                    <Box
                      component="span"
                      sx={{
                        width: 7,
                        height: 7,
                        borderRadius: "50%",
                        bgcolor: active ? color : "divider",
                        ml: "6px !important",
                        mr: "-2px !important",
                      }}
                    />
                  }
                />
              );
            })}
          </Box>

          <Box sx={{ ml: "auto" }}>
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
          </Box>
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
      </CardContent>
    </Card>
  );
}
