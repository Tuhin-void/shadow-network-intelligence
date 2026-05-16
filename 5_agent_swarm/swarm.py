"""
Professional investigation swarm — 5 narrow focused agents.

These agents COMPOSE the existing GraphRAGEngine. They are NOT autonomous
chat-bots — each one runs a single deterministic analysis pass over a
shared `engine_result` dict and returns a structured `AgentFinding`.

Agents (each ~30-80 LOC of analysis logic):

  • RetrievalAnalyst          — qualifies retrieval coverage, recall, structural-edge density
  • GraphTopologyInvestigator — walks structural patterns around the suspects
  • SanctionsExposureTracer   — filters sanctioned entities + traces flow exposure
  • FraudRingAnalyst          — ring-centric structural analysis (membership, severity)
  • SynthesisCoordinator      — orchestrates the four above + merges to single dossier

CLI:
  python3 -m 5_agent_swarm "Identify members of fraud ring FR-002"
  python3 -m 5_agent_swarm --preset ring-identification
"""
from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "3_graph_intelligence_core") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "3_graph_intelligence_core"))


# ── Data structures ────────────────────────────────────────────────────────


@dataclass
class AgentFinding:
    """Structured output from a single agent run."""
    agent: str
    summary: str
    confidence: float            # 0..1
    findings: list[dict]         # narrow per-agent items
    metrics: dict[str, Any]      # numeric signals
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SwarmReport:
    """The coordinator's consolidated output."""
    query: str
    investigation_id: str
    elapsed_ms: float
    agents: list[AgentFinding]
    coordinator_summary: str
    consolidated_metrics: dict[str, Any]

    def to_dict(self) -> dict:
        return {
            **{k: v for k, v in asdict(self).items() if k != "agents"},
            "agents": [a.to_dict() for a in self.agents],
        }


# ── Shared utility ─────────────────────────────────────────────────────────


_STRUCTURAL_EDGES = frozenset({
    "OWNS", "BENEFITS_FROM", "HAS_ACCOUNT",
    "TRANSFERRED_TO", "SENT_TRANSACTION", "RECEIVED_TRANSACTION",
    "SHARES_DEVICE_WITH", "SHARES_ADDRESS_WITH", "ASSOCIATED_WITH",
    "USES_DEVICE", "LOCATED_AT", "REGISTERED_AT", "ACCESSED_FROM",
    "PERSON_MEMBER_OF_RING", "COMPANY_MEMBER_OF_RING", "ACCOUNT_MEMBER_OF_RING",
    "TRANSACTION_MEMBER_OF_RING", "DEVICE_CONNECTED_TO_RING",
    "ADDRESS_CONNECTED_TO_RING",
})


def _edge_normal(e: str) -> str:
    """Strip 'reverse_' prefix and uppercase for canonical comparison."""
    if not e:
        return ""
    if e.startswith("reverse_"):
        return e.replace("reverse_", "").upper()
    return e.upper()


# ── Agents ─────────────────────────────────────────────────────────────────


class RetrievalAnalyst:
    """Qualifies the retrieval pass: coverage, density, evidence completeness."""

    name = "retrieval_analyst"

    def analyze(self, engine_result: dict) -> AgentFinding:
        md = engine_result.get("metadata", {}) or {}
        ent_count = int(md.get("entity_count") or 0)
        nb_count = int(md.get("neighbor_count") or 0)
        ev_count = int(md.get("evidence_count") or 0)
        ctx = engine_result.get("context", []) or []

        struct = sum(1 for n in ctx if _edge_normal(n.get("edge", "")) in _STRUCTURAL_EDGES)
        unique_edge_types = sorted({_edge_normal(n.get("edge", "")) for n in ctx} - {""})

        # Confidence: scales with how rich the retrieval surface is.
        # Calibrated against observed adversarial-benchmark distribution.
        confidence = 0.0
        if ent_count >= 1:
            confidence += 0.3
        if nb_count >= 50:
            confidence += 0.3
        elif nb_count >= 10:
            confidence += 0.15
        if struct >= 3:
            confidence += 0.25
        if ev_count >= 3:
            confidence += 0.15

        notes = []
        if ent_count == 0:
            notes.append("no entities surfaced — retrieval missed completely")
        if nb_count < 5:
            notes.append("very small neighborhood — query may have been too narrow")
        if struct == 0:
            notes.append("no structural edges retrieved — degraded to text-mode")

        return AgentFinding(
            agent=self.name,
            summary=(f"{ent_count} suspects · {nb_count} neighbors · "
                     f"{struct} structural edges · {ev_count} evidence items"),
            confidence=min(1.0, confidence),
            findings=[{"edge_type": e, "count": sum(1 for n in ctx if _edge_normal(n.get("edge","")) == e)}
                      for e in unique_edge_types],
            metrics={
                "entity_count": ent_count,
                "neighbor_count": nb_count,
                "evidence_count": ev_count,
                "structural_edges": struct,
                "unique_edge_types": len(unique_edge_types),
            },
            notes=notes,
        )


class GraphTopologyInvestigator:
    """Walks structural patterns around the suspects: degree, shared infra."""

    name = "graph_topology_investigator"

    def analyze(self, engine_result: dict) -> AgentFinding:
        entities = engine_result.get("entities", []) or []
        ctx = engine_result.get("context", []) or []

        # Group context by source v_id to compute per-suspect degree.
        per_suspect: dict[str, dict[str, int]] = {}
        for n in ctx:
            via = n.get("via") or ""
            if not via:
                continue
            bucket = per_suspect.setdefault(via, {})
            edge = _edge_normal(n.get("edge", ""))
            bucket[edge] = bucket.get(edge, 0) + 1

        findings: list[dict] = []
        for e in entities:
            vid = e.get("v_id")
            if not vid:
                continue
            edge_mix = per_suspect.get(vid, {})
            degree = sum(edge_mix.values())
            findings.append({
                "v_id": vid,
                "name": e.get("name", vid),
                "type": e.get("type", "?"),
                "fraud_degree": e.get("fraud_degree", 0),
                "ring_touch_count": e.get("ring_touch_count", 0),
                "neighborhood_degree": degree,
                "edge_mix": edge_mix,
            })

        # Aggregate signals
        total_degree = sum(f["neighborhood_degree"] for f in findings)
        avg_fraud_degree = (sum(f["fraud_degree"] for f in findings) / len(findings)
                             if findings else 0)
        ring_pop = sum(1 for f in findings if f["ring_touch_count"] > 0)

        confidence = min(1.0,
                         0.4 + (0.05 * min(total_degree, 10)) + (0.2 if ring_pop else 0))

        summary = (f"{len(findings)} suspects · total local degree {total_degree} · "
                   f"avg fraud-degree {avg_fraud_degree:.1f} · "
                   f"{ring_pop} ring-member(s)")

        return AgentFinding(
            agent=self.name,
            summary=summary,
            confidence=confidence,
            findings=findings,
            metrics={
                "total_local_degree": total_degree,
                "avg_fraud_degree": round(avg_fraud_degree, 2),
                "ring_member_suspects": ring_pop,
            },
        )


class SanctionsExposureTracer:
    """
    Detects sanctioned-entity exposure paths.

    This agent doesn't require live KYC data — it inspects engine output
    for any entity whose attrs (or rerank reason) signal a sanctions flag,
    then traces fund-flow edges outward from those entities.
    """

    name = "sanctions_exposure_tracer"

    _FLAG_HINTS = ("sanction", "pep", "blacklist", "watch")
    _FLOW_EDGES = frozenset({
        "TRANSFERRED_TO", "SENT_TRANSACTION", "RECEIVED_TRANSACTION", "HAS_ACCOUNT",
    })

    def analyze(self, engine_result: dict) -> AgentFinding:
        entities = engine_result.get("entities", []) or []
        ctx = engine_result.get("context", []) or []

        flagged: list[dict] = []
        for e in entities:
            blob = " ".join(str(v) for v in (
                e.get("rerank_reason", ""),
                e.get("name", ""),
                e.get("v_id", ""),
                e.get("flags", ""),
            )).lower()
            if any(h in blob for h in self._FLAG_HINTS):
                flagged.append(e)

        # Trace flow edges starting from flagged entities.
        flow_paths: list[dict] = []
        flagged_ids = {e.get("v_id") for e in flagged}
        for n in ctx:
            if _edge_normal(n.get("edge", "")) not in self._FLOW_EDGES:
                continue
            via = n.get("via", "")
            if via in flagged_ids:
                flow_paths.append({
                    "from": via,
                    "to": n.get("v_id"),
                    "edge": n.get("edge"),
                    "depth": n.get("depth", 1),
                })

        confidence = 0.15
        if flagged:
            confidence = 0.55
        if flow_paths:
            confidence = min(1.0, 0.55 + 0.05 * len(flow_paths))

        return AgentFinding(
            agent=self.name,
            summary=(f"{len(flagged)} flagged entities · "
                     f"{len(flow_paths)} downstream flow paths traced"),
            confidence=confidence,
            findings=[{
                "flagged_entities": [{"v_id": e.get("v_id"), "name": e.get("name")}
                                     for e in flagged],
                "flow_paths": flow_paths[:20],
            }],
            metrics={
                "flagged_count": len(flagged),
                "flow_paths_count": len(flow_paths),
            },
            notes=([] if flagged else ["no sanctioned/PEP signal in this retrieval"]),
        )


class FraudRingAnalyst:
    """Ring-centric structural analysis: membership, severity, density."""

    name = "fraud_ring_analyst"

    _RING_EDGES = frozenset({
        "PERSON_MEMBER_OF_RING", "COMPANY_MEMBER_OF_RING",
        "ACCOUNT_MEMBER_OF_RING", "TRANSACTION_MEMBER_OF_RING",
        "DEVICE_CONNECTED_TO_RING", "ADDRESS_CONNECTED_TO_RING",
    })

    def analyze(self, engine_result: dict) -> AgentFinding:
        ctx = engine_result.get("context", []) or []
        entities = engine_result.get("entities", []) or []

        rings_seen: dict[str, dict[str, int]] = {}
        for n in ctx:
            edge = _edge_normal(n.get("edge", ""))
            if edge not in self._RING_EDGES:
                continue
            # The ring id is either source or target depending on direction.
            ring_id = None
            for cand in (n.get("via", ""), n.get("v_id", "")):
                if isinstance(cand, str) and cand.startswith("FR-"):
                    ring_id = cand
                    break
            if not ring_id:
                continue
            r = rings_seen.setdefault(ring_id, {})
            r[edge] = r.get(edge, 0) + 1

        # Also pick up promoted ring members from suspects.
        promoted: dict[str, list[str]] = {}
        for e in entities:
            rr = e.get("rerank_reason", "") or ""
            if rr.startswith("member of ring"):
                rid = rr.split("member of ring", 1)[-1].strip()
                promoted.setdefault(rid, []).append(e.get("v_id", ""))

        findings = [{
            "ring_id": rid,
            "edges_observed": rings_seen.get(rid, {}),
            "promoted_members_in_suspects": promoted.get(rid, []),
        } for rid in sorted(set(rings_seen) | set(promoted))]

        ring_count = len(findings)
        confidence = 0.2 + min(0.7, 0.2 * ring_count)
        if ring_count == 0:
            return AgentFinding(
                agent=self.name,
                summary="no fraud rings touched by this retrieval",
                confidence=0.15,
                findings=[],
                metrics={"rings_touched": 0},
            )

        return AgentFinding(
            agent=self.name,
            summary=(f"{ring_count} ring(s) touched · "
                     f"{sum(len(f['promoted_members_in_suspects']) for f in findings)} "
                     f"members promoted into suspects"),
            confidence=min(1.0, confidence),
            findings=findings,
            metrics={
                "rings_touched": ring_count,
                "ring_membership_edges": sum(
                    sum(f["edges_observed"].values()) for f in findings),
            },
        )


class SynthesisCoordinator:
    """
    Runs the four agents in deterministic order and merges their findings.

    Returns a SwarmReport. This is the entry point used by the reporting
    engine and the CLI.
    """

    name = "synthesis_coordinator"

    def __init__(self, engine: Any | None = None) -> None:
        if engine is None:
            from clients.graph_client import GraphClient
            from configs.config import load_config
            from graph_rag.graphrag_engine import GraphRAGEngine
            cfg = load_config(None)
            self._engine = GraphRAGEngine(GraphClient(cfg), cfg,
                                          compression="rule_based")
        else:
            self._engine = engine
        self._agents = [
            RetrievalAnalyst(),
            GraphTopologyInvestigator(),
            SanctionsExposureTracer(),
            FraudRingAnalyst(),
        ]

    def run(self, query: str, *, top_k: int = 5, depth: int = 2,
            strategy: str = "auto") -> SwarmReport:
        t0 = time.perf_counter()
        engine_result = self._engine.query(
            query=query,
            config={"strategy": strategy, "top_k": top_k, "depth": depth},
        )
        # Ensure context is exposed (engine returns it; some older paths may not).
        engine_result.setdefault("context",
                                 engine_result.get("context", []))

        findings = [a.analyze(engine_result) for a in self._agents]
        elapsed_ms = (time.perf_counter() - t0) * 1000

        # Coordinator synthesis: terse executive overview.
        ent = findings[0].metrics["entity_count"]
        nb = findings[0].metrics["neighbor_count"]
        struct = findings[0].metrics["structural_edges"]
        rings = findings[3].metrics["rings_touched"]
        flagged = findings[2].metrics["flagged_count"]

        verdict_bits = []
        if rings > 0:
            verdict_bits.append(f"{rings} ring(s) touched")
        if flagged > 0:
            verdict_bits.append(f"{flagged} sanctioned entity exposure")
        if struct >= 3:
            verdict_bits.append("multi-edge structural evidence present")
        verdict = " · ".join(verdict_bits) or "low structural signal"

        coordinator_summary = (
            f"Investigation surfaced {ent} suspects across {nb} neighbors "
            f"with {struct} structural edges. {verdict}."
        )

        # Average agent confidence as one trustable headline number.
        avg_conf = sum(f.confidence for f in findings) / len(findings) if findings else 0.0
        prov_md = engine_result.get("metadata", {}) or {}

        return SwarmReport(
            query=query,
            investigation_id=f"SWARM-{int(time.time()*1000)}",
            elapsed_ms=elapsed_ms,
            agents=findings,
            coordinator_summary=coordinator_summary,
            consolidated_metrics={
                "avg_agent_confidence": round(avg_conf, 3),
                "engine_strategy": prov_md.get("strategy", ""),
                "engine_cache_hit": bool(prov_md.get("cache_hit", False)),
                "structural_edges_surfaced": struct,
                "rings_touched": rings,
                "flagged_entities": flagged,
            },
        )
