"""
IntentClassifier — deterministic mapping from analyst natural-language
queries to first-class investigation workflows.

Hard contracts:
  • Pure Python. No LLM call, no fabrication, fast (sub-millisecond).
  • Output is always a structured record — never a free-text answer.
  • An unmapped query returns `kind="unknown"` AND a list of suggested
    workflows so the UI can present operational guidance instead of
    chatbot-style fallback prose.
  • Detected entity IDs (P-, C-, A-, ADDR-, D-, TX-, FR-) are surfaced
    explicitly so the downstream engine can short-circuit token-matching.

This module IS the contract between the UI and the engine for what kind
of investigation a query represents. The existing retriever weights are
NOT modified here — the intent label flows into the report payload and
into the events stream so analysts know which workflow they triggered.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Optional

# Entity ID prefixes the platform uses everywhere.
_ENTITY_ID_RE = re.compile(
    r'\b(P-\d+|C-\d+|A-\d+|ADDR-\d+|D-\d+|TX-\d+|T-\d+|FR-[A-Z0-9_-]+)\b',
    re.IGNORECASE,
)


@dataclass
class IntentMatch:
    kind: str
    display_name: str
    description: str
    confidence: float           # 0..1 — how well the query matched (token overlap)
    matched_patterns: list[str] = field(default_factory=list)
    matched_entity_ids: list[str] = field(default_factory=list)
    strategy_hint: str = "auto"
    suggested_workflows: list[dict] = field(default_factory=list)
    requires_entity_id: bool = False
    # Operational hint shown when intent is unknown / weakly matched —
    # the UI surfaces this so the analyst sees concrete next steps.
    operational_hint: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ── Workflow catalog ────────────────────────────────────────────────────
# Each entry has:
#   kind         — stable id used by frontend + persistence
#   display_name — analyst-facing label
#   description  — one-sentence narrative of what the workflow does
#   keywords     — set of trigger words (matched as whole words, case-insensitive)
#   patterns     — additional regex patterns (compiled below)
#   strategy_hint — what to pass to engine.query(config={"strategy": ...})
#                   (today the engine ignores most of these — emitted for
#                    future routing and for UI display)

_WORKFLOWS: list[dict] = [
    {
        "kind": "rank_suspects",
        "display_name": "suspicious entity ranking",
        "description": "rank entities by combined risk, ring proximity, and topology centrality",
        "keywords": [
            "suspected", "suspect", "suspects", "suspicious", "suspicion",
            "highest", "risk", "risky", "risks", "highrisk",
            "ranking", "ranked", "rank", "top", "most",
            "dangerous", "concerning",
        ],
        "patterns": [
            r"who('?s| is) (the )?most",
            r"top \d* ?(suspect|risky|risk|suspicious)",
            r"highest[- ]risk",
            r"rank(ed)? (the )?(suspect|entit|account|person)",
        ],
        "strategy_hint": "auto",
    },
    {
        "kind": "find_ring",
        "display_name": "fraud ring discovery",
        "description": "surface fraud rings and their members; expose ring continuity",
        "keywords": [
            "ring", "rings", "cluster", "clusters", "syndicate", "syndicates",
            "network", "networks", "circle", "circles",
        ],
        "patterns": [
            r"(show|find|surface|reveal|expose)( me)? (hidden |the )?(fraud )?ring",
            r"identify( the)? (fraud )?ring",
        ],
        "strategy_hint": "community",
    },
    {
        "kind": "trace_money",
        "display_name": "money-flow tracing",
        "description": "trace transactional paths between entities and through chains",
        "keywords": [
            "trace", "tracing", "follow", "flow", "flows", "money",
            "laundering", "launder", "wash", "washing",
            "transaction", "transactions", "transfer", "transfers",
            "path", "paths", "chain", "chains",
        ],
        "patterns": [
            r"trac(e|ing)( the)? (money|funds?|transaction|launder)",
            r"follow( the)? (money|funds?|cash)",
            r"laundering pat(h|hs)",
            r"transaction( |-)flow",
        ],
        "strategy_hint": "path",
    },
    {
        "kind": "ownership_chain",
        "display_name": "ownership chain analysis",
        "description": "reverse-traverse OWNS edges to expose beneficial ownership",
        "keywords": [
            "ownership", "owner", "owners", "owned", "owns",
            "beneficiary", "beneficiaries", "beneficial",
            "ultimate", "behind", "control", "controls", "controlled",
        ],
        "patterns": [
            r"who owns",
            r"ownership chain",
            r"beneficial owner",
            r"who('?s| is) behind",
        ],
        "strategy_hint": "path",
    },
    {
        "kind": "shared_infrastructure",
        "display_name": "shared-infrastructure detection",
        "description": "surface entities co-using devices, addresses, or accounts",
        "keywords": [
            "shared", "share", "shares", "sharing",
            "device", "devices", "address", "addresses",
            "infrastructure", "overlap", "overlapping", "common",
            "co-located", "colocated",
        ],
        "patterns": [
            r"shared (device|address|account|ip)",
            r"who( else)? shares",
            r"common (device|address|account|ip)",
        ],
        "strategy_hint": "neighborhood",
    },
    {
        "kind": "hidden_relationships",
        "display_name": "hidden-relationship discovery",
        "description": "surface BENEFITS_FROM / ASSOCIATED_WITH / inferred edges",
        "keywords": [
            "hidden", "concealed", "covert", "buried",
            "uncover", "expose", "reveal", "discover",
            "relationship", "relationships", "link", "links",
            "connection", "connections", "tie", "ties",
        ],
        "patterns": [
            r"hidden (relation|connection|link)",
            r"uncover (hidden|secret|concealed)",
        ],
        "strategy_hint": "neighborhood",
    },
    {
        "kind": "entity_dossier",
        "display_name": "entity dossier",
        "description": "build a multi-hop dossier centered on the named entity",
        "keywords": [
            "tell", "show", "about", "dossier", "profile",
            "summary", "summarize",
        ],
        "patterns": [
            r"(tell|show)( me)? (about|everything about|the dossier)",
            r"profile( the| of)?",
        ],
        "strategy_hint": "entity_centric",
        "requires_entity_id": True,
    },
    {
        "kind": "neighborhood_expansion",
        "display_name": "neighborhood expansion",
        "description": "expand the typed-edge neighborhood around the named entity",
        "keywords": [
            "neighbor", "neighbors", "neighbour", "neighbourhood",
            "connected", "connection", "connections",
            "around", "near", "adjacent",
        ],
        "patterns": [
            r"connected to",
            r"what('?s| is) (around|near|adjacent to)",
        ],
        "strategy_hint": "neighborhood",
        "requires_entity_id": True,
    },
]

# Pre-compile keyword and pattern matchers for fast classification.
for _wf in _WORKFLOWS:
    _wf["_compiled_patterns"] = [
        re.compile(p, re.IGNORECASE) for p in _wf.get("patterns", [])
    ]
    _wf["_keyword_set"] = {k.lower() for k in _wf.get("keywords", [])}


def _tokenize(q: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9]+", q.lower()) if t]


def _suggested_workflows() -> list[dict]:
    """Surfaced when intent is unknown — operational, not chatbot."""
    return [
        {"kind": wf["kind"], "display_name": wf["display_name"],
         "description": wf["description"]}
        for wf in _WORKFLOWS
        if wf["kind"] in (
            "rank_suspects", "find_ring", "trace_money",
            "ownership_chain", "shared_infrastructure",
        )
    ]


class IntentClassifier:
    """Deterministic intent classifier. Pure Python, no LLM."""

    def classify(self, query: str) -> IntentMatch:
        if not query or not query.strip():
            return IntentMatch(
                kind="unknown",
                display_name="empty query",
                description="no query text provided",
                confidence=0.0,
                suggested_workflows=_suggested_workflows(),
                operational_hint=(
                    "Provide a question that maps to a structural workflow "
                    "— e.g. 'who is the most suspected' or 'trace laundering paths'."
                ),
            )

        text = query.strip()
        tokens = set(_tokenize(text))
        entity_ids = sorted({m.upper() for m in _ENTITY_ID_RE.findall(text)})

        best: Optional[IntentMatch] = None
        for wf in _WORKFLOWS:
            keyword_overlap = tokens & wf["_keyword_set"]
            pattern_hits = [
                p.pattern for p in wf["_compiled_patterns"] if p.search(text)
            ]
            if not keyword_overlap and not pattern_hits:
                continue

            # Confidence: keyword overlap dominates, pattern hits boost.
            kw_score = (
                min(len(keyword_overlap) / 2.0, 1.0)
                if wf["_keyword_set"] else 0.0
            )
            pat_score = min(len(pattern_hits), 2) * 0.4
            confidence = min(kw_score + pat_score, 1.0)

            # `requires_entity_id` workflows only fire confidently if an
            # entity ID is present. Otherwise downgrade but don't reject —
            # the UI can offer to investigate the most-named entity.
            if wf.get("requires_entity_id") and not entity_ids:
                confidence *= 0.5

            candidate = IntentMatch(
                kind=wf["kind"],
                display_name=wf["display_name"],
                description=wf["description"],
                confidence=round(confidence, 3),
                matched_patterns=pattern_hits + sorted(keyword_overlap),
                matched_entity_ids=entity_ids,
                strategy_hint=wf.get("strategy_hint", "auto"),
                requires_entity_id=wf.get("requires_entity_id", False),
            )
            if best is None or candidate.confidence > best.confidence:
                best = candidate

        if best is None or best.confidence < 0.25:
            return IntentMatch(
                kind="unknown",
                display_name="unmapped query",
                description=(
                    "query does not map cleanly to a structural investigation workflow"
                ),
                confidence=best.confidence if best else 0.0,
                matched_entity_ids=entity_ids,
                suggested_workflows=_suggested_workflows(),
                operational_hint=(
                    "rephrase using a structural verb — e.g. 'rank', 'trace', "
                    "'surface', 'connected to' — or include an entity ID like "
                    "'P-005027' or 'FR-001'."
                ),
            )
        return best


# Singleton — classifier is stateless and cheap to share.
_singleton: Optional[IntentClassifier] = None


def get_classifier() -> IntentClassifier:
    global _singleton
    if _singleton is None:
        _singleton = IntentClassifier()
    return _singleton
