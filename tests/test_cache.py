from __future__ import annotations

import threading
import time

import pandas as pd
import pytest

from market_data.cache import InMemoryCache


def _make_df(close: float = 100.0) -> pd.DataFrame:
    return pd.DataFrame({"Close": [close]}, index=pd.DatetimeIndex(["2024-01-01"], name="Date"))


class TestInMemoryCache:
    def test_get_miss(self) -> None:
        cache = InMemoryCache()
        assert cache.get("nonexistent") is None

    def test_set_and_get(self) -> None:
        cache = InMemoryCache()
        df = _make_df()
        cache.set("key1", df)
        result = cache.get("key1")
        assert result is not None
        assert list(result["Close"]) == [100.0]

    def test_ttl_expiry(self) -> None:
        cache = InMemoryCache(ttl_seconds=0)
        df = _make_df()
        cache.set("key1", df)
        time.sleep(0.01)
        assert cache.get("key1") is None

    def test_delete(self) -> None:
        cache = InMemoryCache()
        cache.set("key1", _make_df())
        cache.delete("key1")
        assert cache.get("key1") is None

    def test_delete_nonexistent_key(self) -> None:
        cache = InMemoryCache()
        cache.delete("does_not_exist")

    def test_delete_prefix(self) -> None:
        cache = InMemoryCache()
        cache.set("AAPL:1d:x", _make_df(100.0))
        cache.set("AAPL:1h:x", _make_df(101.0))
        cache.set("GOOG:1d:x", _make_df(200.0))
        cache.delete_prefix("AAPL:")
        assert cache.get("AAPL:1d:x") is None
        assert cache.get("AAPL:1h:x") is None
        assert cache.get("GOOG:1d:x") is not None

    def test_clear(self) -> None:
        cache = InMemoryCache()
        cache.set("a", _make_df())
        cache.set("b", _make_df())
        cache.set("c", _make_df())
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None
        assert cache.get("c") is None

    def test_max_entries_eviction(self) -> None:
        cache = InMemoryCache(ttl_seconds=60, max_entries=2)
        cache.set("first", _make_df(1.0))
        time.sleep(0.001)
        cache.set("second", _make_df(2.0))
        time.sleep(0.001)
        cache.set("third", _make_df(3.0))
        assert cache.get("second") is not None
        assert cache.get("third") is not None
        assert cache.get("first") is None

    def test_overwrite_existing_key(self) -> None:
        cache = InMemoryCache()
        cache.set("key1", _make_df(100.0))
        cache.set("key1", _make_df(200.0))
        result = cache.get("key1")
        assert result is not None
        assert list(result["Close"]) == [200.0]

    def test_thread_safety(self) -> None:
        cache = InMemoryCache(ttl_seconds=60, max_entries=100)
        errors: list[Exception] = []

        def worker(n: int) -> None:
            try:
                for i in range(20):
                    key = f"key:{n}:{i}"
                    cache.set(key, _make_df(float(i)))
                    cache.get(key)
                    if i % 5 == 0:
                        cache.delete(key)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(n,)) for n in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
