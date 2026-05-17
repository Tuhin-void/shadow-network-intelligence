"""Smoke tests for EntityCentricRetriever._topology_rerank.

These tests use a hand-crafted in-process FakeGraphClient that returns
deterministic neighbor sets. They verify the actual scoring contract:
  • ring-touching entities outrank non-ring entities at equal base score
  • higher fraud_degree outranks lower fraud_degree at equal base score
  • the rerank explanation reflects the structural features
  • risk_score INT 0-100 is correctly rescaled to 0-1
  • candidates with zero graph signal still get a stable score

No TigerGraph, no network — pure-Python feature scoring.
"""
import sys
from pathlib import Path

# Ensure the core package is importable.
_CORE = Path(__file__).resolve().parents[2] / "3_graph_intelligence_core"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from retrievers.entity_centric import EntityCentricRetriever, EntityMatch  # noqa: E402


class FakeGraphClient:
    """In-process stand-in. Returns canned neighbor sets per entity ID."""

    def __init__(self, neighbors_by_id: dict):
        self._neighbors_by_id = neighbors_by_id

    def get_neighbors(self, v_id, vertex_type="", edge_type="", limit=50):
        return {"results": [{"neighbors": self._neighbors_by_id.get(v_id, [])}]}

    def get_vertex(self, vertex_type, v_id):
        return None

    def get_vertices(self, vtype, limit=100):
        return []


def _make_retriever(neighbors_by_id):
    client = FakeGraphClient(neighbors_by_id)
    # No embedder — we are testing the rerank, not the semantic fallback.
    return EntityCentricRetriever(client, embedder=None)


def test_ring_touching_entity_outranks_isolated_entity():
    neighbors = {
        # P-001 touches one fraud ring + has 1 ring-edge
        "P-001": [
            {"v_id": "FR-001", "type": "FraudRing",
             "edge_type": "PERSON_MEMBER_OF_RING", "risk_score": 80},
        ],
        # P-002 has no fraud-relevant neighbors
        "P-002": [],
    }
    r = _make_retriever(neighbors)
    cands = [
        EntityMatch(v_id="P-001", vertex_type="Person", name="P1", score=0.5),
        EntityMatch(v_id="P-002", vertex_type="Person", name="P2", score=0.5),
    ]
    out = r._topology_rerank(cands, top_k=2)
    assert out[0].v_id == "P-001", (
        f"ring-touching P-001 should outrank P-002, got {out[0].v_id}"
    )
    assert out[0].ring_touch_count == 1
    assert "ring" in out[0].rerank_explanation.lower()


def test_higher_fraud_degree_outranks_lower():
    neighbors = {
        # P-A has 5 fraud-relevant edges
        "P-A": [
            {"v_id": f"P-{i:03d}", "type": "Person",
             "edge_type": "SHARES_DEVICE_WITH", "risk_score": 0}
            for i in range(5)
        ],
        # P-B has 1 fraud-relevant edge
        "P-B": [
            {"v_id": "P-099", "type": "Person",
             "edge_type": "SHARES_DEVICE_WITH", "risk_score": 0},
        ],
    }
    r = _make_retriever(neighbors)
    cands = [
        EntityMatch(v_id="P-A", vertex_type="Person", name="A", score=0.5),
        EntityMatch(v_id="P-B", vertex_type="Person", name="B", score=0.5),
    ]
    out = r._topology_rerank(cands, top_k=2)
    assert out[0].v_id == "P-A"
    assert out[0].fraud_degree == 5


def test_raw_risk_int_rescaling():
    """risk_score=80 (INT 0-100) must be rescaled to 0.80 in the rerank."""
    r = _make_retriever({"P-1": []})
    cand = [EntityMatch(v_id="P-1", vertex_type="Person", name="P",
                        score=0.0, risk_score=80)]
    out = r._topology_rerank(cand, top_k=1)
    # raw_risk gets weight 0.20 → contribution = 0.20 * 0.80 = 0.16
    # base_score = 0, neighbor_risk = 0, ring_touch = 0, degree = 0
    # → final score ≈ 0.16
    assert 0.14 < out[0].score < 0.18, f"got {out[0].score}"


def test_no_graph_signal_yields_explanation():
    """Documented contract: zero-signal candidates get 'no graph signal'."""
    r = _make_retriever({"P-X": []})
    cand = [EntityMatch(v_id="P-X", vertex_type="Person", name="X", score=0.5)]
    out = r._topology_rerank(cand, top_k=1)
    assert out[0].rerank_explanation == "no graph signal"


def test_top_k_caps_the_rerank_output():
    r = _make_retriever({f"P-{i}": [] for i in range(5)})
    cands = [EntityMatch(v_id=f"P-{i}", vertex_type="Person", name=str(i),
                          score=0.1 * i) for i in range(5)]
    out = r._topology_rerank(cands, top_k=3)
    assert len(out) == 3
    # Higher base_score wins when other signals are equal.
    assert out[0].v_id == "P-4"
