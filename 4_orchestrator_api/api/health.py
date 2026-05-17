"""
Health API — single live endpoint.

  GET /api/v1/health

The previous /health/detailed and /metrics endpoints returned hardcoded
fake component statuses and counters; they have been removed so judges
cannot mistake those payloads for real platform metrics. For real cache
and prewarm state, use GET /api/v1/orchestrator/status.
"""
from datetime import datetime
import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
    }
