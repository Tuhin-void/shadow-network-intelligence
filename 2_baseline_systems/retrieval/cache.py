"""
LRU caching for embeddings and retrieval results.
"""
import hashlib
from collections import OrderedDict
from typing import Optional, Any


class RetrievalCache:
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.embedding_cache: OrderedDict[str, list[float]] = OrderedDict()
        self.retrieval_cache: OrderedDict[str, list[dict]] = OrderedDict()
        self.embedding_hits = 0
        self.retrieval_hits = 0
        self.embedding_misses = 0
        self.retrieval_misses = 0

    def _hash(self, text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()

    def get_embedding(self, text: str) -> Optional[list[float]]:
        key = self._hash(text)
        if key in self.embedding_cache:
            self.embedding_cache.move_to_end(key)
            self.embedding_hits += 1
            return self.embedding_cache[key]
        self.embedding_misses += 1
        return None

    def set_embedding(self, text: str, embedding: list[float]) -> None:
        key = self._hash(text)
        if key in self.embedding_cache:
            self.embedding_cache.move_to_end(key)
        else:
            if len(self.embedding_cache) >= self.max_size:
                self.embedding_cache.popitem(last=False)
            self.embedding_cache[key] = embedding

    def get_retrieval(self, query: str, top_k: int = 10) -> Optional[list[dict]]:
        key = f"{self._hash(query)}:{top_k}"
        if key in self.retrieval_cache:
            self.retrieval_cache.move_to_end(key)
            self.retrieval_hits += 1
            return self.retrieval_cache[key]
        self.retrieval_misses += 1
        return None

    def set_retrieval(self, query: str, top_k: int, results: list[dict]) -> None:
        key = f"{self._hash(query)}:{top_k}"
        if key in self.retrieval_cache:
            self.retrieval_cache.move_to_end(key)
        else:
            if len(self.retrieval_cache) >= self.max_size:
                self.retrieval_cache.popitem(last=False)
            self.retrieval_cache[key] = results

    def clear(self) -> None:
        self.embedding_cache.clear()
        self.retrieval_cache.clear()
        self.embedding_hits = 0
        self.retrieval_hits = 0
        self.embedding_misses = 0
        self.retrieval_misses = 0

    def get_stats(self) -> dict:
        emb_total = self.embedding_hits + self.embedding_misses
        ret_total = self.retrieval_hits + self.retrieval_misses
        return {
            "embedding_cache_size": len(self.embedding_cache),
            "retrieval_cache_size": len(self.retrieval_cache),
            "embedding_hit_rate": self.embedding_hits / emb_total if emb_total > 0 else 0,
            "retrieval_hit_rate": self.retrieval_hits / ret_total if ret_total > 0 else 0,
            "embedding_hits": self.embedding_hits,
            "embedding_misses": self.embedding_misses,
            "retrieval_hits": self.retrieval_hits,
            "retrieval_misses": self.retrieval_misses,
        }