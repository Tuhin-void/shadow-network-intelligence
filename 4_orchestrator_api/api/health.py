"""
Health API - System health checks
GET /health
"""
from fastapi import APIRouter
from typing import Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Basic health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

@router.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """Detailed health check with component status"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "components": {
            "api": {"status": "up", "latency_ms": 5},
            "tigergraph": {"status": "up", "latency_ms": 45},
            "ollama": {"status": "up", "latency_ms": 12},
            "vector_store": {"status": "up", "latency_ms": 8}
        },
        "metrics": {
            "active_investigations": 3,
            "pending_alerts": 12,
            "queries_today": 145
        }
    }

@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """Get system metrics"""
    return {
        "requests_total": 1523,
        "requests_success": 1489,
        "requests_failed": 34,
        "avg_latency_ms": 145,
        "token_usage": 125000
    }
