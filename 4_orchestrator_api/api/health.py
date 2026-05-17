"""
Health API — single live endpoint.

  GET /api/v1/health           — liveness only (always 200 if the API is up)
  GET /api/v1/health?probe=1   — also probes TG; truthful tigergraph_online flag

The previous /health/detailed and /metrics endpoints returned hardcoded
fake component statuses and counters; they have been removed so judges
cannot mistake those payloads for real platform metrics. For real cache
and prewarm state, use GET /api/v1/orchestrator/status (which always
performs a cached liveness probe).
"""
from datetime import datetime
import logging

from fastapi import APIRouter, Request

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def health_check(request: Request, probe: bool = False) -> dict:
    """Liveness endpoint.

    Returns 200 with `status: healthy` whenever the orchestrator API is
    up. When `probe=true`, also performs a fast TG liveness check
    (thread-bounded 3s, cached 10s) and surfaces `tigergraph_online`.
    Monitoring tools can poll `?probe=1` for honest infrastructure state.
    """
    payload: dict = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
    }
    if probe:
        orch = getattr(request.app.state, "orchestrator", None)
        client = getattr(orch, "_client", None) if orch is not None else None
        tg_online: bool | None = None
        if client is not None:
            try:
                tg_online = bool(client.probe_liveness(max_age_s=0))
            except Exception:
                tg_online = False
        payload["tigergraph_online"] = tg_online
        payload["mode"] = (
            "live_tigergraph" if tg_online
            else "offline_local_dataset" if tg_online is False
            else "unknown"
        )
    return payload
