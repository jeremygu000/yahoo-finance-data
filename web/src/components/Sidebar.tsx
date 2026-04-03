"use client";

import { useState, useEffect } from "react";

const NAV_ITEMS = [
  { id: "overview", label: "Overview", icon: "◈" },
  { id: "candlestick", label: "Candlestick", icon: "▨" },
  { id: "comparison", label: "Comparison", icon: "≋" },
  { id: "table", label: "Data Table", icon: "⊞" },
  { id: "vix", label: "VIX", icon: "◎" },
] as const;

type SectionId = (typeof NAV_ITEMS)[number]["id"];

export default function Sidebar() {
  const [active, setActive] = useState<SectionId>("overview");

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting && entry.intersectionRatio >= 0.3) {
            setActive(entry.target.id as SectionId);
          }
        }
      },
      { threshold: 0.3, rootMargin: "-10% 0px -60% 0px" },
    );

    for (const item of NAV_ITEMS) {
      const el = document.getElementById(item.id);
      if (el) observer.observe(el);
    }

    return () => observer.disconnect();
  }, []);

  function scrollTo(id: SectionId) {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  return (
    <aside className="fixed left-0 top-0 h-screen w-56 flex flex-col border-r border-[var(--c-border)] bg-[var(--c-surface)] z-50">
      <div className="px-5 py-5 border-b border-[var(--c-border)]">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded bg-[var(--c-accent)]/20 border border-[var(--c-accent)]/40 flex items-center justify-center text-[var(--c-accent)] text-sm font-bold">
            M
          </div>
          <div>
            <div className="text-sm font-semibold text-[var(--c-text)] leading-tight">
              MarketTerminal
            </div>
            <div className="text-[10px] text-[var(--c-muted)] font-mono">
              v1.0.0
            </div>
          </div>
        </div>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV_ITEMS.map((item) => {
          const isActive = active === item.id;
          return (
            <button
              key={item.id}
              onClick={() => scrollTo(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded text-sm transition-all text-left ${
                isActive
                  ? "bg-[var(--c-accent)]/10 text-[var(--c-accent)] border border-[var(--c-accent)]/20"
                  : "text-[var(--c-text-dim)] hover:text-[var(--c-text)] hover:bg-[var(--c-surface-2)] border border-transparent"
              }`}
            >
              <span
                className={`text-base leading-none font-mono ${isActive ? "text-[var(--c-accent)]" : "text-[var(--c-muted)]"}`}
              >
                {item.icon}
              </span>
              <span className="font-medium">{item.label}</span>
              {isActive && (
                <span className="ml-auto w-1 h-4 rounded-full bg-[var(--c-accent)]" />
              )}
            </button>
          );
        })}
      </nav>

      <div className="px-4 py-4 border-t border-[var(--c-border)]">
        <div className="text-[10px] text-[var(--c-muted)] font-mono space-y-1">
          <div className="flex justify-between">
            <span>API</span>
            <span className="text-[var(--c-green)]">● Live</span>
          </div>
          <div className="text-[var(--c-border)] truncate">
            {process.env.NEXT_PUBLIC_API_URL ?? "localhost:8100"}
          </div>
        </div>
      </div>
    </aside>
  );
}
