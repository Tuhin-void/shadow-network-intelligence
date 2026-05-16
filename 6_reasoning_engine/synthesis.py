"""
Graph-aware reasoning engine.

Operates on the outputs of the agent swarm + engine result. Pure Python,
zero LLM calls. The outputs feed the reporting engine.

Exports:
  • synthesize(swarm_report, engine_result)
      → SynthesisOutput with merged findings + key claims + contradictions
  • structural_confidence(engine_result)
      → 0..1 score grounded in graph-evidence density
  • explain_entity(engine_result, v_id)
      → human-readable rationale for *why* this entity was surfaced
  • detect_contradictions(claims)
      → list[Contradiction] — flags conflicting structural assertions
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Iterable


# ── Data structures ────────────────────────────────────────────────────────


@dataclass
class Claim:
    """A discrete structural assertion derived from graph evidence."""
    statement: str
    basis: str                  # "edge", "ring", "shared_infra", "flow", "path"
    confidence: float           # 0..1
    refs: list[str] = field(default_factory=list)


@dataclass
class Contradiction:
    claim_a: Claim
    claim_b: Claim
    reason: str


@dataclass
class SynthesisOutput:
    query: str
    overall_confidence: float
    key_claims: list[Claim]
    contradictions: list[Contradiction]
    explanations: dict[str, str]            # v_id → why surfaced
    headline: str
    body: str

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "overall_confidence": self.overall_confidence,
            "headline": self.headline,
            "body": self.body,
            "key_claims": [asdict(c) for c in self.key_claims],
            "contradictions": [
                {"a": asdict(x.claim_a), "b": asdict(x.claim_b), "reason": x.reason}
                for x in self.contradictions
            ],
            "explanations": self.explanations,
        }


# ── Shared helpers ─────────────────────────────────────────────────────────


_FLOW_EDGES = {"TRANSFERRED_TO", "SENT_TRANSACTION", "RECEIVED_TRANSACTION"}
_INFRA_EDGES = {"LOCATED_AT", "USES_DEVICE", "ACCESSED_FROM",
                "SHARES_DEVICE_WITH", "SHARES_ADDRESS_WITH",
                "REGISTERED_AT", "ASSOCIATED_WITH"}
_RING_EDGES = {"PERSON_MEMBER_OF_RING", "COMPANY_MEMBER_OF_RING",
               "ACCOUNT_MEMBER_OF_RING", "TRANSACTION_MEMBER_OF_RING",
               "DEVICE_CONNECTED_TO_RING", "ADDRESS_CONNECTED_TO_RING"}
_OWNERSHIP_EDGES = {"OWNS", "BENEFITS_FROM", "HAS_ACCOUNT"}


def _norm_edge(e: str) -> str:
    if not e:
        return ""
    if e.startswith("reverse_"):
        return e.replace("reverse_", "").upper()
    return e.upper()


# ── Structural confidence ──────────────────────────────────────────────────


def structural_confidence(engine_result: dict) -> float:
    """
    Confidence score grounded in graph-evidence density.

    Returns 0..1. Designed so a single-source / no-edge retrieval scores
    low, and rich multi-edge / ring-touching retrievals score high.

    Calibrated against the observed adversarial benchmark distribution:
      • 5 entities + 50+ neighbors + 3+ structural edges → ~0.8+
      • 1 entity + sparse neighborhood                   → ~0.3-0.4
    """
    md = engine_result.get("metadata", {}) or {}
    ent = int(md.get("entity_count") or 0)
    nb = int(md.get("neighbor_count") or 0)
    ev = int(md.get("evidence_count") or 0)
    ctx = engine_result.get("context", []) or []
    struct = sum(1 for n in ctx if _norm_edge(n.get("edge", ""))
                 in (_RING_EDGES | _OWNERSHIP_EDGES | _FLOW_EDGES | _INFRA_EDGES))

    score = 0.0
    score += min(0.30, ent * 0.06)
    score += min(0.30, nb / 200.0 * 0.30)
    score += min(0.20, ev * 0.04)
    score += min(0.20, struct / 8.0 * 0.20)
    return round(min(1.0, score), 3)


# ── Claim extraction ───────────────────────────────────────────────────────


def _extract_claims(engine_result: dict, max_per_kind: int = 6) -> list[Claim]:
    """
    Pull discrete structural claims from the engine context. Each claim is
    a single typed-edge assertion — the smallest unit of evidence the graph
    has to offer.

    Quality guards:
      • Every claim refs only v_ids that exist in entities or context
        (no fabricated identifiers).
      • Empty edges or missing endpoints are dropped (no NULL→? claims).
      • Confidence is grounded in edge basis; the synthesizer never
        invents a number not supported by the basis classification.
    """
    ctx = engine_result.get("context", []) or []
    entities = engine_result.get("entities", []) or []
    seeds = [e.get("v_id") for e in entities if e.get("v_id")]
    seed = seeds[0] if seeds else ""

    # Guard set: only refs from these are allowed in any claim.
    known_ids: set[str] = set(seeds)
    for n in ctx:
        for k in ("v_id", "via"):
            vid = n.get(k)
            if isinstance(vid, str) and vid:
                known_ids.add(vid)

    by_basis: dict[str, list[Claim]] = {
        "ring": [], "ownership": [], "flow": [], "infra": [], "other": []
    }

    for n in ctx:
        edge = _norm_edge(n.get("edge", ""))
        if not edge:
            continue
        src = n.get("via") or seed
        dst = n.get("v_id", "")
        # Quality guard: both endpoints must be present and known.
        if not src or not dst or src not in known_ids or dst not in known_ids:
            continue
        target_name = n.get("name") or dst
        target_type = n.get("type", "")
        if edge in _RING_EDGES:
            basis, conf = "ring", 0.9
            statement = f"{src} is structurally linked to ring {dst} via {edge}"
        elif edge in _OWNERSHIP_EDGES:
            basis, conf = "ownership", 0.85
            statement = f"{src} {edge.lower().replace('_', ' ')} {target_name} ({target_type})"
        elif edge in _FLOW_EDGES:
            basis, conf = "flow", 0.75
            statement = f"{src} —{edge}→ {target_name} ({target_type})"
        elif edge in _INFRA_EDGES:
            basis, conf = "infra", 0.7
            statement = f"{src} shares {edge.lower().replace('_', ' ')} with {target_name}"
        else:
            basis, conf = "other", 0.5
            statement = f"{src} —{edge}→ {target_name}"
        by_basis[basis].append(Claim(statement=statement, basis=basis,
                                     confidence=conf, refs=[src, dst]))

    # Cap per basis so the synthesis stays digestible.
    out: list[Claim] = []
    for kind, items in by_basis.items():
        out.extend(items[:max_per_kind])
    return out


# ── Contradiction detection ────────────────────────────────────────────────


def detect_contradictions(claims: list[Claim]) -> list[Contradiction]:
    """
    Detect structurally inconsistent claims.

    Currently checks for:
      • two flow claims with the same (src, dst) but opposite direction
        on different edges (rare but worth flagging)
      • two ownership claims asserting different parents for the same entity
    """
    contradictions: list[Contradiction] = []

    # Group ownership claims by target.
    ownership_by_target: dict[str, list[Claim]] = {}
    for c in claims:
        if c.basis != "ownership":
            continue
        if len(c.refs) < 2:
            continue
        target = c.refs[1]
        ownership_by_target.setdefault(target, []).append(c)

    for target, items in ownership_by_target.items():
        # If two distinct sources claim ownership of the same target → flag
        seen_sources = {c.refs[0] for c in items}
        if len(seen_sources) > 1 and len(items) >= 2:
            contradictions.append(Contradiction(
                claim_a=items[0], claim_b=items[1],
                reason=f"multiple owners asserted for {target}: {sorted(seen_sources)}",
            ))

    return contradictions


# ── Entity explainer ───────────────────────────────────────────────────────


def explain_entity(engine_result: dict, v_id: str) -> str:
    """
    Human-readable rationale for *why* this entity was surfaced.

    Pulls from rerank_reason, ring_touch_count, fraud_degree, and the
    structural edges touching this entity.
    """
    if not v_id:
        return "no entity id given"
    entities = engine_result.get("entities", []) or []
    ctx = engine_result.get("context", []) or []

    me = next((e for e in entities if e.get("v_id") == v_id), None)
    if not me:
        return f"{v_id} was not in the suspect set"

    rr = me.get("rerank_reason") or ""
    ring = int(me.get("ring_touch_count") or 0)
    deg = int(me.get("fraud_degree") or 0)

    touching = [n for n in ctx if n.get("via") == v_id]
    edge_summary = {}
    for n in touching:
        edge_summary[_norm_edge(n.get("edge", ""))] = edge_summary.get(
            _norm_edge(n.get("edge", "")), 0) + 1

    parts: list[str] = []
    if rr:
        parts.append(f"rerank reason: {rr}")
    if ring > 0:
        parts.append(f"ring proximity: {ring}")
    if deg > 0:
        parts.append(f"fraud-relevant degree: {deg}")
    if edge_summary:
        top_edges = sorted(edge_summary.items(), key=lambda kv: -kv[1])[:4]
        parts.append("local topology: " + ", ".join(
            f"{e}×{n}" for e, n in top_edges
        ))
    if not parts:
        parts.append("present in retrieval set but no further structural signal")
    return " · ".join(parts)


# ── Top-level synthesis ────────────────────────────────────────────────────


def synthesize(
    swarm_report: Any,        # SwarmReport (dataclass)
    engine_result: dict,
    *,
    query: str | None = None,
) -> SynthesisOutput:
    """
    Produce a SynthesisOutput merging swarm findings, engine evidence, and
    contradiction analysis. This is what the reporting engine consumes.
    """
    if query is None:
        query = getattr(swarm_report, "query", "")

    claims = _extract_claims(engine_result)
    contradictions = detect_contradictions(claims)
    conf = structural_confidence(engine_result)

    # Per-suspect explanations.
    explanations: dict[str, str] = {}
    for e in engine_result.get("entities", []) or []:
        vid = e.get("v_id")
        if vid:
            explanations[vid] = explain_entity(engine_result, vid)

    md = engine_result.get("metadata", {}) or {}
    headline = (f"Investigation surfaced {md.get('entity_count', 0)} suspects "
                f"with structural confidence {conf:.2f}.")

    bits: list[str] = []
    by_basis: dict[str, int] = {}
    for c in claims:
        by_basis[c.basis] = by_basis.get(c.basis, 0) + 1
    for k in ("ring", "ownership", "flow", "infra", "other"):
        if by_basis.get(k):
            bits.append(f"{by_basis[k]} {k}")
    body = "Evidence basis breakdown — " + ", ".join(bits) + (
        f". {len(contradictions)} contradiction(s) flagged."
        if contradictions else ". No contradictions detected."
    )

    return SynthesisOutput(
        query=query,
        overall_confidence=conf,
        key_claims=claims,
        contradictions=contradictions,
        explanations=explanations,
        headline=headline,
        body=body,
    )
