"""Pluggable cache abstraction — in-memory now, Redis later (YAGNI)."""

from __future__ import annotations

import threading
import time
from typing import Any, Protocol


class CacheBackend(Protocol):
    """Cache protocol — implement get/set/delete/clear."""

    def get(self, key: str) -> Any | None:
        """Return cached value or None if miss/expired."""
        ...

    def set(self, key: str, value: Any) -> None:
        """Store a value in the cache."""
        ...

    def delete(self, key: str) -> None:
        """Remove a specific key (exact match)."""
        ...

    def delete_prefix(self, prefix: str) -> None:
        """Remove all keys starting with prefix."""
        ...

    def clear(self) -> None:
        """Remove all entries."""
        ...


class InMemoryCache:
    """Thread-safe in-memory cache with TTL and max-size eviction."""

    def __init__(self, ttl_seconds: int = 60, max_entries: int = 256) -> None:
        self._ttl = ttl_seconds
        self._max_entries = max_entries
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        """Return cached value or None if miss/expired."""
        with self._lock:
            if key not in self._store:
                return None
            ts, value = self._store[key]
            if time.monotonic() - ts >= self._ttl:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any) -> None:
        """Store a value in the cache; evict oldest entry if max_entries exceeded."""
        with self._lock:
            self._store[key] = (time.monotonic(), value)
            if len(self._store) > self._max_entries:
                # Evict oldest entry by timestamp
                oldest_key = min(self._store, key=lambda k: self._store[k][0])
                del self._store[oldest_key]

    def delete(self, key: str) -> None:
        """Remove a specific key (exact match)."""
        with self._lock:
            self._store.pop(key, None)

    def delete_prefix(self, prefix: str) -> None:
        """Remove all keys starting with prefix."""
        with self._lock:
            keys = [k for k in self._store if k.startswith(prefix)]
            for k in keys:
                del self._store[k]

    def clear(self) -> None:
        """Remove all entries."""
        with self._lock:
            self._store.clear()
