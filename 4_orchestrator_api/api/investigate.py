"""
Investigate API — production endpoints over the InvestigationOrchestrator.

  POST /investigate         — synchronous investigation, returns the report
  POST /investigate/stream  — Server-Sent Events stream of investigation events
  POST /sessions            — open a new investigation session
  GET  /sessions            — list sessions
  GET  /sessions/{id}       — session detail (incl. recent reports)
  DELETE /sessions/{id}     — close a session
  GET  /orchestrator/status — health / cache / prewarm status

The orchestrator is held in app.state.orchestrator (set in main.py lifespan).
"""
import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Request contracts ─────────────────────────────────────────────────────

class InvestigationRequest(BaseModel):
    query: str = Field(..., description="Natural-language investigation question")
    session_id: Optional[str] = None
    top_k: int = 5
    depth: int = 2
    strategy: str = "auto"


class SessionCreateRequest(BaseModel):
    title: Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.post("/investigate")
def investigate(request: Request, body: InvestigationRequest):
    """
    Run a synchronous investigation. Returns the structured report.

    For live-unfolding intelligence (recommended for the cinematic UI),
    use POST /investigate/stream instead.
    """
    orch = _get_orch(request)
    report = orch.investigate(
        query=body.query, session_id=body.session_id,
        top_k=body.top_k, depth=body.depth, strategy=body.strategy,
    )
    return report


@router.post("/investigate/stream")
def investigate_stream(request: Request, body: InvestigationRequest):
    """
    Stream investigation events via Server-Sent Events. Each event is
    JSON-encoded in a `data:` line; consumers may use EventSource on
    the browser side.
    """
    orch = _get_orch(request)

    def _sse_gen():
        try:
            for ev in orch.investigate_stream(
                query=body.query, session_id=body.session_id,
                top_k=body.top_k, depth=body.depth, strategy=body.strategy,
            ):
                payload = json.dumps(ev.to_dict(), default=_json_default)
                yield f"event: {ev.kind}\ndata: {payload}\n\n"
            yield "event: stream.end\ndata: {}\n\n"
        except Exception as e:
            err = json.dumps({"error": str(e), "type": type(e).__name__})
            yield f"event: error\ndata: {err}\n\n"

    return StreamingResponse(
        _sse_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/sessions")
def create_session(request: Request, body: SessionCreateRequest):
    orch = _get_orch(request)
    sess = orch.open_session(title=body.title or "")
    return sess.to_summary()


@router.get("/sessions")
def list_sessions(request: Request):
    orch = _get_orch(request)
    return {"sessions": orch.list_sessions()}


@router.get("/sessions/{session_id}")
def get_session(request: Request, session_id: str):
    orch = _get_orch(request)
    sess = orch.get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="session not found")
    return {**sess.to_summary(), "reports": sess.reports}


@router.delete("/sessions/{session_id}")
def delete_session(request: Request, session_id: str):
    orch = _get_orch(request)
    ok = orch.close_session(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="session not found")
    return {"ok": True}


@router.get("/orchestrator/status")
def orchestrator_status(request: Request):
    return _get_orch(request).status()


# ── Helpers ───────────────────────────────────────────────────────────────

def _get_orch(request: Request):
    orch = getattr(request.app.state, "orchestrator", None)
    if orch is None:
        raise HTTPException(
            status_code=503,
            detail="Orchestrator not initialized. Check server startup logs.",
        )
    return orch


def _json_default(obj):
    """Handle dataclass / set serialization for SSE payloads."""
    if isinstance(obj, set):
        return sorted(obj)
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    return str(obj)
