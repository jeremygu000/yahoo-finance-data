from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pandas as pd

from market_data import store
from market_data.config import OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_TIMEOUT

logger = logging.getLogger(__name__)

_semaphore = asyncio.Semaphore(2)

_MAX_SESSIONS = 50
_SESSION_TTL = 3600

ChatMessage = dict[str, str]


class _ChatSession:
    __slots__ = ("session_id", "messages", "tickers", "days", "created_at", "updated_at")

    def __init__(
        self,
        session_id: str,
        messages: list[ChatMessage],
        tickers: list[str],
        days: int,
    ) -> None:
        self.session_id = session_id
        self.messages = messages
        self.tickers = tickers
        self.days = days
        self.created_at = time.monotonic()
        self.updated_at = time.monotonic()


_sessions: dict[str, _ChatSession] = {}


def _evict_stale_sessions() -> None:
    now = time.monotonic()
    expired = [sid for sid, s in _sessions.items() if now - s.updated_at > _SESSION_TTL]
    for sid in expired:
        del _sessions[sid]
    while len(_sessions) > _MAX_SESSIONS:
        oldest = min(_sessions, key=lambda k: _sessions[k].updated_at)
        del _sessions[oldest]


def create_session(tickers: list[str], days: int = 30) -> _ChatSession:
    _evict_stale_sessions()
    sid = uuid.uuid4().hex[:16]
    session = _ChatSession(session_id=sid, messages=[], tickers=tickers, days=days)
    _sessions[sid] = session
    return session


def get_session(session_id: str) -> _ChatSession | None:
    session = _sessions.get(session_id)
    if session is None:
        return None
    if time.monotonic() - session.updated_at > _SESSION_TTL:
        del _sessions[session_id]
        return None
    return session

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
        "think": True,
        "keep_alive": "5m",
        "options": {"temperature": 0.3, "num_predict": 2048},
    }

    async with _semaphore:
        async with httpx.AsyncClient(base_url=OLLAMA_HOST, timeout=timeout) as client:
            resp = await client.post("/api/generate", json=payload)
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            thinking = data.get("thinking", "")
            response = data.get("response", "")
            # Wrap thinking in <think> tags so frontend parseThinkTags works
            if thinking:
                response = f"<think>{thinking}</think>{response}"
            return {
                "response": response,
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
        "think": True,
        "keep_alive": "5m",
        "options": {"temperature": 0.3, "num_predict": 2048},
    }

    async with _semaphore:
        async with httpx.AsyncClient(base_url=OLLAMA_HOST, timeout=timeout) as client:
            async with client.stream("POST", "/api/generate", json=payload) as resp:
                resp.raise_for_status()
                in_thinking = False
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    chunk: dict[str, Any] = json.loads(line)
                    thinking_token = chunk.get("thinking", "")
                    response_token = chunk.get("response", "")

                    if thinking_token:
                        if not in_thinking:
                            yield "<think>"
                            in_thinking = True
                        yield thinking_token
                    elif in_thinking and response_token:
                        yield "</think>"
                        in_thinking = False
                        yield response_token
                    elif response_token:
                        yield response_token

                    if chunk.get("done", False):
                        if in_thinking:
                            yield "</think>"
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


async def chat_stream(
    messages: list[ChatMessage],
    model: str = OLLAMA_MODEL,
) -> AsyncIterator[str]:
    timeout = httpx.Timeout(float(OLLAMA_TIMEOUT), connect=10.0)
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": True,
        "think": True,
        "keep_alive": "5m",
        "options": {"temperature": 0.3, "num_predict": 2048},
    }

    async with _semaphore:
        async with httpx.AsyncClient(base_url=OLLAMA_HOST, timeout=timeout) as client:
            async with client.stream("POST", "/api/chat", json=payload) as resp:
                resp.raise_for_status()
                in_thinking = False
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    chunk: dict[str, Any] = json.loads(line)
                    msg = chunk.get("message", {})
                    thinking_token: str = msg.get("thinking", "")
                    content_token: str = msg.get("content", "")

                    if thinking_token:
                        if not in_thinking:
                            yield "<think>"
                            in_thinking = True
                        yield thinking_token
                    elif in_thinking and content_token:
                        yield "</think>"
                        in_thinking = False
                        yield content_token
                    elif content_token:
                        yield content_token

                    if chunk.get("done", False):
                        if in_thinking:
                            yield "</think>"
                        return


async def chat_stream_session(
    session_id: str | None,
    user_message: str,
    tickers: list[str] | None = None,
    days: int = 30,
) -> tuple[str, AsyncIterator[str]]:
    if session_id:
        session = get_session(session_id)
    else:
        session = None

    if session is None:
        resolved_tickers = tickers if tickers else await asyncio.to_thread(store.list_tickers)
        session = create_session(resolved_tickers, days=days)
        data_context = await asyncio.to_thread(build_prompt, resolved_tickers, days)
        session.messages.append({"role": "system", "content": SYSTEM_PROMPT})
        session.messages.append({"role": "user", "content": data_context})
        session.messages.append(
            {
                "role": "assistant",
                "content": "I've reviewed the market data. What would you like to know?",
            }
        )

    session.messages.append({"role": "user", "content": user_message})
    session.updated_at = time.monotonic()

    collected_tokens: list[str] = []

    async def _stream() -> AsyncIterator[str]:
        async for token in chat_stream(session.messages):
            collected_tokens.append(token)
            yield token
        full_response = "".join(collected_tokens)
        clean = full_response
        if "<think>" in clean:
            think_end = clean.find("</think>")
            if think_end != -1:
                clean = clean[think_end + len("</think>") :]
        session.messages.append({"role": "assistant", "content": clean.strip()})

    return session.session_id, _stream()
