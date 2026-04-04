from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from pydantic import BaseModel, field_validator

from market_data.config import DATA_DIR

WATCHLIST_PATH = DATA_DIR.parent / "watchlist.json"

_wl_lock = threading.Lock()


class Watchlist(BaseModel):
    tickers: list[str] = []

    @field_validator("tickers", mode="before")
    @classmethod
    def normalise(cls, v: list[str]) -> list[str]:
        return sorted(set(t.upper() for t in v))


def load_watchlist() -> Watchlist:
    with _wl_lock:
        path = WATCHLIST_PATH
        if not path.exists():
            return Watchlist()
        try:
            data = json.loads(path.read_text())
            return Watchlist.model_validate(data)
        except Exception:
            return Watchlist()


def save_watchlist(wl: Watchlist) -> None:
    with _wl_lock:
        path = WATCHLIST_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(wl.model_dump_json())
        os.replace(tmp, path)


def add_ticker(ticker: str) -> Watchlist:
    with _wl_lock:
        path = WATCHLIST_PATH
        if path.exists():
            try:
                data = json.loads(path.read_text())
                wl = Watchlist.model_validate(data)
            except Exception:
                wl = Watchlist()
        else:
            wl = Watchlist()
        tickers = set(wl.tickers)
        tickers.add(ticker.upper())
        new_wl = Watchlist(tickers=sorted(tickers))
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(new_wl.model_dump_json())
        os.replace(tmp, path)
        return new_wl


def remove_ticker(ticker: str) -> Watchlist:
    with _wl_lock:
        path = WATCHLIST_PATH
        if path.exists():
            try:
                data = json.loads(path.read_text())
                wl = Watchlist.model_validate(data)
            except Exception:
                wl = Watchlist()
        else:
            wl = Watchlist()
        tickers = set(wl.tickers)
        tickers.discard(ticker.upper())
        new_wl = Watchlist(tickers=sorted(tickers))
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(new_wl.model_dump_json())
        os.replace(tmp, path)
        return new_wl


def list_tickers() -> list[str]:
    with _wl_lock:
        path = WATCHLIST_PATH
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text())
            wl = Watchlist.model_validate(data)
            return wl.tickers
        except Exception:
            return []
