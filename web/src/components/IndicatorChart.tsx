"use client";

import { useEffect, useRef, useState } from "react";
import {
  createChart,
  LineSeries,
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
import { fetchOHLCV, fetchIndicators } from "@/lib/api";
import { INDICATOR_COLORS, type IndicatorType } from "@/lib/types";
import { useThemeMode } from "./ThemeProvider";
import useTickers from "@/lib/useTickers";
import { BollingerFillPlugin } from "./plugins/BollingerFillPlugin";

const DAYS_OPTIONS = [30, 90, 180, 365] as const;
type Days = (typeof DAYS_OPTIONS)[number];

const PERIOD_OPTIONS = [10, 14, 20, 50, 100, 200] as const;

const INDICATOR_OPTIONS: { value: IndicatorType; label: string }[] = [
  { value: "sma", label: "SMA" },
  { value: "ema", label: "EMA" },
  { value: "rsi", label: "RSI" },
  { value: "macd", label: "MACD" },
  { value: "bollinger", label: "Bollinger Bands" },
];

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

export default function IndicatorChart() {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const priceSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const indicatorSeriesRef = useRef<ISeriesApi<"Line" | "Histogram">[]>([]);

  const { tickers } = useTickers();
  const [ticker, setTicker] = useState<string>("");
  const [indicator, setIndicator] = useState<IndicatorType>("sma");
  const [period, setPeriod] = useState<number>(20);
  const [days, setDays] = useState<Days>(365);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { mode } = useThemeMode();

  useEffect(() => {
    if (tickers.length > 0 && !ticker) setTicker(tickers[0]);
  }, [tickers, ticker]);

  useEffect(() => {
    if (!containerRef.current) return;

    const theme = CHART_THEMES[mode];

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 400,
      layout: theme,
      grid: theme.grid,
      crosshair: theme.crosshair,
      rightPriceScale: { borderColor: theme.borderColor },
      timeScale: { borderColor: theme.borderColor, timeVisible: true },
    });
    chartRef.current = chart;

    const priceSeries = chart.addSeries(LineSeries, {
      color: "#627183",
      lineWidth: 1,
      lineStyle: 2,
      priceScaleId: "right",
    });
    priceSeriesRef.current = priceSeries;

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
    if (!ticker) return;
    async function load() {
      if (!chartRef.current || !priceSeriesRef.current) return;

      setLoading(true);
      setError(null);

      for (const s of indicatorSeriesRef.current) {
        chartRef.current.removeSeries(s);
      }
      indicatorSeriesRef.current = [];

      try {
        const [bars, points] = await Promise.all([
          fetchOHLCV(ticker, days),
          fetchIndicators(ticker, indicator, { period, days }),
        ]);

        const seenPrice = new Set<number>();
        const priceData: { time: UTCTimestamp; value: number }[] = [];
        for (const b of bars) {
          const t = b.time as UTCTimestamp;
          if (!seenPrice.has(t)) {
            seenPrice.add(t);
            priceData.push({ time: t, value: b.close });
          }
        }
        priceData.sort((a, b) => (a.time as number) - (b.time as number));
        priceSeriesRef.current.setData(priceData);

        const chart = chartRef.current;

        if (indicator === "sma" || indicator === "ema") {
          const key = indicator === "sma" ? "SMA" : "EMA";
          const color = INDICATOR_COLORS[key] ?? "#3b89ff";
          const series = chart.addSeries(LineSeries, { color, lineWidth: 2 });
          indicatorSeriesRef.current.push(series);

          const seen = new Set<number>();
          const lineData: { time: UTCTimestamp; value: number }[] = [];
          for (const p of points) {
            const t = p.time as UTCTimestamp;
            const v = p.values[key];
            if (!seen.has(t) && v !== null && v !== undefined) {
              seen.add(t);
              lineData.push({ time: t, value: v });
            }
          }
          lineData.sort((a, b) => (a.time as number) - (b.time as number));
          series.setData(lineData);
        } else if (indicator === "rsi") {
          const color = INDICATOR_COLORS["RSI"] ?? "#a78bfa";
          const series = chart.addSeries(LineSeries, {
            color,
            lineWidth: 2,
            priceScaleId: "rsi",
          });
          chart.priceScale("rsi").applyOptions({ scaleMargins: { top: 0.7, bottom: 0 } });
          indicatorSeriesRef.current.push(series);

          const obSeries = chart.addSeries(LineSeries, {
            color: "rgba(255,77,141,0.4)",
            lineWidth: 1,
            lineStyle: 1,
            priceScaleId: "rsi",
          });
          indicatorSeriesRef.current.push(obSeries);

          const osSeries = chart.addSeries(LineSeries, {
            color: "rgba(54,187,128,0.4)",
            lineWidth: 1,
            lineStyle: 1,
            priceScaleId: "rsi",
          });
          indicatorSeriesRef.current.push(osSeries);

          const seen = new Set<number>();
          const rsiData: { time: UTCTimestamp; value: number }[] = [];
          const obData: { time: UTCTimestamp; value: number }[] = [];
          const osData: { time: UTCTimestamp; value: number }[] = [];
          for (const p of points) {
            const t = p.time as UTCTimestamp;
            const v = p.values["RSI"];
            if (!seen.has(t) && v !== null && v !== undefined) {
              seen.add(t);
              rsiData.push({ time: t, value: v });
              obData.push({ time: t, value: 70 });
              osData.push({ time: t, value: 30 });
            }
          }
          rsiData.sort((a, b) => (a.time as number) - (b.time as number));
          obData.sort((a, b) => (a.time as number) - (b.time as number));
          osData.sort((a, b) => (a.time as number) - (b.time as number));
          series.setData(rsiData);
          obSeries.setData(obData);
          osSeries.setData(osData);
        } else if (indicator === "macd") {
          const macdSeries = chart.addSeries(LineSeries, {
            color: INDICATOR_COLORS["MACD"] ?? "#36bb80",
            lineWidth: 2,
            priceScaleId: "macd",
          });
          const signalSeries = chart.addSeries(LineSeries, {
            color: INDICATOR_COLORS["Signal"] ?? "#ff4d8d",
            lineWidth: 2,
            priceScaleId: "macd",
          });
          const histSeries = chart.addSeries(HistogramSeries, {
            color: INDICATOR_COLORS["Histogram"] ?? "#fdbc2a",
            priceScaleId: "macd",
          });
          chart.priceScale("macd").applyOptions({ scaleMargins: { top: 0.6, bottom: 0 } });
          indicatorSeriesRef.current.push(macdSeries, signalSeries, histSeries);

          const seen = new Set<number>();
          const macdData: { time: UTCTimestamp; value: number }[] = [];
          const signalData: { time: UTCTimestamp; value: number }[] = [];
          const histData: { time: UTCTimestamp; value: number; color: string }[] = [];

          for (const p of points) {
            const t = p.time as UTCTimestamp;
            const m = p.values["MACD"];
            const s = p.values["Signal"];
            const h = p.values["Histogram"];
            if (
              !seen.has(t) &&
              m !== null &&
              m !== undefined &&
              s !== null &&
              s !== undefined &&
              h !== null &&
              h !== undefined
            ) {
              seen.add(t);
              macdData.push({ time: t, value: m });
              signalData.push({ time: t, value: s });
              histData.push({ time: t, value: h, color: h >= 0 ? "rgba(54,187,128,0.7)" : "rgba(255,113,52,0.7)" });
            }
          }
          macdData.sort((a, b) => (a.time as number) - (b.time as number));
          signalData.sort((a, b) => (a.time as number) - (b.time as number));
          histData.sort((a, b) => (a.time as number) - (b.time as number));
          macdSeries.setData(macdData);
          signalSeries.setData(signalData);
          histSeries.setData(histData);
        } else if (indicator === "bollinger") {
          const upperSeries = chart.addSeries(LineSeries, {
            color: INDICATOR_COLORS["BB_Upper"] ?? "#00d4ff",
            lineWidth: 1,
            lineStyle: 2,
          });
          const middleSeries = chart.addSeries(LineSeries, {
            color: INDICATOR_COLORS["BB_Middle"] ?? "#3b89ff",
            lineWidth: 2,
          });
          const lowerSeries = chart.addSeries(LineSeries, {
            color: INDICATOR_COLORS["BB_Lower"] ?? "#00d4ff",
            lineWidth: 1,
            lineStyle: 2,
          });
          indicatorSeriesRef.current.push(upperSeries, middleSeries, lowerSeries);

          const seen = new Set<number>();
          const upperData: { time: UTCTimestamp; value: number }[] = [];
          const middleData: { time: UTCTimestamp; value: number }[] = [];
          const lowerData: { time: UTCTimestamp; value: number }[] = [];

          for (const p of points) {
            const t = p.time as UTCTimestamp;
            const u = p.values["BB_Upper"];
            const m = p.values["BB_Middle"];
            const l = p.values["BB_Lower"];
            if (
              !seen.has(t) &&
              u !== null &&
              u !== undefined &&
              m !== null &&
              m !== undefined &&
              l !== null &&
              l !== undefined
            ) {
              seen.add(t);
              upperData.push({ time: t, value: u });
              middleData.push({ time: t, value: m });
              lowerData.push({ time: t, value: l });
            }
          }
          upperData.sort((a, b) => (a.time as number) - (b.time as number));
          middleData.sort((a, b) => (a.time as number) - (b.time as number));
          lowerData.sort((a, b) => (a.time as number) - (b.time as number));
          upperSeries.setData(upperData);
          middleSeries.setData(middleData);
          lowerSeries.setData(lowerData);

          const bandData = upperData.map((u, i) => ({
            time: u.time,
            upper: u.value,
            lower: lowerData[i].value,
          }));
          const fillPlugin = new BollingerFillPlugin(bandData);
          upperSeries.attachPrimitive(fillPlugin);
        }

        chart.timeScale().fitContent();
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [ticker, indicator, period, days]);

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

          <FormControl size="small" sx={{ minWidth: 140 }}>
            <InputLabel>Indicator</InputLabel>
            <Select value={indicator} label="Indicator" onChange={(e) => setIndicator(e.target.value as IndicatorType)}>
              {INDICATOR_OPTIONS.map((opt) => (
                <MenuItem key={opt.value} value={opt.value}>
                  {opt.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {indicator !== "macd" && (
            <FormControl size="small" sx={{ minWidth: 90 }}>
              <InputLabel>Period</InputLabel>
              <Select value={period} label="Period" onChange={(e) => setPeriod(Number(e.target.value))}>
                {PERIOD_OPTIONS.map((p) => (
                  <MenuItem key={p} value={p}>
                    {p}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}

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

          <Box sx={{ ml: "auto", display: "flex", alignItems: "center", gap: 1.5 }}>
            {(indicator === "sma" || indicator === "ema") && (
              <Box sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
                <Box
                  component="span"
                  sx={{
                    width: 20,
                    height: 2,
                    bgcolor: INDICATOR_COLORS[indicator === "sma" ? "SMA" : "EMA"],
                    borderRadius: 1,
                    display: "inline-block",
                  }}
                />
                <Typography
                  variant="caption"
                  sx={{ fontFamily: "var(--font-geist-mono)", fontSize: "0.7rem", color: "text.secondary" }}
                >
                  {indicator.toUpperCase()}({period})
                </Typography>
              </Box>
            )}
            {indicator === "bollinger" && (
              <Box sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
                <Box
                  component="span"
                  sx={{
                    width: 20,
                    height: 2,
                    bgcolor: INDICATOR_COLORS["BB_Middle"],
                    borderRadius: 1,
                    display: "inline-block",
                  }}
                />
                <Typography
                  variant="caption"
                  sx={{ fontFamily: "var(--font-geist-mono)", fontSize: "0.7rem", color: "text.secondary" }}
                >
                  BB({period})
                </Typography>
              </Box>
            )}
            {indicator === "macd" && (
              <>
                {(["MACD", "Signal"] as const).map((k) => (
                  <Box key={k} sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
                    <Box
                      component="span"
                      sx={{
                        width: 20,
                        height: 2,
                        bgcolor: INDICATOR_COLORS[k],
                        borderRadius: 1,
                        display: "inline-block",
                      }}
                    />
                    <Typography
                      variant="caption"
                      sx={{ fontFamily: "var(--font-geist-mono)", fontSize: "0.7rem", color: "text.secondary" }}
                    >
                      {k}
                    </Typography>
                  </Box>
                ))}
              </>
            )}
            {indicator === "rsi" && (
              <Box sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
                <Box
                  component="span"
                  sx={{
                    width: 20,
                    height: 2,
                    bgcolor: INDICATOR_COLORS["RSI"],
                    borderRadius: 1,
                    display: "inline-block",
                  }}
                />
                <Typography
                  variant="caption"
                  sx={{ fontFamily: "var(--font-geist-mono)", fontSize: "0.7rem", color: "text.secondary" }}
                >
                  RSI({period})
                </Typography>
              </Box>
            )}
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
