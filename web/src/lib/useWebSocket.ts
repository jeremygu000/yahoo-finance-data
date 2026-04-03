"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import type { PriceUpdate, WSMessage } from "./types";

const WS_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8100").replace(/^http/, "ws") + "/ws/prices";
const RECONNECT_DELAY_MS = 3000;
const MAX_RECONNECT_ATTEMPTS = 10;

export type WSStatus = "connecting" | "connected" | "disconnected";

export function usePriceWebSocket() {
  const [prices, setPrices] = useState<Record<string, PriceUpdate>>({});
  const [status, setStatus] = useState<WSStatus>("disconnected");
  const wsRef = useRef<WebSocket | null>(null);
  const attemptsRef = useRef(0);
  const unmountedRef = useRef(false);

  const connect = useCallback(() => {
    if (unmountedRef.current) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setStatus("connecting");
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("connected");
      attemptsRef.current = 0;
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data) as WSMessage;
        if (msg.type === "price_update" && Array.isArray(msg.data)) {
          setPrices((prev) => {
            const next = { ...prev };
            for (const update of msg.data as PriceUpdate[]) {
              next[update.ticker] = update;
            }
            return next;
          });
        }
      } catch {
        /* empty */
      }
    };

    ws.onclose = () => {
      setStatus("disconnected");
      wsRef.current = null;
      if (!unmountedRef.current && attemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
        attemptsRef.current += 1;
        setTimeout(connect, RECONNECT_DELAY_MS);
      }
    };

    ws.onerror = () => {
      ws.close();
    };
  }, []);

  useEffect(() => {
    unmountedRef.current = false;
    connect();
    return () => {
      unmountedRef.current = true;
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [connect]);

  return { prices, status };
}
