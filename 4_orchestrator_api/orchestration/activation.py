"""EnvironmentActivation — controlled lifecycle for which intelligence
environment the operator has explicitly activated.

This is a UX gate, not a physical scope:
  • The platform has ONE live TigerGraph graph. Sample data and promoted
    uploads merge by vertex ID — there is no namespace isolation.
  • Activation tracks what the OPERATOR has activated and lets the UI
    present an honest "empty until launched" experience instead of
    auto-revealing whatever happens to be in TG after a prior session.

States:
  • "empty"    — no environment activated. /ingest/environment shows
                 0 vertices and all readiness gates closed.
  • "sample"   — operator has run /ingest/sample successfully.
  • "uploaded" — operator has promoted at least one upload.
  • "hybrid"   — both sample + uploads are active (set automatically when
                 a sample is launched after uploads, or vice-versa).
  • "offline"  — TigerGraph is unreachable; environment is effectively the
                 OfflineFallback view. Not operator-controlled.

Persistence: state is written to
`4_orchestrator_api/outputs/environment_state.json`. Survives restart so
a paused-and-resumed orchestrator returns to the last activation.

The full register of operational disclosures lives in
`10_research/09_failure_cases.md` — this module enforces the
"environment activation is intentional, not implicit" contract
documented there.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Literal, Optional

logger = logging.getLogger(__name__)

# Persistence location — same parent dir as the investigation archive.
_STATE_DIR = Path(__file__).resolve().parent.parent / "outputs"
_STATE_FILE = _STATE_DIR / "environment_state.json"


ActivationKind = Literal["empty", "sample", "uploaded", "hybrid", "offline"]
_VALID_KINDS: tuple[str, ...] = ("empty", "sample", "uploaded", "hybrid", "offline")


@dataclass
class ActivationRecord:
    kind: ActivationKind = "empty"
    activated_at: float = 0.0
    activated_by: str = ""           # short reason — "operator_launch", "auto_post_promote", etc.
    profile: Optional[str] = None    # which dataset profile (for sample/hybrid)
    label: str = "no environment activated"
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class EnvironmentActivation:
    """Process-singleton activation tracker. Thread-safe; disk-persisted."""

    def __init__(self, persist: bool = True) -> None:
        self._lock = threading.Lock()
        self._record = ActivationRecord()
        self._persist = persist
        if persist:
            self._load_from_disk()

    # ── State accessors ─────────────────────────────────────────────────

    def current(self) -> ActivationRecord:
        with self._lock:
            return ActivationRecord(**asdict(self._record))

    def is_active(self) -> bool:
        """True iff anything has been activated (i.e., kind != 'empty')."""
        with self._lock:
            return self._record.kind != "empty"

    def kind(self) -> str:
        with self._lock:
            return self._record.kind

    # ── Mutators ────────────────────────────────────────────────────────

    def activate(
        self,
        kind: ActivationKind,
        *,
        by: str = "operator",
        profile: Optional[str] = None,
        label: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> ActivationRecord:
        """Explicit activation. Caller-supplied `kind` MUST be in _VALID_KINDS.

        Hybrid is computed automatically — callers requesting `sample` while
        the current state is `uploaded` (or vice-versa) get promoted to
        `hybrid` so the UI surfaces the merged reality.
        """
        if kind not in _VALID_KINDS:
            raise ValueError(f"invalid activation kind: {kind!r} "
                             f"(must be one of {_VALID_KINDS})")
        with self._lock:
            prev = self._record.kind
            # Auto-promote to hybrid when sample + upload coexist.
            if kind == "sample" and prev == "uploaded":
                effective = "hybrid"
            elif kind == "uploaded" and prev == "sample":
                effective = "hybrid"
            elif kind == "uploaded" and prev == "hybrid":
                effective = "hybrid"
            elif kind == "sample" and prev == "hybrid":
                effective = "hybrid"
            else:
                effective = kind

            self._record = ActivationRecord(
                kind=effective,  # type: ignore[arg-type]
                activated_at=time.time(),
                activated_by=by,
                profile=profile or self._record.profile,
                label=label or _default_label(effective, profile),
                details=details or {},
            )
            self._persist_to_disk()
            logger.info(
                "EnvironmentActivation: %s -> %s (by=%s, profile=%s)",
                prev, effective, by, profile,
            )
            return ActivationRecord(**asdict(self._record))

    def clear(self, *, by: str = "operator") -> ActivationRecord:
        """Return to the empty state. Does NOT mutate TigerGraph — only
        flips the operator-facing activation gate. The underlying live
        graph retains everything (sample + uploads); operators can
        re-activate at any time."""
        with self._lock:
            self._record = ActivationRecord(
                kind="empty",
                activated_at=time.time(),
                activated_by=by,
                profile=None,
                label="no environment activated",
                details={},
            )
            self._persist_to_disk()
            logger.info("EnvironmentActivation: cleared by %s", by)
            return ActivationRecord(**asdict(self._record))

    # ── Persistence ─────────────────────────────────────────────────────

    def _persist_to_disk(self) -> None:
        if not self._persist:
            return
        try:
            _STATE_DIR.mkdir(parents=True, exist_ok=True)
            _STATE_FILE.write_text(json.dumps(self._record.to_dict(), indent=2))
        except Exception as e:
            logger.warning("EnvironmentActivation: persist failed: %s", e)

    def _load_from_disk(self) -> None:
        # Override path: SNI_ENV_ACTIVATION_RESET=1 forces a fresh empty
        # state at boot regardless of what's on disk. Useful for demos
        # that want a clean "operator must launch" landing.
        if os.environ.get("SNI_ENV_ACTIVATION_RESET") == "1":
            logger.info(
                "EnvironmentActivation: SNI_ENV_ACTIVATION_RESET=1 — "
                "starting empty regardless of persisted state."
            )
            return
        if not _STATE_FILE.exists():
            return
        try:
            raw = json.loads(_STATE_FILE.read_text())
            # Validate kind — refuse to load a corrupt state file.
            if raw.get("kind") in _VALID_KINDS:
                self._record = ActivationRecord(
                    kind=raw.get("kind"),
                    activated_at=float(raw.get("activated_at") or 0.0),
                    activated_by=str(raw.get("activated_by") or ""),
                    profile=raw.get("profile"),
                    label=str(raw.get("label") or _default_label(
                        raw.get("kind"), raw.get("profile"))),
                    details=raw.get("details") or {},
                )
                logger.info(
                    "EnvironmentActivation: restored kind=%s from disk",
                    self._record.kind,
                )
        except Exception as e:
            logger.warning("EnvironmentActivation: load failed: %s", e)


def _default_label(kind: str, profile: Optional[str]) -> str:
    if kind == "empty":
        return "no environment activated"
    if kind == "sample":
        return f"sample fraud ecosystem ({profile or 'small'})"
    if kind == "uploaded":
        return "operator-uploaded ecosystem"
    if kind == "hybrid":
        return f"hybrid · sample + uploads ({profile or 'small'})"
    if kind == "offline":
        return "offline · local fallback"
    return kind


# ── Process singleton ───────────────────────────────────────────────────

_singleton: Optional[EnvironmentActivation] = None
_singleton_lock = threading.Lock()


def get_activation() -> EnvironmentActivation:
    global _singleton
    if _singleton is None:
        with _singleton_lock:
            if _singleton is None:
                _singleton = EnvironmentActivation(persist=True)
    return _singleton


# Test helper — never used in production code paths.
def _reset_singleton_for_tests() -> None:
    global _singleton
    with _singleton_lock:
        _singleton = None
