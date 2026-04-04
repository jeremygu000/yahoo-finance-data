"use client";

import { createContext, useContext, useMemo } from "react";
import { usePriceWebSocket } from "@/lib/useWebSocket";
import type { PriceUpdate, AlertTriggered } from "@/lib/types";
import type { WSStatus } from "@/lib/useWebSocket";

interface PriceContextValue {
  prices: Record<string, PriceUpdate>;
  alerts: AlertTriggered[];
  wsStatus: WSStatus;
  subscribedTickers: string[];
  subscribe: (tickers: string[]) => void;
  unsubscribe: (tickers: string[]) => void;
}

const PriceContext = createContext<PriceContextValue>({
  prices: {},
  alerts: [],
  wsStatus: "disconnected",
  subscribedTickers: [],
  subscribe: () => {},
  unsubscribe: () => {},
});

export function useLivePrices(): PriceContextValue {
  return useContext(PriceContext);
}

export default function PriceProvider({ children }: { children: React.ReactNode }) {
  const { prices, alerts, status, subscribedTickers, subscribe, unsubscribe } = usePriceWebSocket();
  const value = useMemo<PriceContextValue>(
    () => ({ prices, alerts, wsStatus: status, subscribedTickers, subscribe, unsubscribe }),
    [prices, alerts, status, subscribedTickers, subscribe, unsubscribe],
  );

  return <PriceContext.Provider value={value}>{children}</PriceContext.Provider>;
}
