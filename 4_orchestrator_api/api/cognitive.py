"""
Cognitive API — orchestrator-side composition of:
  • 5_agent_swarm   (5 professional analysis agents)
  • 6_reasoning_engine (claims, contradictions, structural confidence)

Endpoints:
  POST /investigate/deep           — synchronous deep investigation (returns combined report)
  POST /investigate/deep/stream    — SSE stream of investigation + agent + reasoning events
  POST /demo/deep/{preset_key}     — preset variant of /investigate/deep

The cognitive layer is initialized lazily once per process and reuses the
orchestrator's GraphRAGEngine — no second engine, no duplicate retrieval.
Result-cache hits propagate, so a deep run on a warm cache returns in
~hundreds of ms instead of seconds.
"""
from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
# Both 5_agent_swarm and 6_reasoning_engine define a top-level `orchestration`
# directory in their own trees that would conflict with the API's package.
# We need the swarm/synthesis modules but NOT their orchestration subpkgs.
for p in (_PROJECT_ROOT / "5_agent_swarm", _PROJECT_ROOT / "6_reasoning_engine"):
    sp = str(p)
    if sp not in sys.path:
        sys.path.append(sp)   # append (not insert) so the API's own
                              # `orchestration` package keeps priority.

logger = logging.getLogger(__name__)
router = APIRouter()


class DeepInvestigationRequest(BaseModel):
    query: str = Field(..., description="Natural-language investigation question")
    session_id: Optional[str] = None
    top_k: int = 5
    depth: int = 2
    strategy: str = "auto"


class DemoDeepRequest(BaseModel):
    session_id: Optional[str] = None


# Process-local cognitive singletons. Built lazily on first call so the
# orchestrator's existing lifespan is unaffected.
_cognitive_state: dict = {"coord": None, "synth": None}


def _get_cognitive(request: Request):
    """Build (or reuse) the swarm coordinator backed by the orchestrator engine."""
    if _cognitive_state["coord"] is not None:
        return _cognitive_state["coord"], _cognitive_state["synth"]

    orch = getattr(request.app.state, "orchestrator", None)
    if orch is None:
        raise HTTPException(status_code=503, detail="orchestrator not initialized")

    # Late imports so module load doesn't drag swarm/reasoning into every route.
    from swarm import SynthesisCoordinator
    import synthesis as synth_module

    # Reuse the orchestrator's already-warmed engine.
    coord = SynthesisCoordinator(engine=orch._engine)
    _cognitive_state["coord"] = coord
    _cognitive_state["synth"] = synth_module
    return coord, synth_module


def _build_deep_report(orch, coord, synth_module, *, query: str,
                       session_id: Optional[str], top_k: int, depth: int,
                       strategy: str) -> dict:
    """
    Run the orchestrator investigation (cache-aware), then run the swarm + reasoning
    on the same engine_result so no second retrieval is performed.
    """
    t0 = time.perf_counter()

    # 1. Investigation report (cache-aware, builds session).
    inv_report = orch.investigate(
        query=query, session_id=session_id,
        top_k=top_k, depth=depth, strategy=strategy,
    )

    # 2. Re-pull engine_result from the cache so swarm/reasoning operate on
    #    the exact same retrieval surface (no duplicate cost).
    engine_result, cache_hit = orch._result_cache.get_or_compute(
        query=query, top_k=top_k, depth=depth, strategy=strategy,
        compute=lambda: orch._engine.query(
            query=query,
            config={"strategy": strategy, "top_k": top_k, "depth": depth},
        ),
    )

    # 3. Swarm.
    swarm_report = coord.run(query, top_k=top_k, depth=depth, strategy=strategy)

    # 4. Reasoning synthesis.
    syn = synth_module.synthesize(swarm_report, engine_result, query=query)

    elapsed_ms = (time.perf_counter() - t0) * 1000

    return {
        "query": query,
        "elapsed_ms": elapsed_ms,
        "investigation": inv_report,
        "swarm": swarm_report.to_dict(),
        "reasoning": syn.to_dict(),
        "metadata": {
            "investigation_cache_hit": bool(inv_report.get("structural_signals", {}).get("strategy", False)) and False,
            "engine_cache_hit": bool(cache_hit),
            "agent_count": len(swarm_report.agents),
            "claim_count": len(syn.key_claims),
            "contradiction_count": len(syn.contradictions),
            "overall_confidence": syn.overall_confidence,
        },
    }


# ── Endpoints ─────────────────────────────────────────────────────────────


@router.post("/investigate/deep")
def investigate_deep(request: Request, body: DeepInvestigationRequest):
    """
    Synchronous deep investigation: orchestrator + agent swarm + reasoning.

    Returns the combined structured report. Use this when the cinematic
    streaming flow is not needed (e.g., headless CLI clients, reports).

    Requires an activated environment — returns 409 with operational hint
    when activation.kind == "empty".
    """
    from orchestration.activation_gate import require_activation
    require_activation(operation="deep_investigation")
    orch = getattr(request.app.state, "orchestrator", None)
    if orch is None:
        raise HTTPException(status_code=503, detail="orchestrator not initialized")
    coord, synth_module = _get_cognitive(request)
    return _build_deep_report(
        orch, coord, synth_module,
        query=body.query, session_id=body.session_id,
        top_k=body.top_k, depth=body.depth, strategy=body.strategy,
    )


@router.post("/investigate/deep/stream")
def investigate_deep_stream(request: Request, body: DeepInvestigationRequest):
    """
    Streamed deep investigation. Yields:
      • original SSE event stream from the orchestrator
      • one `agent.finished` event per swarm agent
      • one `reasoning.synthesized` event with claims + confidence
      • final `deep_report.finalized` event with the combined report

    Requires an activated environment (see /investigate/deep).
    """
    from orchestration.activation_gate import require_activation
    require_activation(operation="deep_investigation_stream")
    orch = getattr(request.app.state, "orchestrator", None)
    if orch is None:
        raise HTTPException(status_code=503, detail="orchestrator not initialized")
    coord, synth_module = _get_cognitive(request)

    def _gen():
        try:
            seq = 0

            # Phase 1: stream the orchestrator events.
            engine_result_holder: dict = {}
            for ev in orch.investigate_stream(
                query=body.query, session_id=body.session_id,
                top_k=body.top_k, depth=body.depth, strategy=body.strategy,
            ):
                seq += 1
                # Capture the final report payload so swarm/reasoning can reuse it.
                if ev.kind == "report.finalized":
                    engine_result_holder["report"] = ev.payload
                yield f"event: {ev.kind}\ndata: {json.dumps(ev.to_dict(), default=str)}\n\n"

            # Phase 2: get engine_result via cache (warm now).
            engine_result, _ = orch._result_cache.get_or_compute(
                query=body.query, top_k=body.top_k, depth=body.depth,
                strategy=body.strategy,
                compute=lambda: orch._engine.query(
                    query=body.query,
                    config={"strategy": body.strategy, "top_k": body.top_k, "depth": body.depth},
                ),
            )

            # Phase 3: swarm — emit per-agent events as we run them.
            from swarm import (RetrievalAnalyst, GraphTopologyInvestigator,
                               SanctionsExposureTracer, FraudRingAnalyst)
            agents = [
                RetrievalAnalyst(),
                GraphTopologyInvestigator(),
                SanctionsExposureTracer(),
                FraudRingAnalyst(),
            ]
            findings = []
            for a in agents:
                f = a.analyze(engine_result)
                findings.append(f)
                seq += 1
                yield (f"event: agent.finished\n"
                       f"data: {json.dumps({'kind':'agent.finished','seq':seq,'payload':f.to_dict()}, default=str)}\n\n")

            # Phase 4: reasoning synthesis.
            from swarm import SwarmReport
            sr = SwarmReport(
                query=body.query, investigation_id=f"DEEP-{int(time.time()*1000)}",
                elapsed_ms=0, agents=findings,
                coordinator_summary="streamed deep investigation",
                consolidated_metrics={},
            )
            syn = synth_module.synthesize(sr, engine_result, query=body.query)
            seq += 1
            yield (f"event: reasoning.synthesized\n"
                   f"data: {json.dumps({'kind':'reasoning.synthesized','seq':seq,'payload':syn.to_dict()}, default=str)}\n\n")

            # Phase 5: final deep report.
            seq += 1
            deep = {
                "query": body.query,
                "investigation": engine_result_holder.get("report"),
                "swarm": sr.to_dict(),
                "reasoning": syn.to_dict(),
            }
            # Attach deep report to the archived investigation so the
            # Recent Investigations panel can replay the full cognitive
            # layer instead of just the shallow report.
            try:
                inv_id = (engine_result_holder.get("report") or {}).get("investigation_id")
                if inv_id:
                    from orchestration.archive import get_archive
                    get_archive().attach_deep_report(inv_id, deep)
            except Exception:
                pass
            yield (f"event: deep_report.finalized\n"
                   f"data: {json.dumps({'kind':'deep_report.finalized','seq':seq,'payload':deep}, default=str)}\n\n")

            yield "event: stream.end\ndata: {}\n\n"
        except Exception as e:
            logger.exception("deep stream failure")
            err = json.dumps({"error": str(e), "type": type(e).__name__})
            yield f"event: error\ndata: {err}\n\n"

    return StreamingResponse(
        _gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/demo/deep/{preset_key}")
def demo_deep(request: Request, preset_key: str,
              body: Optional[DemoDeepRequest] = None):
    """Synchronous deep investigation for a curated preset.

    Requires an activated environment (see /investigate/deep).
    """
    from orchestration.activation_gate import require_activation
    from orchestration.presets import get_preset
    require_activation(operation=f"demo_preset:{preset_key}")
    preset = get_preset(preset_key)
    if not preset:
        raise HTTPException(status_code=404, detail=f"preset '{preset_key}' not found")

    orch = getattr(request.app.state, "orchestrator", None)
    if orch is None:
        raise HTTPException(status_code=503, detail="orchestrator not initialized")
    coord, synth_module = _get_cognitive(request)
    deep = _build_deep_report(
        orch, coord, synth_module,
        query=preset["query"],
        session_id=(body.session_id if body else None),
        top_k=preset["top_k"], depth=preset["depth"], strategy="auto",
    )
    return {"preset_key": preset_key,
            "preset": {k: v for k, v in preset.items() if k != "query"},
            **deep}
