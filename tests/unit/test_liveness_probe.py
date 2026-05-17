"""Smoke tests for GraphClient.probe_liveness — the truthful-state probe.

The platform's lazy `_offline_mode` flag only flips when a graph call
fails. `probe_liveness` is the active probe that lets `/orchestrator/status`,
`/ingest/environment`, and `/health?probe=1` detect a paused TG within
seconds, instead of waiting for the next investigation to time out.

These tests cover:
  • probe returns False when no connection exists (clean offline)
  • probe caches results for max_age_s seconds
  • probe with max_age_s=0 forces a fresh check
  • probe failure flips _offline_mode to True (sync with rest of fallback)
  • probe success on a previously-offline client flips back to False
  • thread-bounded timeout — probe doesn't hang the caller
"""
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_CORE = Path(__file__).resolve().parents[2] / "3_graph_intelligence_core"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from clients.graph_client import GraphClient  # noqa: E402


def _build_client(echo_fn=None):
    """Construct a GraphClient with a mocked pyTigerGraph connection so
    probe_liveness can exercise echo() without a real network."""
    from configs.config import load_config
    cfg = load_config(None)
    # Blank creds so __init__ takes the no-credentials offline path,
    # then we manually inject a mock connection.
    cfg.tigergraph.gsql_secret = ""
    cfg.tigergraph.username = ""
    cfg.tigergraph.password = ""
    client = GraphClient(cfg, dataset=None)
    # Reset to "online" with a mocked connection.
    client._offline_mode = False
    client._tg_conn = MagicMock()
    if echo_fn is None:
        client._tg_conn.echo = MagicMock(return_value="Hello GSQL")
    else:
        client._tg_conn.echo = MagicMock(side_effect=echo_fn)
    # Clear probe cache for clean test state.
    client._last_probe_at = 0.0
    client._last_probe_result = None
    return client


def test_probe_returns_true_when_echo_succeeds():
    client = _build_client()
    assert client.probe_liveness() is True
    assert client._offline_mode is False
    assert client._tg_conn.echo.call_count == 1


def test_probe_returns_false_when_no_connection():
    client = _build_client()
    client._tg_conn = None
    assert client.probe_liveness() is False
    # Probe with no connection means we're definitionally offline.
    assert client._offline_mode is True


def test_probe_failure_flips_offline_flag():
    client = _build_client(echo_fn=lambda: (_ for _ in ()).throw(
        ConnectionError("workspace paused")
    ))
    assert client._offline_mode is False  # start state
    result = client.probe_liveness()
    assert result is False
    assert client._offline_mode is True   # flipped


def test_probe_success_triggers_full_reconnect_when_recovering():
    """Documented contract: when probe succeeds while we were previously
    offline, the probe MUST trigger a full reconnect (not just flip the
    flag). A successful echo can coexist with a stale auth-token state,
    so we always rebuild the pyTigerGraph connection on recovery.

    With a mock conn, reconnect fails — the test asserts the recovery
    path was attempted (probe returned True, reconnect was called) even
    though the mock makes the reconnect itself fail."""
    client = _build_client()
    client._offline_mode = True
    client._last_probe_at = 0.0
    client._last_probe_result = None
    # Track whether reconnect_if_offline was called.
    original_reconnect = client.reconnect_if_offline
    reconnect_calls = []
    def _spy(**kwargs):
        reconnect_calls.append(kwargs)
        return original_reconnect(**kwargs)
    client.reconnect_if_offline = _spy  # type: ignore[assignment]

    result = client.probe_liveness(max_age_s=0)
    assert result is True, "probe returned ok"
    assert len(reconnect_calls) == 1, (
        "probe did not call reconnect_if_offline on recovery"
    )
    # min_interval_s=0 — the probe just confirmed reachability, so no cooldown.
    assert reconnect_calls[0].get("min_interval_s") == 0


def test_probe_caches_result_within_max_age():
    client = _build_client()
    r1 = client.probe_liveness(max_age_s=10.0)
    r2 = client.probe_liveness(max_age_s=10.0)
    r3 = client.probe_liveness(max_age_s=10.0)
    assert r1 is r2 is r3 is True
    # echo should have been called once — subsequent calls return the
    # cached result.
    assert client._tg_conn.echo.call_count == 1


def test_probe_force_fresh_with_zero_max_age():
    client = _build_client()
    client.probe_liveness(max_age_s=10.0)
    client.probe_liveness(max_age_s=0)
    client.probe_liveness(max_age_s=0)
    assert client._tg_conn.echo.call_count == 3


def test_probe_timeout_returns_false_within_bound():
    """probe_liveness must bound execution by `timeout_s` even when the
    underlying echo() blocks indefinitely. Without this, a paused TG
    would hang the orchestrator status endpoint."""

    def _hang():
        time.sleep(10)
        return "never reached"

    client = _build_client(echo_fn=_hang)
    t0 = time.perf_counter()
    result = client.probe_liveness(max_age_s=0, timeout_s=0.5)
    elapsed = time.perf_counter() - t0
    assert result is False
    # 0.5s timeout + ThreadPoolExecutor overhead. Allow generous CI slack.
    assert elapsed < 2.0, f"probe took {elapsed:.2f}s (expected <2s)"
    assert client._offline_mode is True


def test_repeated_probes_dont_repeatedly_log_offline():
    """When already offline, a failing probe should NOT keep calling
    _enable_offline_mode (which logs the loud banner). The banner should
    fire ONCE on the transition, not on every subsequent probe."""
    client = _build_client(echo_fn=lambda: (_ for _ in ()).throw(
        ConnectionError("paused")
    ))
    client.probe_liveness(max_age_s=0)
    assert client._offline_mode is True
    # Track _enable_offline_mode calls.
    original = client._enable_offline_mode
    call_count = [0]
    def _wrapped():
        call_count[0] += 1
        return original()
    client._enable_offline_mode = _wrapped  # type: ignore[assignment]
    # Force another fresh probe — still failing.
    client.probe_liveness(max_age_s=0)
    client.probe_liveness(max_age_s=0)
    # _enable_offline_mode should NOT be called again (we're already offline).
    assert call_count[0] == 0, (
        f"_enable_offline_mode called {call_count[0]} extra times — "
        "should be 0 when already offline"
    )
