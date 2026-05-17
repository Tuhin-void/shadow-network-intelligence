"""Smoke tests for the schema source of truth.

`3_graph_intelligence_core/validation/schema_def.py` declares the canonical
vertices + edges. This test locks in:
  • the documented 7-vertex / 19-edge surface
  • per-ring-type explicit membership edges (no polymorphic edges)
  • deprecated edges (`MEMBER_OF_RING`, `CONNECTED_TO_RING`, `PART_OF`)
    are NOT defined
  • PRIORITY_EDGES + RING_MEMBERSHIP_EDGES stay consistent with EDGE_TYPES
"""
import sys
from pathlib import Path

_CORE = Path(__file__).resolve().parents[2] / "3_graph_intelligence_core"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from validation import schema_def as sd  # noqa: E402


def test_documented_vertex_count():
    assert len(sd.VERTEX_TYPES) == 7
    assert {v.name for v in sd.VERTEX_TYPES} == {
        "Person", "Company", "Account", "Address",
        "Device", "Transaction", "FraudRing",
    }


def test_documented_edge_count():
    assert len(sd.EDGE_TYPES) == 19


def test_per_type_ring_membership_edges_present():
    """Live schema uses explicit per-type edges, not polymorphic ones."""
    names = {e.name for e in sd.EDGE_TYPES}
    for required in (
        "PERSON_MEMBER_OF_RING", "COMPANY_MEMBER_OF_RING",
        "ACCOUNT_MEMBER_OF_RING", "TRANSACTION_MEMBER_OF_RING",
        "DEVICE_CONNECTED_TO_RING", "ADDRESS_CONNECTED_TO_RING",
    ):
        assert required in names, f"missing required ring edge {required}"


def test_deprecated_edges_not_defined():
    """Deprecated polymorphic edges must not reappear in the schema."""
    names = {e.name for e in sd.EDGE_TYPES}
    for forbidden in ("MEMBER_OF_RING", "CONNECTED_TO_RING", "PART_OF"):
        assert forbidden not in names, (
            f"deprecated edge {forbidden} reintroduced into schema"
        )


def test_ring_membership_frozenset_matches_edge_definitions():
    edge_names = {e.name for e in sd.EDGE_TYPES}
    for name in sd.RING_MEMBERSHIP_EDGES:
        assert name in edge_names, (
            f"RING_MEMBERSHIP_EDGES references {name} but it's not in EDGE_TYPES"
        )


def test_priority_edges_subset_of_defined_edges():
    edge_names = {e.name for e in sd.EDGE_TYPES}
    for name in sd.PRIORITY_EDGES:
        assert name in edge_names, (
            f"PRIORITY_EDGES references {name} but it's not in EDGE_TYPES"
        )


def test_get_vertex_get_edge_lookup():
    assert sd.get_vertex("Person").name == "Person"
    assert sd.get_vertex("DoesNotExist") is None
    assert sd.get_edge("OWNS").name == "OWNS"
    assert sd.get_edge("Nope") is None
