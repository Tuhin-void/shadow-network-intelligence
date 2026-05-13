"""Metrics module — tracks retrieval and GraphRAG performance."""
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RetrievalMetrics:
    entity_count: int = 0
    neighbor_count: int = 0
    edge_count: int = 0
    path_count: int = 0
    community_count: int = 0
    retrieval_time_ms: float = 0.0
    compression_time_ms: float = 0.0
    total_time_ms: float = 0.0
    strategy: str = "unknown"
    compression_type: str = "unknown"
    token_count: int = 0

    def __repr__(self) -> str:
        return (f"RetrievalMetrics(entity={self.entity_count}, neighbors={self.neighbor_count}, "
                f"time={self.total_time_ms:.1f}ms, strategy={self.strategy})")


class MetricsCollector:
    """
    Collects and aggregates metrics for graph retrieval operations.
    """

    def __init__(self):
        self.history: list[RetrievalMetrics] = []
        self.current: Optional[RetrievalMetrics] = None

    def start_retrieval(self, strategy: str = "unknown") -> None:
        self.current = RetrievalMetrics(strategy=strategy, total_time_ms=0)
        self.current._start_time = time.time()

    def end_retrieval(self) -> None:
        if self.current:
            self.current.retrieval_time_ms = (time.time() - self.current._start_time) * 1000

    def end_compression(self) -> None:
        if self.current:
            self.current.compression_time_ms = (time.time() - self.current._start_time -
                                                 self.current.retrieval_time_ms) * 1000

    def record_result(self, metadata: dict, answer: str = "") -> RetrievalMetrics:
        if self.current:
            self.current.entity_count = metadata.get("entity_count", 0)
            self.current.neighbor_count = metadata.get("neighbor_count", 0)
            self.current.total_time_ms = (time.time() - self.current._start_time) * 1000
            self.current.compression_type = metadata.get("compression", "unknown")
            self.current.token_count = len(answer) // 4
            self.history.append(self.current)
            self.current = None
        return RetrievalMetrics()

    def aggregate(self) -> dict:
        if not self.history:
            return {}
        total = len(self.history)
        return {
            "total_queries": total,
            "avg_time_ms": sum(m.total_time_ms for m in self.history) / total,
            "avg_entities": sum(m.entity_count for m in self.history) / total,
            "avg_neighbors": sum(m.neighbor_count for m in self.history) / total,
            "strategy_breakdown": self._strategy_breakdown(),
        }

    def _strategy_breakdown(self) -> dict:
        breakdown = {}
        for m in self.history:
            s = m.strategy
            if s not in breakdown:
                breakdown[s] = {"count": 0, "avg_time": 0.0, "total_time": 0.0}
            breakdown[s]["count"] += 1
            breakdown[s]["total_time"] += m.total_time_ms

        for s in breakdown:
            breakdown[s]["avg_time"] = breakdown[s]["total_time"] / breakdown[s]["count"]
        return breakdown