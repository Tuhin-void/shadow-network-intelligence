"""Caching module — caches retrieval results for repeated queries."""
import time
import hashlib
from typing import Optional, Any


class RetrievalCache:
    """
    Simple TTL cache for graph retrieval results.
    """

    def __init__(self, enabled: bool = True, default_ttl: int = 300):
        self.enabled = enabled
        self.default_ttl = default_ttl
        self._cache: dict[str, dict] = {}

    def _make_key(self, query: str, strategy: str, top_k: int, depth: int) -> str:
        raw = f"{query}:{strategy}:{top_k}:{depth}"
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, query: str, strategy: str = "auto", top_k: int = 10, depth: int = 2) -> Optional[Any]:
        if not self.enabled:
            return None

        key = self._make_key(query, strategy, top_k, depth)
        entry = self._cache.get(key)

        if entry is None:
            return None

        if time.time() > entry["expires_at"]:
            del self._cache[key]
            return None

        self._cache[key]["hits"] = entry.get("hits", 0) + 1
        return entry["value"]

    def set(
        self,
        query: str,
        value: Any,
        strategy: str = "auto",
        top_k: int = 10,
        depth: int = 2,
        ttl: Optional[int] = None,
    ) -> None:
        if not self.enabled:
            return

        key = self._make_key(query, strategy, top_k, depth)
        self._cache[key] = {
            "value": value,
            "created_at": time.time(),
            "expires_at": time.time() + (ttl or self.default_ttl),
            "hits": 0,
        }

    def clear(self) -> None:
        self._cache.clear()

    def stats(self) -> dict:
        total = len(self._cache)
        now = time.time()
        expired = sum(1 for e in self._cache.values() if e["expires_at"] < now)
        hits = sum(e.get("hits", 0) for e in self._cache.values())
        return {
            "total_entries": total,
            "expired_entries": expired,
            "total_hits": hits,
        }

    def invalidate_pattern(self, pattern: str) -> int:
        count = 0
        keys_to_delete = []
        for key in self._cache:
            if pattern in key:
                keys_to_delete.append(key)
        for key in keys_to_delete:
            del self._cache[key]
            count += 1
        return count