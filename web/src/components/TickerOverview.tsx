"use client";

import { useEffect, useState } from "react";
import { fetchTickers, fetchLatest } from "@/lib/api";
import type { TickerInfo, LatestQuote } from "@/lib/types";
import { TICKERS } from "@/lib/types";

interface TickerCard extends TickerInfo {
  latest: LatestQuote | null;
  change: number | null;
  changePct: number | null;
}

function formatPrice(n: number): string {
  return n.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatVolume(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return n.toString();
}

export default function TickerOverview() {
  const [cards, setCards] = useState<TickerCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const infos = await fetchTickers();
        const enriched = await Promise.all(
          infos.map(async (info) => {
            const latest = await fetchLatest(info.ticker);
            let change: number | null = null;
            let changePct: number | null = null;
            if (latest) {
              change = latest.close - latest.open;
              changePct = ((latest.close - latest.open) / latest.open) * 100;
            }
            return { ...info, latest, change, changePct };
          }),
        );
        setCards(enriched);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="grid grid-cols-2 xl:grid-cols-3 gap-4">
        {TICKERS.map((t) => (
          <div key={t} className="card animate-pulse h-36" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-[var(--c-red)] font-mono text-sm p-4 border border-[var(--c-red)]/30 rounded bg-[var(--c-red)]/5">
        {error}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 xl:grid-cols-3 gap-4">
      {cards.map((card) => {
        const isUp = card.change !== null && card.change >= 0;
        const changeColor =
          card.change === null
            ? "text-[var(--c-muted)]"
            : isUp
              ? "text-[var(--c-green)]"
              : "text-[var(--c-red)]";

        return (
          <div
            key={card.ticker}
            className="card group hover:border-[var(--c-accent)]/50 transition-colors"
          >
            <div className="flex items-start justify-between mb-3">
              <div>
                <span className="ticker-badge">{card.ticker}</span>
              </div>
              {card.change !== null && (
                <div
                  className={`text-xs font-mono font-semibold px-2 py-0.5 rounded ${isUp ? "bg-[var(--c-green)]/10 text-[var(--c-green)]" : "bg-[var(--c-red)]/10 text-[var(--c-red)]"}`}
                >
                  {isUp ? "▲" : "▼"} {Math.abs(card.changePct ?? 0).toFixed(2)}%
                </div>
              )}
            </div>

            <div className="mb-3">
              {card.latest ? (
                <div className="text-2xl font-mono font-bold text-[var(--c-text)]">
                  {formatPrice(card.latest.close)}
                </div>
              ) : (
                <div className="text-lg font-mono text-[var(--c-muted)]">—</div>
              )}
              {card.change !== null && (
                <div className={`text-sm font-mono ${changeColor}`}>
                  {card.change >= 0 ? "+" : ""}
                  {formatPrice(card.change)}
                </div>
              )}
            </div>

            <div className="border-t border-[var(--c-border)] pt-3 grid grid-cols-2 gap-x-4 gap-y-1">
              <div className="text-[10px] text-[var(--c-muted)] uppercase tracking-wider">
                Rows
              </div>
              <div className="text-[10px] text-[var(--c-muted)] uppercase tracking-wider">
                Size
              </div>
              <div className="font-mono text-xs text-[var(--c-text-dim)]">
                {card.rows.toLocaleString()}
              </div>
              <div className="font-mono text-xs text-[var(--c-text-dim)]">
                {card.size_kb} KB
              </div>
              <div className="text-[10px] text-[var(--c-muted)] uppercase tracking-wider col-span-2 mt-1">
                Range
              </div>
              <div className="font-mono text-xs text-[var(--c-text-dim)] col-span-2">
                {card.first_date} → {card.last_date}
              </div>
              {card.latest && (
                <>
                  <div className="text-[10px] text-[var(--c-muted)] uppercase tracking-wider mt-1">
                    Volume
                  </div>
                  <div className="font-mono text-xs text-[var(--c-text-dim)] mt-1">
                    {formatVolume(card.latest.volume)}
                  </div>
                </>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
