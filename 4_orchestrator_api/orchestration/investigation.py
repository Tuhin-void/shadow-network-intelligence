"""
InvestigationOrchestrator — the thin layer that coordinates existing
intelligence systems for an investigation lifecycle.

Pipeline:
  1. session open (or reuse)
  2. ensure GraphRAGEngine + caches warmed
  3. run engine.query(...)  ← all retrieval lives in 3_graph_intelligence_core
  4. project result into a structured InvestigationReport
  5. emit a stream of events for the cinematic UI to consume
  6. record the report into the session

This module DOES NOT:
  - duplicate retrieval logic
  - move GraphRAG into the API layer
  - manage agents
"""
from __future__ import annotations

import sys
import time
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Optional

# Make 3_graph_intelligence_core importable.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_CORE = _PROJECT_ROOT / "3_graph_intelligence_core"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from .events import (
    InvestigationEvent,
    EVENT_SESSION_STARTED, EVENT_QUERY_RECEIVED, EVENT_PREWARM_DONE,
    EVENT_ENTITY_FOUND, EVENT_NEIGHBORHOOD_DONE, EVENT_RING_DISCOVERED,
    EVENT_HIDDEN_RELATION, EVENT_TRAVERSAL_PATH, EVENT_RING_MEMBER_PROMO,
    EVENT_EVIDENCE_COLLECTED, EVENT_REPORT_FINALIZED, EVENT_ERROR,
)
from .session import SessionStore, InvestigationSession
from .report import build_report
from .result_cache import ResultCache


class InvestigationOrchestrator:
    """
    Thin orchestration over GraphRAGEngine. Initializes the engine ONCE and
    reuses it across all investigations (caches are process-scoped). Optionally
    prewarms on first init.
    """

    def __init__(self, prewarm_on_init: bool = True, prewarm_top_n: int = 30,
                 preset_prewarm: bool = False) -> None:
        from clients.graph_client import GraphClient
        from configs.config import load_config
        from graph_rag.graphrag_engine import GraphRAGEngine

        self._config = load_config(None)
        self._client = GraphClient(self._config)
        self._engine = GraphRAGEngine(self._client, self._config, compression="rule_based")
        self._sessions = SessionStore()
        self._is_offline = self._client._offline_mode
        # Result cache (LRU + TTL). Memoizes identical engine.query calls so
        # the second invocation of a stable preset returns in <50ms.
        self._result_cache = ResultCache()

        self._prewarm_stats: dict = {}
        if prewarm_on_init and not self._is_offline:
            try:
                self._prewarm_stats = self._engine.prewarm(top_n=prewarm_top_n)
            except Exception as e:
                self._prewarm_stats = {"warmed": 0, "error": str(e)}

        self._preset_prewarm_stats: dict = {}
        if preset_prewarm and not self._is_offline:
            self._preset_prewarm_stats = self._prewarm_presets()

    def _prewarm_presets(self) -> dict:
        """
        Run every curated demo preset once at boot to warm the result cache.
        Subsequent clicks on the same preset return in <50ms.

        Each preset run is wrapped in try/except so a single bad preset
        doesn't break boot.
        """
        from .presets import DEMO_PRESETS
        t0 = time.time()
        succeeded: list[str] = []
        failed: list[dict] = []
        for p in DEMO_PRESETS:
            try:
                _ = self._engine.query(
                    query=p["query"],
                    config={"strategy": "auto", "top_k": p["top_k"], "depth": p["depth"]},
                )
                # Insert directly into the cache so subsequent calls hit it.
                self._result_cache.get_or_compute(
                    query=p["query"], top_k=p["top_k"], depth=p["depth"],
                    strategy="auto",
                    compute=lambda r=_: r,
                )
                succeeded.append(p["key"])
            except Exception as e:
                failed.append({"key": p["key"], "error": str(e)[:120]})
        return {
            "warmed_presets": succeeded,
            "failed": failed,
            "elapsed_s": round(time.time() - t0, 2),
        }

    # ── Session management ────────────────────────────────────────────────

    def open_session(self, title: str = "") -> InvestigationSession:
        return self._sessions.open(title=title)

    def get_session(self, session_id: str) -> Optional[InvestigationSession]:
        return self._sessions.get(session_id)

    def list_sessions(self) -> list[dict]:
        return self._sessions.list()

    def close_session(self, session_id: str) -> bool:
        return self._sessions.delete(session_id)

    # ── Investigation execution ───────────────────────────────────────────

    def investigate(
        self,
        query: str,
        session_id: Optional[str] = None,
        top_k: int = 5,
        depth: int = 2,
        strategy: str = "auto",
    ) -> dict:
        """Synchronous investigation. Returns a structured report dict."""
        events = list(self._investigate_stream(
            query, session_id=session_id, top_k=top_k, depth=depth, strategy=strategy,
        ))
        finalize = next((e for e in reversed(events)
                         if e.kind == EVENT_REPORT_FINALIZED), None)
        return finalize.payload if finalize else {"error": "no report produced"}

    def investigate_stream(
        self,
        query: str,
        session_id: Optional[str] = None,
        top_k: int = 5,
        depth: int = 2,
        strategy: str = "auto",
    ) -> Iterator[InvestigationEvent]:
        """Streaming investigation. Yields events in order; suitable for SSE."""
        return self._investigate_stream(
            query, session_id=session_id, top_k=top_k, depth=depth, strategy=strategy,
        )

    # ── Internal ──────────────────────────────────────────────────────────

    def _investigate_stream(
        self,
        query: str,
        session_id: Optional[str],
        top_k: int,
        depth: int,
        strategy: str,
    ) -> Iterator[InvestigationEvent]:
        # 1. Resolve or open a session.
        if session_id and self._sessions.get(session_id):
            session = self._sessions.get(session_id)  # type: ignore[assignment]
        else:
            session = self._sessions.open(title=query[:60])

        inv_id = f"Q-{uuid.uuid4().hex[:8]}"
        seq = 0

        def emit(kind: str, payload: dict[str, Any]) -> InvestigationEvent:
            nonlocal seq
            seq += 1
            return InvestigationEvent(
                kind=kind, payload=payload, session_id=session.id, seq=seq,
            )

        yield emit(EVENT_SESSION_STARTED, {
            "session": session.to_summary(),
            "investigation_id": inv_id,
            "offline_mode": self._is_offline,
            "prewarm": self._prewarm_stats,
        })
        yield emit(EVENT_QUERY_RECEIVED, {"query": query, "top_k": top_k, "depth": depth})

        if self._prewarm_stats and self._prewarm_stats.get("warmed", 0) > 0:
            yield emit(EVENT_PREWARM_DONE, self._prewarm_stats)

        # 2. Run the underlying engine (this is where ALL retrieval happens).
        #    Result cache short-circuits identical (query, top_k, depth, strategy).
        t0 = time.perf_counter()
        try:
            engine_result, cache_hit = self._result_cache.get_or_compute(
                query=query, top_k=top_k, depth=depth, strategy=strategy,
                compute=lambda: self._engine.query(
                    query=query,
                    config={"strategy": strategy, "top_k": top_k, "depth": depth},
                ),
            )
        except Exception as e:
            yield emit(EVENT_ERROR, {"error": str(e), "type": type(e).__name__})
            return
        elapsed_ms = (time.perf_counter() - t0) * 1000
        # Annotate the result so downstream consumers can see cache provenance.
        md = engine_result.setdefault("metadata", {})
        md["cache_hit"] = bool(cache_hit)

        # 3. Emit fine-grained discovery events from the engine result.
        for ent in engine_result.get("entities", [])[:8]:
            yield emit(EVENT_ENTITY_FOUND, {
                "v_id": ent.get("v_id"),
                "type": ent.get("type"),
                "name": ent.get("name"),
                "risk_score": ent.get("risk_score"),
                "ring_touch_count": ent.get("ring_touch_count"),
                "fraud_degree": ent.get("fraud_degree"),
                "rerank_reason": ent.get("rerank_reason"),
                "promoted_from_ring": ent.get("rerank_reason", "").startswith("member of ring"),
            })

        # Counts of discovered ring connections / hidden rels / paths.
        context = engine_result.get("context", []) or []
        ring_count = sum(1 for n in context if "_RING" in n.get("edge", "")
                         or "_MEMBER_OF_RING" in n.get("edge", ""))
        if ring_count:
            yield emit(EVENT_RING_DISCOVERED, {
                "edge_count": ring_count,
                "via": list({n.get("via", "") for n in context
                             if "_RING" in n.get("edge", "")} - {""}),
            })

        hidden_count = sum(1 for n in context
                           if n.get("edge") in ("BENEFITS_FROM", "SHARES_DEVICE_WITH",
                                                 "SHARES_ADDRESS_WITH", "ASSOCIATED_WITH"))
        if hidden_count:
            yield emit(EVENT_HIDDEN_RELATION, {"count": hidden_count})

        promoted = [e for e in engine_result.get("entities", [])
                    if (e.get("rerank_reason") or "").startswith("member of ring")]
        if promoted:
            yield emit(EVENT_RING_MEMBER_PROMO, {
                "promoted_ids": [e.get("v_id") for e in promoted],
                "count": len(promoted),
            })

        yield emit(EVENT_NEIGHBORHOOD_DONE, {
            "neighbor_count": engine_result.get("metadata", {}).get("neighbor_count", 0),
        })

        paths = engine_result.get("paths", []) or []
        for p in paths[:3]:
            yield emit(EVENT_TRAVERSAL_PATH, {
                "from": p.get("from", ""),
                "to":   p.get("to", ""),
                "length": p.get("length") or p.get("path_length") or 0,
            })

        evidence = engine_result.get("sources", []) or []
        if evidence:
            yield emit(EVENT_EVIDENCE_COLLECTED, {
                "count": len(evidence),
                "types": sorted({e.get("type", "") for e in evidence}),
            })

        # 4. Build the structured report.
        report = build_report(
            query=query,
            investigation_id=inv_id,
            session_id=session.id,
            engine_result=engine_result,
            elapsed_ms=elapsed_ms,
        )
        report_dict = report.to_dict()
        self._sessions.record_report(session.id, report_dict)

        yield emit(EVENT_REPORT_FINALIZED, report_dict)

    # ── Status / introspection ────────────────────────────────────────────

    def status(self) -> dict:
        cache_hits = getattr(self._client, "_cache_hits", 0)
        cache_misses = getattr(self._client, "_cache_misses", 0)
        return {
            "offline_mode": self._is_offline,
            "session_count": len(self._sessions._sessions),
            "prewarm": self._prewarm_stats,
            "preset_prewarm": self._preset_prewarm_stats,
            "cache_hits": cache_hits,
            "cache_misses": cache_misses,
            "result_cache": self._result_cache.stats(),
        }
