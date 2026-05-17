"""
InvestigationArchive — disk-backed persistent record of every investigation
the orchestrator runs.

Contract:
  • Append-only. Each investigation is one JSON file under
    `4_orchestrator_api/outputs/investigations/INV-<id>.json`.
  • Survives backend restart. Frontend can list / fetch via API.
  • Thread-safe. Single RLock around index + file writes.
  • Bounded. Keeps newest N (default 200) — older files are pruned.
  • Lossy by design. We store the report payload and key derived signals
    (suspect count, ring count, confidence, intent kind) — NOT the full
    raw graph event stream. Replay reads the persisted report and the
    standard /investigate/stream emits new events when re-run.

A deep_report (cognitive layer: swarm + reasoning) can be patched onto
an existing investigation via `attach_deep_report(investigation_id, ...)`
— the deep stream calls this after emitting deep_report.finalized.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_DIR = _REPO_ROOT / "4_orchestrator_api" / "outputs" / "investigations"

_MAX_ARCHIVED = int(os.environ.get("SNI_INVESTIGATION_ARCHIVE_MAX", "200"))


class InvestigationArchive:
    """Disk-backed investigation archive, one JSON file per investigation."""

    def __init__(self, base_dir: Optional[Path] = None,
                 max_entries: int = _MAX_ARCHIVED) -> None:
        self._dir = Path(base_dir) if base_dir else _DEFAULT_DIR
        self._dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._max_entries = max_entries

    # ── Write paths ─────────────────────────────────────────────────────

    def record_investigation(self, record: dict) -> Path:
        """Persist a new investigation record. Returns the file path.

        Required keys:
          investigation_id, session_id, query, intent, report.
        """
        inv_id = str(record.get("investigation_id") or "").strip()
        if not inv_id:
            raise ValueError("record requires investigation_id")
        record = dict(record)
        record.setdefault("created_at", time.time())
        record.setdefault("summary", self._derive_summary(record))

        path = self._path_for(inv_id)
        with self._lock:
            path.write_text(json.dumps(record, indent=2, default=str))
            self._prune_locked()
        return path

    def attach_deep_report(self, investigation_id: str, deep_report: dict) -> bool:
        """Patch a deep_report onto an existing archived investigation.
        Returns True if the file existed and was updated."""
        with self._lock:
            path = self._path_for(investigation_id)
            if not path.exists():
                return False
            try:
                rec = json.loads(path.read_text())
            except Exception:
                return False
            rec["deep_report"] = deep_report
            rec["summary"] = self._derive_summary(rec)
            path.write_text(json.dumps(rec, indent=2, default=str))
            return True

    # ── Read paths ──────────────────────────────────────────────────────

    def list(self, limit: int = 50, intent_kind: Optional[str] = None) -> list[dict]:
        """Return summaries newest-first. Each summary is enough to render
        a Recent Investigations row without loading the full report."""
        with self._lock:
            files = sorted(self._dir.glob("*.json"),
                           key=lambda p: p.stat().st_mtime, reverse=True)
        out: list[dict] = []
        for p in files:
            if len(out) >= limit:
                break
            try:
                rec = json.loads(p.read_text())
            except Exception:
                continue
            if intent_kind and (rec.get("intent") or {}).get("kind") != intent_kind:
                continue
            out.append(self._summary_row(rec, file_path=p))
        return out

    def get(self, investigation_id: str) -> Optional[dict]:
        """Return the full archived record, or None if missing."""
        with self._lock:
            path = self._path_for(investigation_id)
            if not path.exists():
                return None
            try:
                return json.loads(path.read_text())
            except Exception:
                return None

    def delete(self, investigation_id: str) -> bool:
        with self._lock:
            path = self._path_for(investigation_id)
            if not path.exists():
                return False
            try:
                path.unlink()
                return True
            except Exception:
                return False

    def stats(self) -> dict:
        with self._lock:
            files = list(self._dir.glob("*.json"))
        return {
            "directory":  str(self._dir.relative_to(_REPO_ROOT)),
            "count":      len(files),
            "max_entries": self._max_entries,
        }

    # ── Internal ────────────────────────────────────────────────────────

    def _path_for(self, investigation_id: str) -> Path:
        safe = "".join(c for c in investigation_id if c.isalnum() or c in "._-")
        return self._dir / f"{safe}.json"

    def _prune_locked(self) -> None:
        files = sorted(self._dir.glob("*.json"),
                       key=lambda p: p.stat().st_mtime, reverse=True)
        for old in files[self._max_entries:]:
            try:
                old.unlink()
            except Exception:
                pass

    def _summary_row(self, rec: dict, *, file_path: Optional[Path] = None) -> dict:
        rep = rec.get("report") or {}
        intent = rec.get("intent") or {}
        sigs = rep.get("structural_signals") or {}
        summary = rec.get("summary") or self._derive_summary(rec)
        env = rec.get("environment") or {}
        return {
            "investigation_id": rec.get("investigation_id"),
            "session_id":       rec.get("session_id"),
            "created_at":       rec.get("created_at"),
            "query":            rec.get("query"),
            "intent_kind":      intent.get("kind"),
            "intent_display":   intent.get("display_name"),
            "intent_confidence": intent.get("confidence"),
            "suspect_count":    summary.get("suspect_count"),
            "ring_count":       summary.get("ring_count"),
            "neighbor_count":   sigs.get("neighbor_count"),
            "evidence_count":   sigs.get("evidence_count"),
            "fraud_degree_sum": sigs.get("fraud_degree_sum"),
            "ring_touch_sum":   sigs.get("ring_touch_sum"),
            "elapsed_ms":       rec.get("elapsed_ms"),
            "offline_mode":     rec.get("offline_mode"),
            "has_deep_report":  bool(rec.get("deep_report")),
            "deep_confidence":  summary.get("deep_confidence"),
            # Environment snapshot captured at investigation time. UI uses
            # this to warn when a replay would run against a different graph.
            "env_total_vertices": env.get("total_vertices"),
            "env_kind":          env.get("environment_kind"),
            "env_online":        env.get("tigergraph_online"),
            "size_bytes":       (file_path.stat().st_size if file_path else None),
        }

    def _derive_summary(self, rec: dict) -> dict:
        rep = rec.get("report") or {}
        sigs = rep.get("structural_signals") or {}
        deep = rec.get("deep_report") or {}
        reasoning = (deep.get("reasoning") or {}) if isinstance(deep, dict) else {}
        return {
            "suspect_count":   len(rep.get("suspects") or []),
            "ring_count":      len(rep.get("ring_connections") or []),
            "evidence_count":  sigs.get("evidence_count", 0),
            "deep_confidence": reasoning.get("overall_confidence"),
        }


# Singleton
_singleton: Optional[InvestigationArchive] = None


def get_archive() -> InvestigationArchive:
    global _singleton
    if _singleton is None:
        _singleton = InvestigationArchive()
    return _singleton
