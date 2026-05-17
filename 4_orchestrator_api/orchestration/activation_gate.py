"""Cross-router helper: enforce the operator-controlled environment
activation gate on routes that consume the live intelligence environment.

When `EnvironmentActivation.kind == "empty"`, the platform's UX contract
is "no environment activated until the operator explicitly Launches one".
Routes that mutate or read live graph state should respect this contract
so the UI never shows a contradictory "the environment is empty BUT here
are some suspects from the graph" experience.

Routes that DO NOT call this gate (intentionally):
  • /ingest/environment, /ingest/activation       — they describe state
  • /ingest/activate, /ingest/clear, /ingest/sample — they MUTATE state
  • /ingest/upload, /ingest/promote, /ingest/promote-ecosystem
                                                  — promote IS the action
                                                    that flips activation
  • /benchmark/summary, /benchmark/quantitative,
    /benchmark/adversarial, /benchmark/runs/{id}  — read-only artifacts,
                                                    always available for
                                                    evidence inspection
  • /investigations, /investigations/{id}         — archive always readable
  • /orchestrator/intent                          — sub-ms pure-python
                                                    classifier, no graph
  • /orchestrator/status, /health, /orchestrator/reconnect
                                                  — operational telemetry

Routes that DO call this gate:
  • /investigate, /investigate/stream             — live retrieval
  • /investigate/deep/stream                      — live retrieval + swarm
  • /benchmark/run, /benchmark/ad-hoc, /benchmark/run/stream
                                                  — live execution
"""
from __future__ import annotations

from typing import Optional

from fastapi import HTTPException

from .activation import get_activation


def require_activation(operation: str = "investigation") -> None:
    """Raise HTTPException(409) when no environment is activated.

    The response body is structured (not free text) so the dashboard can
    render an operator-friendly "Launch first" affordance rather than a
    generic error banner.

    Args:
        operation: short label describing what was rejected — surfaced
            in the `operation` field of the error body.
    """
    act = get_activation().current()
    if act.kind == "empty":
        # Structured 409 — the UI's error handler maps this to a
        # "Launch Sample Ecosystem" CTA rather than the red error toast.
        raise HTTPException(
            status_code=409,
            detail={
                "error":           "environment_not_activated",
                "operation":       operation,
                "activation_kind": act.kind,
                "message": (
                    "No environment is activated. The operator must "
                    "explicitly launch a sample ecosystem or promote an "
                    "uploaded ecosystem before running live investigations "
                    "or benchmarks."
                ),
                "next_steps": [
                    "Open /sources in the dashboard and click "
                    "'Launch Sample Fraud Ecosystem'",
                    "OR POST /api/v1/ingest/sample?profile=small",
                    "OR upload + promote a CSV ecosystem via /api/v1/ingest/upload "
                    "and /api/v1/ingest/promote/{upload_id}",
                    "OR flip the activation gate directly: "
                    "POST /api/v1/ingest/activate {kind: 'sample'} "
                    "(only valid if data already exists in TG from a prior session)",
                ],
                "read_only_endpoints_still_available": [
                    "/api/v1/benchmark/summary",
                    "/api/v1/benchmark/quantitative",
                    "/api/v1/benchmark/runs",
                    "/api/v1/benchmark/runs/{run_id}",
                    "/api/v1/investigations",
                    "/api/v1/investigations/{investigation_id}",
                    "/api/v1/ingest/environment",
                    "/api/v1/orchestrator/intent",
                    "/api/v1/health",
                ],
            },
        )


def is_activated() -> bool:
    """Convenience: True when an environment is activated. Callers that
    want to softly degrade (return a stub response instead of raising)
    can use this instead of `require_activation`."""
    return get_activation().current().kind != "empty"


def current_activation_dict() -> dict:
    """Return the current activation record as a plain dict. Useful when
    a route wants to embed activation metadata in its successful response."""
    return get_activation().current().to_dict()
