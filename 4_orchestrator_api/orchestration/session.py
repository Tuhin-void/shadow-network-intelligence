"""
Investigation session — in-memory, single-process state.

A session tracks:
  - which entities have been touched across queries
  - accumulated evidence across queries (capped)
  - the chain of investigation reports

This is intentionally lightweight — no persistence layer, no database.
Sessions live for the process lifetime. For production multi-instance
deployment, a Redis backend can be plugged in via the same interface.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class InvestigationSession:
    id: str
    created_at: float = field(default_factory=time.time)
    last_query_at: Optional[float] = None
    queries_run: int = 0
    # Cumulative set of entity IDs ever surfaced in this session.
    touched_entity_ids: set[str] = field(default_factory=set)
    # Cumulative set of fraud rings touched.
    touched_rings: set[str] = field(default_factory=set)
    # Last N reports (capped to 10).
    reports: list[dict] = field(default_factory=list)
    title: str = ""
    notes: str = ""

    def to_summary(self) -> dict:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "last_query_at": self.last_query_at,
            "queries_run": self.queries_run,
            "touched_entity_count": len(self.touched_entity_ids),
            "touched_rings": sorted(self.touched_rings),
            "report_count": len(self.reports),
            "title": self.title,
        }


class SessionStore:
    """In-memory session store. Process-local."""

    _MAX_REPORTS_PER_SESSION = 10

    def __init__(self) -> None:
        self._sessions: dict[str, InvestigationSession] = {}

    def open(self, title: str = "") -> InvestigationSession:
        sid = f"INV-{uuid.uuid4().hex[:10]}"
        sess = InvestigationSession(id=sid, title=title or f"Investigation {sid}")
        self._sessions[sid] = sess
        return sess

    def get(self, session_id: str) -> Optional[InvestigationSession]:
        return self._sessions.get(session_id)

    def list(self) -> list[dict]:
        return [s.to_summary() for s in self._sessions.values()]

    def record_report(self, session_id: str, report: dict) -> None:
        """Append a finalized report; update touched-entity bookkeeping."""
        sess = self._sessions.get(session_id)
        if not sess:
            return
        sess.queries_run += 1
        sess.last_query_at = time.time()
        for ent in report.get("suspects", []):
            v_id = ent.get("v_id")
            if v_id:
                sess.touched_entity_ids.add(v_id)
        for rel in report.get("ring_connections", []):
            via = rel.get("via")
            if via and via.startswith("FR-"):
                sess.touched_rings.add(via)
        # Bounded history.
        sess.reports.append(report)
        if len(sess.reports) > self._MAX_REPORTS_PER_SESSION:
            sess.reports = sess.reports[-self._MAX_REPORTS_PER_SESSION:]

    def delete(self, session_id: str) -> bool:
        return self._sessions.pop(session_id, None) is not None
