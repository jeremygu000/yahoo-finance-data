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
import { fetchOHLCV } from "@/lib/api";
import type { OHLCVBar } from "@/lib/types";
import { TICKERS } from "@/lib/types";

const DAYS_OPTIONS = [30, 90, 180, 365] as const;
type Days = (typeof DAYS_OPTIONS)[number];

const CHART_THEME = {
  background: { type: ColorType.Solid, color: "#080d18" },
  textColor: "#8892a4",
  grid: { vertLines: { color: "#111827" }, horzLines: { color: "#111827" } },
  crosshair: { vertLine: { color: "#334155" }, horzLine: { color: "#334155" } },
};

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

  useEffect(() => {
    if (!containerRef.current || !volumeContainerRef.current) return;

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 340,
      layout: CHART_THEME,
      grid: CHART_THEME.grid,
      crosshair: CHART_THEME.crosshair,
      rightPriceScale: { borderColor: "#1e293b" },
      timeScale: { borderColor: "#1e293b", timeVisible: true },
    });
    chartRef.current = chart;

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#00ff88",
      downColor: "#ff3366",
      borderUpColor: "#00ff88",
      borderDownColor: "#ff3366",
      wickUpColor: "#00cc6a",
      wickDownColor: "#cc2952",
    });
    candleRef.current = candleSeries;

    const volumeChart = createChart(volumeContainerRef.current, {
      width: volumeContainerRef.current.clientWidth,
      height: 80,
      layout: CHART_THEME,
      grid: CHART_THEME.grid,
      rightPriceScale: { borderColor: "#1e293b" },
      timeScale: { borderColor: "#1e293b", timeVisible: false },
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
  }, []);

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
            color:
              b.close >= b.open
                ? "rgba(0,255,136,0.4)"
                : "rgba(255,51,102,0.4)",
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
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <label className="text-xs text-[var(--c-muted)] uppercase tracking-wider">
            Ticker
          </label>
          <select
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            className="select-field"
          >
            {TICKERS.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs text-[var(--c-muted)] uppercase tracking-wider">
            Range
          </label>
          <div className="flex gap-1">
            {DAYS_OPTIONS.map((d) => (
              <button
                key={d}
                onClick={() => setDays(d)}
                className={`px-2 py-1 text-xs font-mono rounded transition-colors ${
                  days === d
                    ? "bg-[var(--c-accent)] text-[var(--c-bg)] font-semibold"
                    : "text-[var(--c-muted)] hover:text-[var(--c-text)] hover:bg-[var(--c-surface-2)]"
                }`}
              >
                {d}d
              </button>
            ))}
          </div>
        </div>
        {latest && (
          <div className="ml-auto flex items-center gap-4 font-mono text-xs">
            {(["O", "H", "L", "C"] as const).map((label, i) => {
              const val = [latest.open, latest.high, latest.low, latest.close][
                i
              ];
              return (
                <span key={label}>
                  <span className="text-[var(--c-muted)]">{label} </span>
                  <span className="text-[var(--c-text)]">{val.toFixed(2)}</span>
                </span>
              );
            })}
          </div>
        )}
      </div>

      {error && (
        <div className="text-[var(--c-red)] text-sm font-mono p-3 border border-[var(--c-red)]/30 rounded">
          {error}
        </div>
      )}

      <div className="relative rounded overflow-hidden border border-[var(--c-border)]">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-[var(--c-bg)]/80 z-10">
            <div className="loading-spinner" />
          </div>
        )}
        <div ref={containerRef} className="w-full" />
      </div>

      <div className="relative rounded overflow-hidden border border-[var(--c-border)]">
        <div className="absolute top-1 left-2 text-[10px] text-[var(--c-muted)] uppercase tracking-wider z-10">
          Volume
        </div>
        <div ref={volumeContainerRef} className="w-full" />
      </div>
    </div>
  );
}
