from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pandas as pd

from market_data import store
from market_data.config import OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_TIMEOUT

logger = logging.getLogger(__name__)

_semaphore = asyncio.Semaphore(2)

SYSTEM_PROMPT = (
    "You are a senior financial analyst. "
    "Analyze the provided market data and give a concise, actionable summary. "
    "Include: 1) Overall market trend, 2) Notable movers and sector rotation, "
    "3) Key support/resistance levels, 4) Risk factors to watch. "
    "Use bullet points. Be direct and data-driven. No disclaimers."
)


def _format_ohlcv_csv(ticker: str, df: pd.DataFrame, tail: int = 10) -> str:
    recent = df.tail(tail)
    lines: list[str] = [f"Ticker: {ticker}"]
    lines.append("Date,Open,High,Low,Close,Volume")
    for ts, row in recent.iterrows():
        d = ts.strftime("%Y-%m-%d") if hasattr(ts, "strftime") else str(ts)
        lines.append(
            f"{d},{row['Open']:.2f},{row['High']:.2f}," f"{row['Low']:.2f},{row['Close']:.2f},{int(row['Volume'])}"
        )

    if len(df) >= 2:
        first_close = float(df.iloc[0]["Close"])
        last_close = float(df.iloc[-1]["Close"])
        pct = ((last_close - first_close) / first_close) * 100
        lines.append(f"Period change: {pct:+.2f}%")

    return "\n".join(lines)


def build_prompt(tickers: list[str], days: int = 30) -> str:
    sections: list[str] = []
    for t in tickers:
        df = store.load(t, days=days)
        if df.empty:
            sections.append(f"Ticker: {t}\nNo data available.")
            continue
        sections.append(_format_ohlcv_csv(t, df))

    data_block = "\n\n".join(sections)
    return (
        f"Analyze the following {days}-day OHLCV data for {len(tickers)} tickers.\n\n"
        f"{data_block}\n\n"
        "Provide a market summary following your role instructions."
    )


async def health_check() -> bool:
    try:
        async with httpx.AsyncClient(base_url=OLLAMA_HOST, timeout=5.0) as client:
            resp = await client.get("/api/tags")
            return resp.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


async def generate(
    prompt: str,
    system: str = SYSTEM_PROMPT,
    model: str = OLLAMA_MODEL,
) -> dict[str, Any]:
    timeout = httpx.Timeout(float(OLLAMA_TIMEOUT), connect=10.0)
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "keep_alive": "5m",
        "options": {"temperature": 0.3, "num_predict": 2048},
    }

    async with _semaphore:
        async with httpx.AsyncClient(base_url=OLLAMA_HOST, timeout=timeout) as client:
            resp = await client.post("/api/generate", json=payload)
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            return {
                "response": data.get("response", ""),
                "model": data.get("model", model),
                "total_duration_ms": data.get("total_duration", 0) // 1_000_000,
                "eval_count": data.get("eval_count", 0),
            }


async def generate_stream(
    prompt: str,
    system: str = SYSTEM_PROMPT,
    model: str = OLLAMA_MODEL,
) -> AsyncIterator[str]:
    timeout = httpx.Timeout(float(OLLAMA_TIMEOUT), connect=10.0)
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "system": system,
        "stream": True,
        "keep_alive": "5m",
        "options": {"temperature": 0.3, "num_predict": 2048},
    }

    async with _semaphore:
        async with httpx.AsyncClient(base_url=OLLAMA_HOST, timeout=timeout) as client:
            async with client.stream("POST", "/api/generate", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    import json

                    chunk: dict[str, Any] = json.loads(line)
                    token = chunk.get("response", "")
                    if token:
                        yield token
                    if chunk.get("done", False):
                        return


async def generate_summary(
    tickers: list[str],
    days: int = 30,
) -> dict[str, Any]:
    prompt = await asyncio.to_thread(build_prompt, tickers, days)
    return await generate(prompt)


async def generate_summary_stream(
    tickers: list[str],
    days: int = 30,
) -> AsyncIterator[str]:
    prompt = await asyncio.to_thread(build_prompt, tickers, days)
    async for token in generate_stream(prompt):
        yield token
