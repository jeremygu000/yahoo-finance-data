"use client";

import { useEffect, useState } from "react";
import { fetchOHLCV } from "@/lib/api";
import type { OHLCVBar, SortColumn, SortDirection } from "@/lib/types";
import { TICKERS } from "@/lib/types";

const PAGE_SIZE = 50;

function formatNum(n: number, decimals = 2): string {
  return n.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function formatVolume(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}

export default function DataTable() {
  const [ticker, setTicker] = useState<string>("QQQ");
  const [allData, setAllData] = useState<OHLCVBar[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortCol, setSortCol] = useState<SortColumn>("date");
  const [sortDir, setSortDir] = useState<SortDirection>("desc");
  const [page, setPage] = useState(0);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      setPage(0);
      try {
        const bars = await fetchOHLCV(ticker, 365);
        setAllData(bars);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [ticker]);

  function handleSort(col: SortColumn) {
    if (col === sortCol) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortCol(col);
      setSortDir("desc");
    }
    setPage(0);
  }

  const sorted = [...allData].sort((a, b) => {
    let av: string | number, bv: string | number;
    if (sortCol === "date") {
      av = a.date;
      bv = b.date;
    } else {
      av = a[sortCol];
      bv = b[sortCol];
    }
    if (av < bv) return sortDir === "asc" ? -1 : 1;
    if (av > bv) return sortDir === "asc" ? 1 : -1;
    return 0;
  });

  const totalPages = Math.ceil(sorted.length / PAGE_SIZE);
  const pageData = sorted.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  const cols: { key: SortColumn; label: string; align: "left" | "right" }[] = [
    { key: "date", label: "Date", align: "left" },
    { key: "open", label: "Open", align: "right" },
    { key: "high", label: "High", align: "right" },
    { key: "low", label: "Low", align: "right" },
    { key: "close", label: "Close", align: "right" },
    { key: "volume", label: "Volume", align: "right" },
  ];

  function SortIcon({ col }: { col: SortColumn }) {
    if (col !== sortCol)
      return <span className="text-[var(--c-border)]"> ⇅</span>;
    return (
      <span className="text-[var(--c-accent)]">
        {sortDir === "asc" ? " ↑" : " ↓"}
      </span>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
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
        {!loading && (
          <span className="text-xs text-[var(--c-muted)] font-mono ml-auto">
            {sorted.length.toLocaleString()} rows
          </span>
        )}
      </div>

      {error && (
        <div className="text-[var(--c-red)] text-sm font-mono p-3 border border-[var(--c-red)]/30 rounded">
          {error}
        </div>
      )}

      <div className="rounded border border-[var(--c-border)] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs font-mono">
            <thead>
              <tr className="border-b border-[var(--c-border)] bg-[var(--c-surface-2)]">
                {cols.map((col) => (
                  <th
                    key={col.key}
                    className={`px-4 py-2.5 font-semibold text-[var(--c-text-dim)] uppercase tracking-wider cursor-pointer hover:text-[var(--c-text)] select-none transition-colors ${
                      col.align === "right" ? "text-right" : "text-left"
                    }`}
                    onClick={() => handleSort(col.key)}
                  >
                    {col.label}
                    <SortIcon col={col.key} />
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading
                ? Array.from({ length: 10 }).map((_, i) => (
                    <tr
                      key={i}
                      className="border-b border-[var(--c-border)]/40"
                    >
                      {cols.map((col) => (
                        <td key={col.key} className="px-4 py-2.5">
                          <div className="h-3 rounded bg-[var(--c-surface-2)] animate-pulse w-full" />
                        </td>
                      ))}
                    </tr>
                  ))
                : pageData.map((row, i) => {
                    const isUp = row.close >= row.open;
                    return (
                      <tr
                        key={row.date + i}
                        className="border-b border-[var(--c-border)]/40 hover:bg-[var(--c-surface-2)] transition-colors"
                      >
                        <td className="px-4 py-2 text-[var(--c-text-dim)]">
                          {row.date}
                        </td>
                        <td className="px-4 py-2 text-right text-[var(--c-text)]">
                          {formatNum(row.open)}
                        </td>
                        <td className="px-4 py-2 text-right text-[var(--c-green)]">
                          {formatNum(row.high)}
                        </td>
                        <td className="px-4 py-2 text-right text-[var(--c-red)]">
                          {formatNum(row.low)}
                        </td>
                        <td
                          className={`px-4 py-2 text-right font-semibold ${isUp ? "text-[var(--c-green)]" : "text-[var(--c-red)]"}`}
                        >
                          {formatNum(row.close)}
                        </td>
                        <td className="px-4 py-2 text-right text-[var(--c-muted)]">
                          {formatVolume(row.volume)}
                        </td>
                      </tr>
                    );
                  })}
            </tbody>
          </table>
        </div>
      </div>

      {!loading && totalPages > 1 && (
        <div className="flex items-center justify-between">
          <button
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            className="px-3 py-1.5 text-xs font-mono rounded border border-[var(--c-border)] text-[var(--c-muted)] hover:text-[var(--c-text)] hover:border-[var(--c-text-dim)] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            ← Prev
          </button>
          <span className="text-xs font-mono text-[var(--c-muted)]">
            Page {page + 1} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={page === totalPages - 1}
            className="px-3 py-1.5 text-xs font-mono rounded border border-[var(--c-border)] text-[var(--c-muted)] hover:text-[var(--c-text)] hover:border-[var(--c-text-dim)] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
