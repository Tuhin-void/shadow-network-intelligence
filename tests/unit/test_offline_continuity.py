"""Smoke tests for GraphClient OfflineFallback continuity.

These tests verify the *evaluator-resilience* contract: when TigerGraph
is unreachable, the platform's GraphClient must continue to serve real
graph data from the local CSV dataset — NOT return empty lists.

They guard against the historical regression where the orchestrator
constructed `GraphClient(config)` without a dataset, causing
investigations to silently return 0 suspects during TG outages.

No network, no TigerGraph, no pyTigerGraph calls — we exercise the
OfflineFallback path directly with a hand-crafted dataset.
"""
import sys
from pathlib import Path

_CORE = Path(__file__).resolve().parents[2] / "3_graph_intelligence_core"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from clients.graph_client import GraphClient, OfflineFallback  # noqa: E402


class _FakeDataset:
    """Minimal stand-in for ShadowDataset — only what OfflineFallback reads."""
    def __init__(self):
        self.persons = [
            {"id": "P-001", "name": "Alice Smith",    "risk_score": 80},
            {"id": "P-002", "name": "Bob Jones",      "risk_score": 50},
            {"id": "P-003", "name": "Carol Petrov",   "risk_score": 70},
        ]
        self.companies = [
            {"id": "C-001", "name": "Shell Holdings", "risk_score": 90},
            {"id": "C-002", "name": "Trading Inc",    "risk_score": 30},
        ]
        self.accounts = [
            {"id": "A-001", "owner_id": "P-001"},
            {"id": "A-002", "owner_id": "P-002"},
        ]
        self.transactions = []
        self.fraud_rings = []
        self.edges = [
            {"from_id": "P-001", "to_id": "C-001", "relationship": "OWNS"},
            {"from_id": "P-001", "to_id": "A-001", "relationship": "HAS_ACCOUNT"},
            {"from_id": "P-002", "to_id": "A-002", "relationship": "HAS_ACCOUNT"},
        ]

    def get_edges_for_entity(self, entity_id):
        return [e for e in self.edges
                if e.get("from_id") == entity_id or e.get("to_id") == entity_id]

    def get_entity_by_id(self, entity_id):
        for coll in (self.persons, self.companies, self.accounts):
            for e in coll:
                if e.get("id") == entity_id:
                    return e
        return None


def _make_offline_client():
    """Build a GraphClient that has fallen back to offline mode with a real
    dataset — without touching the network.

    We blank out the TG credentials before construction so `_init_pyTigerGraph`
    takes the `No valid TigerGraph credentials` branch and engages offline
    fallback immediately. Keeps the test suite fast and hermetic.
    """
    from configs.config import load_config
    cfg = load_config(None)
    # Empty out the cloud creds so `_init_pyTigerGraph` short-circuits.
    cfg.tigergraph.gsql_secret = ""
    cfg.tigergraph.username = ""
    cfg.tigergraph.password = ""
    ds = _FakeDataset()
    client = GraphClient(cfg, dataset=ds)
    # Defensive: in case env-resolved creds slipped through, force offline.
    if not client._offline_mode:
        client._tg_conn = None
        client._enable_offline_mode()
    return client, ds


def test_offline_fallback_initializes_from_dataset():
    """Documented contract: passing dataset → OfflineFallback indexes it."""
    client, ds = _make_offline_client()
    assert client._offline_mode is True
    assert client._offline_fallback._initialized is True
    assert len(client._offline_fallback._entity_index) >= 7  # 3+2+2 entities


def test_offline_get_vertex_returns_real_entity():
    """get_vertex must return the indexed entity in offline mode."""
    client, _ = _make_offline_client()
    v = client.get_vertex("Person", "P-001")
    assert v is not None
    assert v.get("v_id") == "P-001"
    assert v.get("type") == "Person"
    # Real attribute payload, not a stub.
    assert v.get("attributes", {}).get("risk_score") == 80


def test_offline_get_vertices_returns_real_persons():
    """get_vertices(Person) must return persons from the offline index —
    NOT an empty list. This is the bug that caused investigations to
    silently return 0 suspects."""
    client, _ = _make_offline_client()
    persons = client.get_vertices("Person", limit=10)
    assert len(persons) >= 3
    ids = {p.get("v_id") for p in persons}
    assert "P-001" in ids
    assert "P-002" in ids
    assert "P-003" in ids


def test_offline_get_vertices_returns_real_companies():
    client, _ = _make_offline_client()
    companies = client.get_vertices("Company", limit=10)
    assert len(companies) >= 2
    ids = {c.get("v_id") for c in companies}
    assert "C-001" in ids


def test_offline_get_neighbors_returns_real_edges():
    """get_neighbors must traverse the indexed edges."""
    client, _ = _make_offline_client()
    nbrs = client.get_neighbors("P-001", limit=10)
    assert "results" in nbrs
    neighbor_list = nbrs["results"][0].get("neighbors") or []
    assert len(neighbor_list) >= 2  # OWNS C-001 + HAS_ACCOUNT A-001
    targets = {n.get("v_id") for n in neighbor_list}
    assert "C-001" in targets
    assert "A-001" in targets


def test_health_check_reports_offline_mode_honestly():
    """health_check must surface mode=OFFLINE — UI relies on this for the
    degraded-mode pill."""
    client, _ = _make_offline_client()
    h = client.health_check()
    assert h["offline_mode"] is True
    assert h["mode"] == "OFFLINE"
    # Health is True (the platform is functional, just degraded).
    assert h["healthy"] is True


def test_offline_fallback_handles_dataset_without_edges():
    """Defensive: a dataset that lacks `get_edges_for_entity` shouldn't crash."""
    class _MinimalDataset:
        persons = [{"id": "P-099", "name": "Test"}]
        companies = []
        accounts = []
        transactions = []
        fraud_rings = []
    fb = OfflineFallback(_MinimalDataset())
    fb.init_from_dataset(_MinimalDataset())
    assert fb._initialized is True
    # No edges → empty edge index but entity index still populated.
    assert len(fb._edge_index) == 0
    assert "P-099" in fb._entity_index
