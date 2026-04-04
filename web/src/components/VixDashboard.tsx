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
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";
import Grid from "@mui/material/Grid";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Alert from "@mui/material/Alert";
import CircularProgress from "@mui/material/CircularProgress";
import Skeleton from "@mui/material/Skeleton";
import { fetchOHLCV, fetchLatest } from "@/lib/api";
import type { OHLCVBar, LatestQuote } from "@/lib/types";
import { getVixZone, VIX_ZONE_CONFIG } from "@/lib/types";
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

export default function VixDashboard() {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const lineRef = useRef<ISeriesApi<"Line"> | null>(null);

  const [days, setDays] = useState<Days>(365);
  const [latest, setLatest] = useState<LatestQuote | null>(null);
  const [history, setHistory] = useState<OHLCVBar[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { mode } = useThemeMode();

  useEffect(() => {
    if (!containerRef.current) return;

    const theme = CHART_THEMES[mode];

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 300,
      layout: theme,
      grid: theme.grid,
      crosshair: theme.crosshair,
      rightPriceScale: { borderColor: theme.borderColor },
      timeScale: { borderColor: theme.borderColor, timeVisible: true },
    });
    chartRef.current = chart;

    const series = chart.addSeries(LineSeries, {
      color: "#ff7134",
      lineWidth: 2,
      priceLineVisible: true,
      lastValueVisible: true,
    });
    lineRef.current = series;

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
      setLoading(true);
      setError(null);
      try {
        const [bars, q] = await Promise.all([fetchOHLCV("VIX", days), fetchLatest("VIX")]);
        setHistory(bars);
        setLatest(q);
        if (lineRef.current) {
          const seen = new Set<number>();
          const lineData: { time: UTCTimestamp; value: number }[] = [];
          for (const b of bars) {
            const t = b.time as UTCTimestamp;
            if (!seen.has(t)) {
              seen.add(t);
              lineData.push({ time: t, value: b.close });
            }
          }
          lineData.sort((a, b) => (a.time as number) - (b.time as number));
          lineRef.current.setData(lineData);
          chartRef.current?.timeScale().fitContent();
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [days]);

  const vixValue = latest?.close ?? null;
  const zone = vixValue !== null ? getVixZone(vixValue) : null;
  const zoneConfig = zone ? VIX_ZONE_CONFIG[zone] : null;

  const stats =
    history.length > 0
      ? {
          min: Math.min(...history.map((b) => b.low)),
          max: Math.max(...history.map((b) => b.high)),
          avg: history.reduce((s, b) => s + b.close, 0) / history.length,
        }
      : null;

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      {error && <Alert severity="error">{error}</Alert>}

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card
            sx={{
              height: "100%",
              border: zoneConfig ? `1px solid ${zoneConfig.border}` : "none",
              bgcolor: zoneConfig ? zoneConfig.bg : "background.paper",
            }}
          >
            <CardContent sx={{ p: 3 }}>
              <Typography
                variant="caption"
                sx={{
                  color: "text.disabled",
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                  display: "block",
                  mb: 1.5,
                }}
              >
                VIX Current Value
              </Typography>
              {loading ? (
                <Skeleton variant="rectangular" height={64} sx={{ borderRadius: "8px" }} />
              ) : vixValue !== null ? (
                <>
                  <Typography
                    sx={{
                      fontFamily: "var(--font-geist-mono)",
                      fontWeight: 700,
                      fontSize: "3.5rem",
                      lineHeight: 1,
                      color: zoneConfig?.color ?? "text.primary",
                      mb: 1.5,
                    }}
                  >
                    {vixValue.toFixed(2)}
                  </Typography>
                  {zoneConfig && (
                    <Chip
                      label={zoneConfig.label}
                      size="small"
                      icon={
                        <Box
                          component="span"
                          sx={{
                            width: 8,
                            height: 8,
                            borderRadius: "50%",
                            bgcolor: zoneConfig.color,
                            ml: "8px !important",
                            mr: "-4px !important",
                          }}
                        />
                      }
                      sx={{
                        bgcolor: zoneConfig.bg,
                        color: zoneConfig.color,
                        border: `1px solid ${zoneConfig.border}`,
                        fontFamily: "var(--font-geist-mono)",
                        fontWeight: 600,
                        borderRadius: "999px",
                      }}
                    />
                  )}
                  <Typography variant="caption" sx={{ display: "block", mt: 1, color: "text.disabled" }}>
                    As of {latest?.date}
                  </Typography>
                </>
              ) : (
                <Typography sx={{ color: "text.disabled", fontFamily: "var(--font-geist-mono)" }}>No data</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 6 }}>
          <Card sx={{ height: "100%" }}>
            <CardContent sx={{ p: 3 }}>
              <Typography
                variant="caption"
                sx={{
                  color: "text.disabled",
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                  display: "block",
                  mb: 1.5,
                }}
              >
                VIX Zones
              </Typography>
              <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75 }}>
                {(["low", "normal", "elevated", "extreme"] as const).map((z) => {
                  const cfg = VIX_ZONE_CONFIG[z];
                  const isActive = zone === z;
                  const ranges: Record<string, string> = {
                    low: "< 15",
                    normal: "15 – 25",
                    elevated: "25 – 35",
                    extreme: "> 35",
                  };
                  return (
                    <Box
                      key={z}
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        px: 1.5,
                        py: 1,
                        borderRadius: "6px",
                        bgcolor: isActive ? cfg.bg : "transparent",
                        border: "1px solid",
                        borderColor: isActive ? cfg.border : "transparent",
                        transition: "all 0.2s",
                      }}
                    >
                      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                        <Box sx={{ width: 8, height: 8, borderRadius: "50%", bgcolor: cfg.color, flexShrink: 0 }} />
                        <Typography
                          sx={{
                            fontSize: "0.8rem",
                            fontFamily: "var(--font-geist-mono)",
                            color: isActive ? cfg.color : "text.secondary",
                            fontWeight: isActive ? 600 : 400,
                          }}
                        >
                          {cfg.label}
                        </Typography>
                      </Box>
                      <Typography
                        sx={{ fontSize: "0.75rem", fontFamily: "var(--font-geist-mono)", color: "text.disabled" }}
                      >
                        {ranges[z]}
                      </Typography>
                      {isActive && vixValue !== null && (
                        <Typography
                          sx={{
                            fontSize: "0.75rem",
                            fontFamily: "var(--font-geist-mono)",
                            fontWeight: 700,
                            color: cfg.color,
                          }}
                        >
                          ← {vixValue.toFixed(2)}
                        </Typography>
                      )}
                    </Box>
                  );
                })}
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {stats && (
        <Grid container spacing={2}>
          {[
            { label: `${days}d Min`, value: stats.min.toFixed(2), color: "#36bb80" },
            { label: `${days}d Avg`, value: stats.avg.toFixed(2), color: "text.primary" },
            { label: `${days}d Max`, value: stats.max.toFixed(2), color: "#ff7134" },
          ].map((s) => (
            <Grid key={s.label} size={{ xs: 4 }}>
              <Card>
                <CardContent sx={{ p: 2, textAlign: "center" }}>
                  <Typography
                    variant="caption"
                    sx={{
                      color: "text.disabled",
                      fontSize: "0.65rem",
                      textTransform: "uppercase",
                      letterSpacing: "0.06em",
                      display: "block",
                      mb: 0.5,
                    }}
                  >
                    {s.label}
                  </Typography>
                  <Typography
                    sx={{ fontFamily: "var(--font-geist-mono)", fontWeight: 700, fontSize: "1.25rem", color: s.color }}
                  >
                    {s.value}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      <Card>
        <CardContent sx={{ p: 3 }}>
          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "flex-end", mb: 2 }}>
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
    </Box>
  );
}
