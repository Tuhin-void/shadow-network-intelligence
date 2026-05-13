"""
Investigation events — the stream of structural-intelligence moments
that the UI consumes to "play" an investigation live.

Each event is a typed dataclass with:
  - kind         : event type discriminator
  - timestamp_ms : monotonic emission time
  - payload      : event-specific dict

Events are emitted in the order:
  session_started → query_received → entity_found* → neighborhood_expanded
  → ring_discovered* → hidden_relationship* → traversal_path*
  → evidence_collected → report_finalized

This is the "intelligence-as-it-unfolds" surface the cinematic UI hooks into.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class InvestigationEvent:
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp_ms: float = field(default_factory=lambda: time.time() * 1000)
    session_id: str = ""
    seq: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


# Event kinds — kept stable; UI contracts depend on these names.
EVENT_SESSION_STARTED   = "session.started"
EVENT_QUERY_RECEIVED    = "query.received"
EVENT_PREWARM_DONE      = "prewarm.done"
EVENT_ENTITY_FOUND      = "entity.found"
EVENT_NEIGHBORHOOD_DONE = "neighborhood.expanded"
EVENT_RING_DISCOVERED   = "ring.discovered"
EVENT_HIDDEN_RELATION   = "hidden_relationship.found"
EVENT_TRAVERSAL_PATH    = "traversal.path"
EVENT_RING_MEMBER_PROMO = "ring.member_promoted"
EVENT_EVIDENCE_COLLECTED= "evidence.collected"
EVENT_REPORT_FINALIZED  = "report.finalized"
EVENT_ERROR             = "error"
