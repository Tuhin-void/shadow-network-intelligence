"""Smoke tests for the ingest schema-detection logic.

Locks in the *contract* that real CSV files — including the platform's own
`outputs/{profile}/csv/*.csv` outputs and any reasonable user variant —
auto-detect cleanly. Specifically:

  • Filename-first detection (singular / plural / aliases)
  • ID column aliasing (id / person_id / personId / entity_id)
  • Edge-file detection (*_edges.csv, *_ring_memberships.csv, *_ring_connections.csv)
  • Defaults from filename-to-edge-type map for ring membership files
  • Rejection of genuinely malformed files (no false positives)

No backend, no TigerGraph — pure unit tests.
"""
from importlib import import_module

ingest = import_module("4_orchestrator_api.api.ingest")


# ── Vertex detection ──────────────────────────────────────────────────────

def test_persons_csv_with_real_dataset_headers():
    """The platform's own persons.csv (which includes is_watched not in the
    historical accept set) must detect cleanly. Regression guard for the
    'unrecognized schema' bug where strict-subset detection rejected the
    platform's own outputs."""
    header = ["id", "name", "first_name", "last_name", "date_of_birth",
              "nationality", "tax_id", "risk_score", "is_pep",
              "is_sanctioned", "is_watched"]
    det = ingest._detect_schema("persons.csv", header)
    assert det is not None
    assert det["kind"] == "vertex"
    assert det["vertex_type"] == "Person"
    assert det["id_col"] == "id"
    assert det["via"] == "filename"


def test_filename_singular_plural_variants():
    header = ["id", "name"]
    for fname in ("persons.csv", "person.csv", "people.csv"):
        det = ingest._detect_schema(fname, header)
        assert det and det["vertex_type"] == "Person", f"failed for {fname}"


def test_companies_filename_variants():
    header = ["id", "name", "industry"]
    for fname in ("companies.csv", "company.csv", "corp.csv"):
        det = ingest._detect_schema(fname, header)
        assert det and det["vertex_type"] == "Company", f"failed for {fname}"


def test_transactions_filename_variants():
    header = ["id", "amount", "currency"]
    for fname in ("transactions.csv", "transaction.csv", "tx.csv", "txns.csv"):
        det = ingest._detect_schema(fname, header)
        assert det and det["vertex_type"] == "Transaction", f"failed for {fname}"


def test_id_column_aliasing():
    """Detection must accept person_id, personId, entity_id, etc."""
    for col in ("person_id", "personId", "PERSON_ID", "entity_id"):
        det = ingest._detect_schema("persons.csv", [col, "name"])
        assert det, f"failed to detect with id column {col}"
        assert det["id_col"] == col


def test_header_only_detection_when_filename_unrecognized():
    """If filename gives no hint but headers unambiguously suggest a type."""
    det = ingest._detect_schema("uploaded.csv", ["account_id", "balance"])
    assert det
    assert det["vertex_type"] == "Account"
    assert det["via"] == "header_only"


def test_fraud_rings_vertex_detection():
    header = ["id", "name", "ring_type", "severity", "description"]
    det = ingest._detect_schema("fraud_rings.csv", header)
    assert det
    assert det["kind"] == "vertex"
    assert det["vertex_type"] == "FraudRing"


# ── Edge detection ────────────────────────────────────────────────────────

def test_canonical_edges_csv_with_from_to():
    """edges.csv with from_id/to_id/relationship/from_type/to_type cols."""
    header = ["from_id", "from_type", "to_id", "to_type", "relationship",
              "weight", "is_fraud_related", "fraud_ring_id"]
    det = ingest._detect_schema("edges.csv", header)
    assert det
    assert det["kind"] == "edge"
    assert det["from_col"] == "from_id"
    assert det["to_col"] == "to_id"
    assert det["rel_col"] == "relationship"


def test_person_ring_memberships_default_edge_type():
    """*_ring_memberships.csv files use entity_id + ring_id and the edge
    type is encoded in the filename (PERSON_MEMBER_OF_RING, etc)."""
    header = ["entity_id", "ring_id", "role", "confidence_score", "discovered_at"]
    det = ingest._detect_schema("person_ring_memberships.csv", header)
    assert det
    assert det["kind"] == "edge"
    assert det["from_col"] == "entity_id"
    assert det["to_col"] == "ring_id"
    assert det["default_edge_type"] == "PERSON_MEMBER_OF_RING"
    assert det["default_from_type"] == "Person"
    assert det["default_to_type"] == "FraudRing"


def test_all_six_ring_membership_filenames():
    """The four membership + two connection ring-edge files all map."""
    header = ["entity_id", "ring_id", "role", "confidence_score", "discovered_at"]
    cases = {
        "person_ring_memberships.csv":       "PERSON_MEMBER_OF_RING",
        "company_ring_memberships.csv":      "COMPANY_MEMBER_OF_RING",
        "account_ring_memberships.csv":      "ACCOUNT_MEMBER_OF_RING",
        "transaction_ring_memberships.csv":  "TRANSACTION_MEMBER_OF_RING",
        "address_ring_connections.csv":      "ADDRESS_CONNECTED_TO_RING",
        "device_ring_connections.csv":       "DEVICE_CONNECTED_TO_RING",
    }
    for fname, expected_etype in cases.items():
        det = ingest._detect_schema(fname, header)
        assert det, f"failed to detect {fname}"
        assert det["default_edge_type"] == expected_etype, (
            f"{fname}: got {det['default_edge_type']} expected {expected_etype}"
        )


def test_generic_account_device_edges_via_filename_token():
    """Generic relationship file via filename `_edges` + from/to header."""
    header = ["source_id", "target_id", "edge_type", "timestamp"]
    det = ingest._detect_schema("account_device_edges.csv", header)
    assert det
    assert det["kind"] == "edge"
    assert det["from_col"] == "source_id"
    assert det["to_col"] == "target_id"
    assert det["rel_col"] == "edge_type"


# ── Negative cases (rejection) ────────────────────────────────────────────

def test_empty_header_returns_none():
    assert ingest._detect_schema("anything.csv", []) is None


def test_random_file_with_no_id_column_returns_none():
    det = ingest._detect_schema("weather.csv",
                                ["temperature", "humidity", "wind"])
    assert det is None


def test_ambiguous_header_only_returns_none():
    """If the header has multiple matching ID aliases AND no filename hint,
    detection must be ambiguous → None (not a wrong guess)."""
    # `id` alone matches every vertex type → ambiguous when no filename hint
    det = ingest._detect_schema("mystery.csv", ["id", "name"])
    assert det is None


# ── Row builder (vertex) ──────────────────────────────────────────────────

def test_build_vertex_records_coerces_risk_score_int_pct():
    """is_pep + risk_score must coerce correctly via _SCHEMA_HINTS rules."""
    csv_text = ("id,name,risk_score,is_pep\n"
                "P-001,Alice,0.75,true\n"
                "P-002,Bob,80,false\n"
                ",NoID,0.1,false\n")
    records, skipped = ingest._build_vertex_records(csv_text, "Person", "id")
    assert len(records) == 2
    assert len(skipped) == 1
    assert skipped[0]["reason"] == "missing id"
    r1 = next(r for r in records if r["v_id"] == "P-001")
    # 0.75 → 75 via int_pct rescaling
    assert r1["risk_score"] == 75
    assert r1["pep_flag"] is True
    r2 = next(r for r in records if r["v_id"] == "P-002")
    # 80 stays 80 (already in 0-100 range)
    assert r2["risk_score"] == 80


# ── Row builder (edge) ────────────────────────────────────────────────────

def test_build_edge_records_groups_by_triple_and_uses_filename_default():
    csv_text = ("entity_id,ring_id,role,confidence_score\n"
                "P-001,FR-001,leader,0.9\n"
                "P-002,FR-001,member,0.7\n")
    det = ingest._detect_schema("person_ring_memberships.csv",
                                ["entity_id", "ring_id", "role", "confidence_score"])
    grouped, skipped = ingest._build_edge_records(csv_text, det)
    assert not skipped
    # Single edge_type / from / to combo expected.
    assert len(grouped) == 1
    key = ("PERSON_MEMBER_OF_RING", "Person", "FraudRing")
    assert key in grouped
    assert len(grouped[key]) == 2
    rec = grouped[key][0]
    assert rec["from_id"] == "P-001"
    assert rec["to_id"]   == "FR-001"
    assert rec["from_type"] == "Person"
    assert rec["to_type"]   == "FraudRing"
    # Extra columns flow through as edge attributes (TG drops unknowns).
    assert "role" in rec
    assert "confidence_score" in rec


def test_build_edge_records_uses_relationship_column_when_no_default():
    """Generic edges.csv with mixed relationship column values must group
    one batch per edge_type."""
    csv_text = ("from_id,from_type,to_id,to_type,relationship\n"
                "P-001,Person,C-001,Company,OWNS\n"
                "P-002,Person,A-001,Account,HAS_ACCOUNT\n"
                "P-003,Person,C-001,Company,OWNS\n")
    det = ingest._detect_schema("edges.csv", [
        "from_id", "from_type", "to_id", "to_type", "relationship",
    ])
    grouped, _ = ingest._build_edge_records(csv_text, det)
    assert len(grouped) == 2
    # Two OWNS rows + one HAS_ACCOUNT row, both grouped correctly.
    owns_key = ("OWNS", "Person", "Company")
    has_key  = ("HAS_ACCOUNT", "Person", "Account")
    assert len(grouped[owns_key]) == 2
    assert len(grouped[has_key]) == 1
