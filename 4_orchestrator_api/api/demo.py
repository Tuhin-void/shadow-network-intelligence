"""
Demo API — preset investigations curated for live demonstrations.

  GET  /demo/presets               — list available presets
  POST /demo/run/{preset_key}      — synchronous preset investigation
  POST /demo/stream/{preset_key}   — SSE stream of preset investigation
"""
import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Local imports: orchestration.presets is the source of truth for demo content.
from orchestration.presets import list_presets, get_preset

logger = logging.getLogger(__name__)
router = APIRouter()


class DemoRunRequest(BaseModel):
    session_id: Optional[str] = None


@router.get("/demo/presets")
def get_presets():
    return {"presets": list_presets()}


@router.post("/demo/run/{preset_key}")
def run_preset(request: Request, preset_key: str, body: Optional[DemoRunRequest] = None):
    """Synchronous preset investigation. Returns the structured report."""
    preset = get_preset(preset_key)
    if not preset:
        raise HTTPException(status_code=404, detail=f"preset '{preset_key}' not found")
    orch = _get_orch(request)
    report = orch.investigate(
        query=preset["query"],
        session_id=(body.session_id if body else None),
        top_k=preset["top_k"],
        depth=preset["depth"],
    )
    return {
        "preset_key": preset_key,
        "preset": {k: v for k, v in preset.items() if k != "query"},
        "query": preset["query"],
        "report": report,
    }


@router.post("/demo/stream/{preset_key}")
def stream_preset(request: Request, preset_key: str, body: Optional[DemoRunRequest] = None):
    """Stream a preset investigation as SSE — same as /investigate/stream
    but with a curated query. Use this for the cinematic demo flow."""
    preset = get_preset(preset_key)
    if not preset:
        raise HTTPException(status_code=404, detail=f"preset '{preset_key}' not found")
    orch = _get_orch(request)

    def _sse_gen():
        try:
            for ev in orch.investigate_stream(
                query=preset["query"],
                session_id=(body.session_id if body else None),
                top_k=preset["top_k"],
                depth=preset["depth"],
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
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _get_orch(request: Request):
    orch = getattr(request.app.state, "orchestrator", None)
    if orch is None:
        raise HTTPException(
            status_code=503,
            detail="Orchestrator not initialized.",
        )
    return orch


def _json_default(obj):
    if isinstance(obj, set):
        return sorted(obj)
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    return str(obj)
