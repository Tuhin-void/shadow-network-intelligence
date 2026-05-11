"""Metrics calculation utilities"""
from typing import Dict, List, Any

class MetricsCalculator:
    """Calculate performance metrics."""
    
    @staticmethod
    def calculate_latency_stats(latencies: List[float]) -> Dict[str, float]:
        """Calculate latency statistics."""
        if not latencies:
            return {"avg": 0, "p50": 0, "p95": 0, "p99": 0}
        
        sorted_latencies = sorted(latencies)
        return {
            "avg": sum(sorted_latencies) / len(sorted_latencies),
            "p50": sorted_latencies[int(len(sorted_latencies) * 0.5)],
            "p95": sorted_latencies[int(len(sorted_latencies) * 0.95)],
            "p99": sorted_latencies[int(len(sorted_latencies) * 0.99)] if len(sorted_latencies) > 1 else sorted_latencies[-1]
        }
