"""Smoke tests for EnvironmentActivation.

These tests lock in the explicit-activation contract:
  • Default boot = "empty" (operator must Launch before anything shows)
  • activate("sample") then activate("uploaded") → auto-promotes to "hybrid"
  • clear() returns to empty without raising
  • Persisted state survives a "restart" (new instance reads the file)
  • SNI_ENV_ACTIVATION_RESET=1 forces empty regardless of disk
  • Invalid kinds raise ValueError (the API surfaces this as 400)

No network, no orchestrator boot — pure in-process logic.
"""
import os
import tempfile
import importlib
from pathlib import Path

# Reload the module fresh per test so each test gets a clean singleton.
import sys


def _fresh_activation_module(tmp_dir: Path):
    """Reload the activation module with _STATE_FILE pointed at a tmp dir
    so tests don't touch the real outputs/ directory."""
    mod = importlib.import_module("4_orchestrator_api.orchestration.activation")
    importlib.reload(mod)
    mod._STATE_DIR = tmp_dir
    mod._STATE_FILE = tmp_dir / "environment_state.json"
    mod._reset_singleton_for_tests()
    return mod


def test_default_state_is_empty(tmp_path):
    mod = _fresh_activation_module(tmp_path)
    rec = mod.get_activation().current()
    assert rec.kind == "empty"
    assert rec.label == "no environment activated"
    assert mod.get_activation().is_active() is False


def test_explicit_sample_activation(tmp_path):
    mod = _fresh_activation_module(tmp_path)
    rec = mod.get_activation().activate("sample",
                                        by="operator_launch",
                                        profile="small")
    assert rec.kind == "sample"
    assert rec.profile == "small"
    assert "sample" in rec.label
    assert mod.get_activation().is_active() is True


def test_sample_then_upload_auto_promotes_to_hybrid(tmp_path):
    mod = _fresh_activation_module(tmp_path)
    mod.get_activation().activate("sample", profile="small")
    rec = mod.get_activation().activate("uploaded",
                                        by="auto_post_promote")
    assert rec.kind == "hybrid"
    assert mod.get_activation().kind() == "hybrid"


def test_upload_then_sample_auto_promotes_to_hybrid(tmp_path):
    mod = _fresh_activation_module(tmp_path)
    mod.get_activation().activate("uploaded")
    rec = mod.get_activation().activate("sample", profile="small")
    assert rec.kind == "hybrid"


def test_clear_returns_to_empty(tmp_path):
    mod = _fresh_activation_module(tmp_path)
    mod.get_activation().activate("sample", profile="small")
    rec = mod.get_activation().clear(by="test")
    assert rec.kind == "empty"
    assert mod.get_activation().is_active() is False


def test_persistence_round_trip(tmp_path):
    """First instance activates sample; second instance reads it from disk."""
    mod = _fresh_activation_module(tmp_path)
    mod.get_activation().activate("sample", profile="small")
    # Drop singleton + load again (simulates restart) — same on-disk file.
    mod._reset_singleton_for_tests()
    rec = mod.get_activation().current()
    assert rec.kind == "sample"
    assert rec.profile == "small"


def test_reset_env_var_forces_empty_on_load(tmp_path):
    """SNI_ENV_ACTIVATION_RESET=1 forces a fresh empty state at load time."""
    mod = _fresh_activation_module(tmp_path)
    mod.get_activation().activate("sample", profile="small")
    mod._reset_singleton_for_tests()
    os.environ["SNI_ENV_ACTIVATION_RESET"] = "1"
    try:
        rec = mod.get_activation().current()
        assert rec.kind == "empty"
    finally:
        del os.environ["SNI_ENV_ACTIVATION_RESET"]


def test_invalid_kind_raises(tmp_path):
    mod = _fresh_activation_module(tmp_path)
    import pytest
    with pytest.raises(ValueError):
        mod.get_activation().activate("garbage")


def test_singleton_returns_same_instance(tmp_path):
    mod = _fresh_activation_module(tmp_path)
    a = mod.get_activation()
    b = mod.get_activation()
    assert a is b
