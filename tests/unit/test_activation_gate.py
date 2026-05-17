"""Smoke tests for the activation gate.

Locks in the contract that live retrieval / live benchmark endpoints
reject with HTTP 409 (and a structured operator hint) when no
environment has been activated, while read-only artifact endpoints
remain available regardless.
"""
import importlib
from pathlib import Path

import pytest
from fastapi import HTTPException


def _fresh_activation(tmp_path: Path):
    """Reload the activation module with state file in a tmp dir so the
    test doesn't touch the real persisted environment."""
    mod = importlib.import_module("4_orchestrator_api.orchestration.activation")
    importlib.reload(mod)
    mod._STATE_DIR = tmp_path
    mod._STATE_FILE = tmp_path / "environment_state.json"
    mod._reset_singleton_for_tests()
    return mod


def _fresh_gate(tmp_path: Path):
    """Reload activation_gate AFTER activation has been freshly seeded."""
    _fresh_activation(tmp_path)
    gate = importlib.import_module("4_orchestrator_api.orchestration.activation_gate")
    importlib.reload(gate)
    return gate


def test_gate_raises_409_when_empty(tmp_path):
    gate = _fresh_gate(tmp_path)
    with pytest.raises(HTTPException) as exc_info:
        gate.require_activation(operation="investigation")
    err = exc_info.value
    assert err.status_code == 409
    assert isinstance(err.detail, dict)
    assert err.detail["error"] == "environment_not_activated"
    assert err.detail["operation"] == "investigation"
    assert err.detail["activation_kind"] == "empty"
    # Contract: next_steps must be a non-empty list (operator hint).
    assert isinstance(err.detail["next_steps"], list)
    assert len(err.detail["next_steps"]) >= 3
    # Contract: read-only endpoints surfaced so evaluator can fall back.
    assert "/api/v1/benchmark/summary" in err.detail["read_only_endpoints_still_available"]


def test_gate_passes_after_sample_activation(tmp_path):
    gate = _fresh_gate(tmp_path)
    act_mod = importlib.import_module("4_orchestrator_api.orchestration.activation")
    act_mod.get_activation().activate("sample", profile="small")
    # Re-import gate so it sees the new singleton if any caching crept in.
    importlib.reload(gate)
    # Should NOT raise.
    gate.require_activation(operation="investigation")


def test_gate_passes_after_uploaded_activation(tmp_path):
    gate = _fresh_gate(tmp_path)
    act_mod = importlib.import_module("4_orchestrator_api.orchestration.activation")
    act_mod.get_activation().activate("uploaded", by="test")
    importlib.reload(gate)
    gate.require_activation(operation="benchmark_run")


def test_gate_passes_in_hybrid_state(tmp_path):
    gate = _fresh_gate(tmp_path)
    act_mod = importlib.import_module("4_orchestrator_api.orchestration.activation")
    act_mod.get_activation().activate("sample", profile="small")
    act_mod.get_activation().activate("uploaded")  # → hybrid
    importlib.reload(gate)
    gate.require_activation(operation="benchmark_ad_hoc")


def test_gate_re_blocks_after_clear(tmp_path):
    gate = _fresh_gate(tmp_path)
    act_mod = importlib.import_module("4_orchestrator_api.orchestration.activation")
    act_mod.get_activation().activate("sample", profile="small")
    importlib.reload(gate)
    gate.require_activation(operation="investigation")  # OK
    act_mod.get_activation().clear()
    importlib.reload(gate)
    with pytest.raises(HTTPException) as exc_info:
        gate.require_activation(operation="investigation")
    assert exc_info.value.status_code == 409


def test_is_activated_reflects_current_state(tmp_path):
    gate = _fresh_gate(tmp_path)
    assert gate.is_activated() is False
    act_mod = importlib.import_module("4_orchestrator_api.orchestration.activation")
    act_mod.get_activation().activate("sample", profile="small")
    importlib.reload(gate)
    assert gate.is_activated() is True


def test_current_activation_dict_returns_record(tmp_path):
    gate = _fresh_gate(tmp_path)
    act_mod = importlib.import_module("4_orchestrator_api.orchestration.activation")
    act_mod.get_activation().activate("sample", profile="small", by="operator")
    importlib.reload(gate)
    d = gate.current_activation_dict()
    assert d["kind"] == "sample"
    assert d["profile"] == "small"
    assert d["activated_by"] == "operator"
