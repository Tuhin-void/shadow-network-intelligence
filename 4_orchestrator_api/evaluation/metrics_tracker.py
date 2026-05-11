"""
Shadow Network Intelligence - Metrics Tracker
Tracks system and benchmark metrics
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

@dataclass
class BenchmarkResult:
    approach: str
    query: str
    accuracy: float
    latency_ms: float
    token_count: int
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)

@dataclass
class SystemMetrics:
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    active_investigations: int
    alerts_generated: int
    api_latency_p99: float

class MetricsTracker:
    """
    Tracks system performance and benchmark metrics.
    """
    
    def __init__(self, storage_path: str = "metrics"):
        self.storage_path = storage_path
        self.benchmark_results: List[BenchmarkResult] = []
        self.system_metrics: List[SystemMetrics] = []
    
    def record_benchmark(
        self,
        approach: str,
        query: str,
        accuracy: float,
        latency_ms: float,
        token_count: int,
        metadata: Dict = None
    ) -> BenchmarkResult:
        """Record a benchmark result"""
        result = BenchmarkResult(
            approach=approach,
            query=query,
            accuracy=accuracy,
            latency_ms=latency_ms,
            token_count=token_count,
            metadata=metadata or {}
        )
        self.benchmark_results.append(result)
        logger.info(f"Benchmark recorded: {approach} ({accuracy:.2%} accuracy)")
        return result
    
    def record_system_metrics(self, metrics: SystemMetrics):
        """Record system metrics snapshot"""
        self.system_metrics.append(metrics)
    
    def get_benchmark_summary(self) -> Dict[str, Any]:
        """Get summary of benchmark results"""
        if not self.benchmark_results:
            return {"error": "No benchmark results"}
        
        by_approach = {}
        for result in self.benchmark_results:
            if result.approach not in by_approach:
                by_approach[result.approach] = {
                    "count": 0,
                    "total_accuracy": 0.0,
                    "total_latency": 0.0,
                    "total_tokens": 0
                }
            
            by_approach[result.approach]["count"] += 1
            by_approach[result.approach]["total_accuracy"] += result.accuracy
            by_approach[result.approach]["total_latency"] += result.latency_ms
            by_approach[result.approach]["total_tokens"] += result.token_count
        
        summary = {}
        for approach, stats in by_approach.items():
            count = stats["count"]
            summary[approach] = {
                "avg_accuracy": stats["total_accuracy"] / count,
                "avg_latency_ms": stats["total_latency"] / count,
                "total_tokens": stats["total_tokens"],
                "runs": count
            }
        
        return {
            "total_runs": len(self.benchmark_results),
            "date_range": {
                "start": min(r.timestamp for r in self.benchmark_results).isoformat(),
                "end": max(r.timestamp for r in self.benchmark_results).isoformat()
            },
            "by_approach": summary
        }
    
    def compare_approaches(self) -> Dict[str, Any]:
        """Compare all approaches"""
        summary = self.get_benchmark_summary()
        
        if "error" in summary:
            return summary
        
        approaches = list(summary["by_approach"].keys())
        
        best_accuracy = max(
            approaches,
            key=lambda a: summary["by_approach"][a]["avg_accuracy"]
        )
        fastest = min(
            approaches,
            key=lambda a: summary["by_approach"][a]["avg_latency_ms"]
        )
        most_efficient = min(
            approaches,
            key=lambda a: summary["by_approach"][a]["total_tokens"]
        )
        
        return {
            "winner_accuracy": best_accuracy,
            "winner_latency": fastest,
            "winner_efficiency": most_efficient,
            "recommendation": self._get_recommendation(summary)
        }
    
    def _get_recommendation(self, summary: Dict) -> str:
        """Get recommendation based on results"""
        graphrag_accuracy = summary["by_approach"].get("graphrag", {}).get("avg_accuracy", 0)
        
        if graphrag_accuracy >= 0.85:
            return "GraphRAG recommended for accuracy-critical queries"
        elif graphrag_accuracy >= 0.70:
            return "GraphRAG provides good accuracy with reasonable latency"
        else:
            return "Consider combining approaches for best results"
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get current system health"""
        if not self.system_metrics:
            return {"status": "unknown", "message": "No metrics available"}
        
        latest = self.system_metrics[-1]
        
        return {
            "status": "healthy" if latest.cpu_usage < 90 else "degraded",
            "cpu_usage": latest.cpu_usage,
            "memory_usage": latest.memory_usage,
            "active_investigations": latest.active_investigations,
            "p99_latency_ms": latest.api_latency_p99,
            "timestamp": latest.timestamp.isoformat()
        }