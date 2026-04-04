"use client";

import { useEffect, useState } from "react";
import { fetchTickers } from "@/lib/api";

interface UseTickersResult {
  tickers: string[];
  loading: boolean;
}

/** Module-level cache so every component shares one fetch. */
let cachedTickers: string[] | null = null;
let inflightPromise: Promise<string[]> | null = null;

function loadTickers(): Promise<string[]> {
  if (cachedTickers) return Promise.resolve(cachedTickers);
  if (inflightPromise) return inflightPromise;

  inflightPromise = fetchTickers()
    .then((infos) => {
      cachedTickers = infos.map((i) => i.ticker).toSorted();
      inflightPromise = null;
      return cachedTickers;
    })
    .catch((err) => {
      inflightPromise = null;
      throw err;
    });

  return inflightPromise;
}

export default function useTickers(): UseTickersResult {
  const [tickers, setTickers] = useState<string[]>(cachedTickers ?? []);
  const [loading, setLoading] = useState(cachedTickers === null);

  useEffect(() => {
    if (cachedTickers) {
      setTickers(cachedTickers);
      setLoading(false);
      return;
    }

    let cancelled = false;
    loadTickers()
      .then((list) => {
        if (!cancelled) {
          setTickers(list);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return { tickers, loading };
}
