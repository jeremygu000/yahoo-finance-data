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
import { fetchCompare } from "@/lib/api";
import type { CompareData } from "@/lib/types";
import { TICKERS, TICKER_COLORS, type Ticker } from "@/lib/types";

const DAYS_OPTIONS = [30, 90, 180, 365] as const;
type Days = (typeof DAYS_OPTIONS)[number];

const CHART_THEME = {
  background: { type: ColorType.Solid, color: "#080d18" },
  textColor: "#8892a4",
  grid: { vertLines: { color: "#111827" }, horzLines: { color: "#111827" } },
  crosshair: { vertLine: { color: "#334155" }, horzLine: { color: "#334155" } },
};

export default function PriceComparison() {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesMap = useRef<Map<string, ISeriesApi<"Line">>>(new Map());

  const [days, setDays] = useState<Days>(90);
  const [selected, setSelected] = useState<Set<Ticker>>(
    new Set(["QQQ", "XOM", "XLE"]),
  );
  const [data, setData] = useState<CompareData>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 380,
      layout: CHART_THEME,
      grid: CHART_THEME.grid,
      crosshair: CHART_THEME.crosshair,
      rightPriceScale: { borderColor: "#1e293b" },
      timeScale: { borderColor: "#1e293b", timeVisible: true },
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
  }, []);

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
      const color = TICKER_COLORS[t as Ticker] ?? "#ffffff";
      let series = seriesMap.current.get(t);
      if (!series) {
        series = chart.addSeries(LineSeries, { color, lineWidth: 2 });
        seriesMap.current.set(t, series);
      }
      const lineData = points.map((p) => ({
        time: p.time as UTCTimestamp,
        value: p.close,
      }));
      series.setData(lineData);
    }

    chart.timeScale().fitContent();
  }, [data]);

  function toggleTicker(t: Ticker) {
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
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex flex-wrap gap-2">
          {TICKERS.map((t) => {
            const active = selected.has(t);
            const color = TICKER_COLORS[t];
            return (
              <button
                key={t}
                onClick={() => toggleTicker(t)}
                className={`flex items-center gap-1.5 px-3 py-1 rounded text-xs font-mono transition-all border ${
                  active
                    ? "border-transparent"
                    : "border-[var(--c-border)] text-[var(--c-muted)]"
                }`}
                style={
                  active
                    ? {
                        backgroundColor: `${color}22`,
                        color,
                        borderColor: `${color}55`,
                      }
                    : {}
                }
              >
                <span
                  className="w-2 h-2 rounded-full inline-block"
                  style={{ background: active ? color : "var(--c-border)" }}
                />
                {t}
              </button>
            );
          })}
        </div>
        <div className="ml-auto flex gap-1">
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
    </div>
  );
}
