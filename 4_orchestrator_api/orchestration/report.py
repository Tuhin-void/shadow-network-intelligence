"""
InvestigationReport — the canonical structured output of an investigation.

Sections map directly to typed live-graph edges so the structure of the
report is itself the proof of graph-native intelligence.

This module ONLY formats / projects data; it does not call retrieval.
All inputs come from a `GraphRAGEngine.query(...)` result dict.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class ReportEntity:
    v_id: str
    type: str
    name: str
    risk_score: Any = None
    propagated_risk: Any = None
    ring_touch_count: int = 0
    fraud_degree: int = 0
    rerank_reason: str = ""


@dataclass
class ReportRelationship:
    source_v_id: str
    target_v_id: str
    target_type: str
    target_name: str
    edge: str
    via: str = ""
    depth: int = 1


@dataclass
class ReportPath:
    from_v_id: str
    to_v_id: str
    length: int


@dataclass
class ReportEvidence:
    id: str
    type: str
    strength: float
    content: str
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass
class InvestigationReport:
    """
    9-section structured report. Every section is sourced from typed graph
    edges. Empty sections are omitted from the rendered narrative but kept
    in the JSON contract for stable client integration.
    """
    query: str
    investigation_id: str
    session_id: str
    strategy: str
    elapsed_ms: float
    suspects:              list[ReportEntity]       = field(default_factory=list)
    hidden_relationships:  list[ReportRelationship] = field(default_factory=list)
    ring_connections:      list[ReportRelationship] = field(default_factory=list)
    ownership_flow:        list[ReportRelationship] = field(default_factory=list)
    transaction_flows:     list[ReportRelationship] = field(default_factory=list)
    shared_infrastructure: list[ReportRelationship] = field(default_factory=list)
    traversal_paths:       list[ReportPath]         = field(default_factory=list)
    structural_signals:    dict[str, Any]           = field(default_factory=dict)
    evidence_chain:        list[ReportEvidence]     = field(default_factory=list)
    narrative:             str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# Edge classification — used to bucket context items into the correct section.
_RING_EDGES = frozenset({
    "PERSON_MEMBER_OF_RING", "COMPANY_MEMBER_OF_RING",
    "ACCOUNT_MEMBER_OF_RING", "TRANSACTION_MEMBER_OF_RING",
    "DEVICE_CONNECTED_TO_RING", "ADDRESS_CONNECTED_TO_RING",
})
_OWNERSHIP_EDGES = frozenset({"OWNS", "BENEFITS_FROM", "HAS_ACCOUNT"})
_FLOW_EDGES = frozenset({
    "TRANSFERRED_TO", "SENT_TRANSACTION", "RECEIVED_TRANSACTION",
})
_INFRA_EDGES = frozenset({
    "LOCATED_AT", "USES_DEVICE", "ACCESSED_FROM",
    "SHARES_DEVICE_WITH", "SHARES_ADDRESS_WITH", "ASSOCIATED_WITH",
    "REGISTERED_AT",
})


def build_report(
    *,
    query: str,
    investigation_id: str,
    session_id: str,
    engine_result: dict,
    elapsed_ms: float,
) -> InvestigationReport:
    """Project a `GraphRAGEngine.query` result into the structured report."""
    md = engine_result.get("metadata", {}) or {}
    suspects = [
        ReportEntity(
            v_id=e.get("v_id", ""),
            type=e.get("type", ""),
            name=e.get("name") or e.get("v_id", ""),
            risk_score=e.get("risk_score"),
            propagated_risk=e.get("propagated_risk"),
            ring_touch_count=int(e.get("ring_touch_count") or 0),
            fraud_degree=int(e.get("fraud_degree") or 0),
            rerank_reason=e.get("rerank_reason") or "",
        )
        for e in engine_result.get("entities", [])
    ]

    # Bucket context items by edge classification.
    context = engine_result.get("context", []) or []
    seeds = [e.get("v_id", "") for e in engine_result.get("entities", [])]
    seed = seeds[0] if seeds else ""

    hidden_rels: list[ReportRelationship] = []
    ring_conns:  list[ReportRelationship] = []
    own_flow:    list[ReportRelationship] = []
    tx_flow:     list[ReportRelationship] = []
    infra:       list[ReportRelationship] = []

    for n in context:
        edge_raw = n.get("edge", "")
        # Normalize: reverse_* edges from FraudRing-side traversal map back to
        # their canonical forward name so they bucket into RING CONNECTIONS.
        if edge_raw.startswith("reverse_"):
            edge = edge_raw.replace("reverse_", "").upper()
        else:
            edge = edge_raw
        rel = ReportRelationship(
            source_v_id=n.get("via", seed),
            target_v_id=n.get("v_id", ""),
            target_type=n.get("type", ""),
            target_name=n.get("name") or n.get("v_id", ""),
            edge=edge,
            via=n.get("via", ""),
            depth=int(n.get("depth") or 1),
        )
        if edge in _RING_EDGES or edge.startswith("co-"):
            ring_conns.append(rel)
        elif edge in _OWNERSHIP_EDGES:
            own_flow.append(rel)
        elif edge in _FLOW_EDGES:
            tx_flow.append(rel)
        elif edge in _INFRA_EDGES:
            infra.append(rel)
        else:
            hidden_rels.append(rel)

    # Cap each section to keep reports compact for UI rendering.
    SECTION_CAP = 8
    paths = [
        ReportPath(
            from_v_id=str(p.get("from", "")),
            to_v_id=str(p.get("to", "")),
            length=int(p.get("length") or p.get("path_length") or 0),
        )
        for p in (engine_result.get("paths", []) or [])[:SECTION_CAP]
    ]

    evidence = [
        ReportEvidence(
            id=str(s.get("id", "")),
            type=str(s.get("type", "")),
            strength=float(s.get("strength") or 0),
            content=str(s.get("content", "")),
            provenance=s.get("provenance", {}) or {},
        )
        for s in (engine_result.get("sources", []) or [])[:6]
    ]

    structural_signals = {
        "entity_count":    md.get("entity_count", 0),
        "neighbor_count":  md.get("neighbor_count", 0),
        "evidence_count":  md.get("evidence_count", 0),
        "strategy":        md.get("strategy", ""),
        "ring_touch_sum":  sum(s.ring_touch_count for s in suspects),
        "fraud_degree_sum": sum(s.fraud_degree for s in suspects),
        "context_breakdown": {
            "ring_connections":      len(ring_conns),
            "ownership_flow":        len(own_flow),
            "transaction_flows":     len(tx_flow),
            "shared_infrastructure": len(infra),
            "hidden_relationships":  len(hidden_rels),
        },
    }

    return InvestigationReport(
        query=query,
        investigation_id=investigation_id,
        session_id=session_id,
        strategy=md.get("strategy", ""),
        elapsed_ms=elapsed_ms,
        suspects=suspects[:SECTION_CAP],
        hidden_relationships=hidden_rels[:SECTION_CAP],
        ring_connections=ring_conns[:SECTION_CAP],
        ownership_flow=own_flow[:SECTION_CAP],
        transaction_flows=tx_flow[:SECTION_CAP],
        shared_infrastructure=infra[:SECTION_CAP],
        traversal_paths=paths,
        structural_signals=structural_signals,
        evidence_chain=evidence,
        narrative=str(engine_result.get("answer", "")),
    )
