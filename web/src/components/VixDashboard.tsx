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
import { fetchOHLCV, fetchLatest } from "@/lib/api";
import type { OHLCVBar, LatestQuote } from "@/lib/types";
import { getVixZone, VIX_ZONE_CONFIG } from "@/lib/types";

const DAYS_OPTIONS = [30, 90, 180, 365] as const;
type Days = (typeof DAYS_OPTIONS)[number];

const ZONE_LINES = [
  { value: 15, label: "15", color: "#22c55e" },
  { value: 25, label: "25", color: "#eab308" },
  { value: 35, label: "35", color: "#f97316" },
];

export default function VixDashboard() {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const lineRef = useRef<ISeriesApi<"Line"> | null>(null);

  const [days, setDays] = useState<Days>(365);
  const [latest, setLatest] = useState<LatestQuote | null>(null);
  const [history, setHistory] = useState<OHLCVBar[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 300,
      layout: {
        background: { type: ColorType.Solid, color: "#080d18" },
        textColor: "#8892a4",
      },
      grid: {
        vertLines: { color: "#111827" },
        horzLines: { color: "#111827" },
      },
      crosshair: {
        vertLine: { color: "#334155" },
        horzLine: { color: "#334155" },
      },
      rightPriceScale: { borderColor: "#1e293b" },
      timeScale: { borderColor: "#1e293b", timeVisible: true },
    });
    chartRef.current = chart;

    const series = chart.addSeries(LineSeries, {
      color: "#ff6b35",
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
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [bars, q] = await Promise.all([
          fetchOHLCV("VIX", days),
          fetchLatest("VIX"),
        ]);
        setHistory(bars);
        setLatest(q);
        if (lineRef.current) {
          const lineData = bars.map((b) => ({
            time: b.time as UTCTimestamp,
            value: b.close,
          }));
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
    <div className="space-y-4">
      {error && (
        <div className="text-[var(--c-red)] text-sm font-mono p-3 border border-[var(--c-red)]/30 rounded">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div
          className="card flex flex-col gap-3"
          style={
            zoneConfig
              ? { borderColor: zoneConfig.border, background: zoneConfig.bg }
              : {}
          }
        >
          <div className="text-xs text-[var(--c-muted)] uppercase tracking-wider">
            VIX Current Value
          </div>
          {loading ? (
            <div className="h-16 animate-pulse bg-[var(--c-surface-2)] rounded" />
          ) : vixValue !== null ? (
            <>
              <div
                className="text-5xl font-mono font-bold tracking-tight"
                style={{ color: zoneConfig?.color ?? "var(--c-text)" }}
              >
                {vixValue.toFixed(2)}
              </div>
              {zoneConfig && (
                <div
                  className="inline-flex items-center gap-2 text-sm font-mono px-3 py-1.5 rounded-full w-fit"
                  style={{
                    backgroundColor: zoneConfig.bg,
                    color: zoneConfig.color,
                    border: `1px solid ${zoneConfig.border}`,
                  }}
                >
                  <span
                    className="w-2 h-2 rounded-full"
                    style={{ background: zoneConfig.color }}
                  />
                  {zoneConfig.label}
                </div>
              )}
              <div className="text-xs text-[var(--c-muted)] font-mono">
                As of {latest?.date}
              </div>
            </>
          ) : (
            <div className="text-[var(--c-muted)] font-mono">No data</div>
          )}
        </div>

        <div className="card flex flex-col gap-3">
          <div className="text-xs text-[var(--c-muted)] uppercase tracking-wider">
            VIX Zones
          </div>
          <div className="space-y-2">
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
                <div
                  key={z}
                  className="flex items-center justify-between px-3 py-2 rounded text-xs font-mono transition-all"
                  style={
                    isActive
                      ? {
                          backgroundColor: cfg.bg,
                          border: `1px solid ${cfg.border}`,
                        }
                      : { border: "1px solid transparent" }
                  }
                >
                  <div className="flex items-center gap-2">
                    <span
                      className="w-2 h-2 rounded-full"
                      style={{ background: cfg.color }}
                    />
                    <span
                      style={{
                        color: isActive ? cfg.color : "var(--c-text-dim)",
                      }}
                    >
                      {cfg.label}
                    </span>
                  </div>
                  <span className="text-[var(--c-muted)]">{ranges[z]}</span>
                  {isActive && vixValue !== null && (
                    <span
                      className="font-semibold"
                      style={{ color: cfg.color }}
                    >
                      ← {vixValue.toFixed(2)}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {stats && (
        <div className="grid grid-cols-3 gap-3">
          {[
            {
              label: `${days}d Min`,
              value: stats.min.toFixed(2),
              color: "var(--c-green)",
            },
            {
              label: `${days}d Avg`,
              value: stats.avg.toFixed(2),
              color: "var(--c-text)",
            },
            {
              label: `${days}d Max`,
              value: stats.max.toFixed(2),
              color: "var(--c-red)",
            },
          ].map((s) => (
            <div key={s.label} className="card text-center">
              <div className="text-[10px] text-[var(--c-muted)] uppercase tracking-wider mb-1">
                {s.label}
              </div>
              <div
                className="font-mono text-xl font-bold"
                style={{ color: s.color }}
              >
                {s.value}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {ZONE_LINES.map((z) => (
            <span
              key={z.value}
              className="flex items-center gap-1 text-[10px] font-mono text-[var(--c-muted)]"
            >
              <span
                className="w-4 h-px inline-block"
                style={{ background: z.color }}
              />
              {z.label}
            </span>
          ))}
        </div>
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
