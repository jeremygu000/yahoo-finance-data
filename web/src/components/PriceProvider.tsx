"use client";

import { createContext, useContext } from "react";
import { usePriceWebSocket } from "@/lib/useWebSocket";
import type { PriceUpdate, AlertTriggered } from "@/lib/types";
import type { WSStatus } from "@/lib/useWebSocket";

interface PriceContextValue {
  prices: Record<string, PriceUpdate>;
  alerts: AlertTriggered[];
  wsStatus: WSStatus;
}

const PriceContext = createContext<PriceContextValue>({
  prices: {},
  alerts: [],
  wsStatus: "disconnected",
});

export function useLivePrices(): PriceContextValue {
  return useContext(PriceContext);
}

export default function PriceProvider({ children }: { children: React.ReactNode }) {
  const { prices, alerts, status } = usePriceWebSocket();

  return (
    <PriceContext.Provider value={{ prices, alerts, wsStatus: status }}>
      {children}
    </PriceContext.Provider>
  );
}
