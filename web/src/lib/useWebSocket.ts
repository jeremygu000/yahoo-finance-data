"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import type { PriceUpdate, WSMessage, AlertTriggered, WSSubscribeMessage } from "./types";

const WS_BASE = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8100").replace(/^http/, "ws");
const WS_API_KEY = process.env.NEXT_PUBLIC_API_KEY ?? "";
const WS_URL = WS_BASE + "/ws/prices" + (WS_API_KEY ? `?api_key=${encodeURIComponent(WS_API_KEY)}` : "");
const RECONNECT_DELAY_MS = 3000;
const MAX_RECONNECT_ATTEMPTS = 10;
const MAX_ALERTS = 10;

export type WSStatus = "connecting" | "connected" | "disconnected";

export function usePriceWebSocket() {
  const [prices, setPrices] = useState<Record<string, PriceUpdate>>({});
  const [alerts, setAlerts] = useState<AlertTriggered[]>([]);
  const [status, setStatus] = useState<WSStatus>("disconnected");
  const [subscribedTickers, setSubscribedTickers] = useState<string[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const attemptsRef = useRef(0);
  const unmountedRef = useRef(false);
  const pendingSubRef = useRef<WSSubscribeMessage[]>([]);

  const sendMessage = useCallback((msg: WSSubscribeMessage) => {
    const ws = wsRef.current;
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(msg));
    } else {
      pendingSubRef.current.push(msg);
    }
  }, []);

  const subscribe = useCallback(
    (tickers: string[]) => {
      if (tickers.length > 0) {
        sendMessage({ action: "subscribe", tickers });
      }
    },
    [sendMessage],
  );

  const unsubscribe = useCallback(
    (tickers: string[]) => {
      if (tickers.length > 0) {
        sendMessage({ action: "unsubscribe", tickers });
      }
    },
    [sendMessage],
  );

  const connect = useCallback(() => {
    if (unmountedRef.current) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setStatus("connecting");
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.addEventListener("open", () => {
      setStatus("connected");
      attemptsRef.current = 0;
      for (const msg of pendingSubRef.current) {
        ws.send(JSON.stringify(msg));
      }
      pendingSubRef.current = [];
    });

    ws.addEventListener("message", (event) => {
      try {
        const msg = JSON.parse(event.data as string) as WSMessage;

        if (msg.type === "ping") {
          ws.send(JSON.stringify({ type: "pong" }));
          return;
        }

        if (msg.type === "subscribed" || msg.type === "unsubscribed") {
          if (Array.isArray(msg.tickers)) {
            setSubscribedTickers(msg.tickers);
          }
          return;
        }

        if (msg.type === "price_update" && Array.isArray(msg.data)) {
          setPrices((prev) => {
            const next = { ...prev };
            for (const update of msg.data as PriceUpdate[]) {
              next[update.ticker] = update;
            }
            return next;
          });
        } else if (msg.type === "alert_triggered" && Array.isArray(msg.data)) {
          setAlerts((prev) => {
            const newAlerts = msg.data as AlertTriggered[];
            const combined = [...newAlerts, ...prev];
            return combined.slice(0, MAX_ALERTS);
          });
        }
      } catch {
        /* empty */
      }
    });

    ws.addEventListener("close", () => {
      setStatus("disconnected");
      wsRef.current = null;
      if (!unmountedRef.current && attemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
        attemptsRef.current += 1;
        setTimeout(connect, RECONNECT_DELAY_MS);
      }
    });

    ws.addEventListener("error", () => {
      ws.close();
    });
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

  return { prices, alerts, status, subscribedTickers, subscribe, unsubscribe };
}
