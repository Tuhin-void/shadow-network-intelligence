"""
Result cache for completed investigation reports.

Wraps `GraphRAGEngine.query` results at the orchestrator level so that
identical (query, top_k, depth, strategy) tuples return immediately on
repeat. This is the most impactful latency optimization for the demo
flow: presets are stable, so the second invocation of any preset
returns in < 50ms after the first.

Design constraints:
  • Pure-Python, no extra dependencies.
  • Bounded by entry count AND TTL — prevents unbounded growth.
  • Toggleable via env var SNI_RESULT_CACHE_ENABLED (default on).
  • Thread-safe for FastAPI's threaded request handling.
  • Does NOT alter retrieval surface — returned dict is the original
    engine result, so downstream report building is unchanged.

Cache key is the SHA1 of the canonical-form tuple — never the raw query
text (so memory stays bounded regardless of query length).
"""
from __future__ import annotations

import hashlib
import os
import threading
import time
from collections import OrderedDict
from typing import Any, Callable, Optional


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


class ResultCache:
    """Bounded LRU + TTL cache for engine query results."""

    def __init__(
        self,
        *,
        max_entries: Optional[int] = None,
        ttl_seconds: Optional[int] = None,
        enabled: Optional[bool] = None,
    ) -> None:
        self.max_entries = max_entries if max_entries is not None else _env_int(
            "SNI_RESULT_CACHE_SIZE", 64)
        self.ttl_seconds = ttl_seconds if ttl_seconds is not None else _env_int(
            "SNI_RESULT_CACHE_TTL", 300)
        self.enabled = enabled if enabled is not None else _env_bool(
            "SNI_RESULT_CACHE_ENABLED", True)
        self._store: OrderedDict[str, tuple[float, dict[str, Any]]] = OrderedDict()
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    # ── Internal helpers ────────────────────────────────────────────────

    @staticmethod
    def _make_key(query: str, top_k: int, depth: int, strategy: str) -> str:
        canonical = f"{(query or '').strip().lower()}|{top_k}|{depth}|{strategy or ''}"
        return hashlib.sha1(canonical.encode("utf-8"), usedforsecurity=False).hexdigest()

    def _evict_expired_locked(self) -> None:
        now = time.time()
        expired = [k for k, (ts, _) in self._store.items()
                   if now - ts > self.ttl_seconds]
        for k in expired:
            self._store.pop(k, None)
            self._evictions += 1

    # ── Public API ──────────────────────────────────────────────────────

    def get_or_compute(
        self,
        *,
        query: str,
        top_k: int,
        depth: int,
        strategy: str,
        compute: Callable[[], dict[str, Any]],
    ) -> tuple[dict[str, Any], bool]:
        """
        Return (result, cache_hit). `compute` is called only on miss.
        """
        if not self.enabled:
            return compute(), False

        key = self._make_key(query, top_k, depth, strategy)

        with self._lock:
            self._evict_expired_locked()
            entry = self._store.get(key)
            if entry is not None:
                ts, result = entry
                # Refresh LRU ordering.
                self._store.move_to_end(key)
                self._hits += 1
                # Return a shallow copy so downstream mutation doesn't poison
                # the cache entry.
                return dict(result), True

        # Cache miss: compute outside the lock so we don't block hits.
        result = compute()

        with self._lock:
            self._store[key] = (time.time(), result)
            self._store.move_to_end(key)
            self._misses += 1
            while len(self._store) > self.max_entries:
                self._store.popitem(last=False)
                self._evictions += 1

        return result, False

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "enabled":     self.enabled,
                "entries":     len(self._store),
                "max_entries": self.max_entries,
                "ttl_seconds": self.ttl_seconds,
                "hits":        self._hits,
                "misses":      self._misses,
                "evictions":   self._evictions,
                "hit_rate":    (self._hits / (self._hits + self._misses))
                               if (self._hits + self._misses) else 0.0,
            }

    def clear(self) -> int:
        with self._lock:
            n = len(self._store)
            self._store.clear()
            return n
