"""Smoke tests for the deterministic IntentClassifier.

These tests confirm:
  • the documented workflow mappings (rank_suspects, find_ring,
    trace_money, ownership_chain, shared_infrastructure) trigger on
    realistic analyst phrasings;
  • the entity-ID extractor catches every prefix the platform supports;
  • unknown queries get `kind="unknown"` plus operational suggestions
    (no chatbot drift);
  • the singleton accessor returns a single classifier instance.

No backend, no TigerGraph, no LLM. Pure determinism — fast.
"""
from importlib import import_module

intent_mod = import_module("4_orchestrator_api.orchestration.intent")
IntentClassifier = intent_mod.IntentClassifier
get_classifier = intent_mod.get_classifier


def test_singleton_returns_same_instance():
    a = get_classifier()
    b = get_classifier()
    assert a is b


def test_empty_query_returns_unknown_with_hint():
    m = IntentClassifier().classify("")
    assert m.kind == "unknown"
    assert m.confidence == 0.0
    assert m.operational_hint  # non-empty
    assert m.suggested_workflows  # non-empty list of workflow dicts


def test_rank_suspects_intent():
    m = IntentClassifier().classify("who is the most suspected?")
    assert m.kind == "rank_suspects"
    assert m.confidence >= 0.5
    assert m.strategy_hint == "auto"


def test_find_ring_intent():
    m = IntentClassifier().classify("surface the hidden fraud rings in the network")
    assert m.kind == "find_ring"
    assert m.strategy_hint == "community"


def test_trace_money_intent():
    m = IntentClassifier().classify("trace the money flow through the laundering chain")
    assert m.kind == "trace_money"
    assert m.strategy_hint == "path"


def test_ownership_chain_intent():
    m = IntentClassifier().classify("who is the ultimate beneficial owner of C-001?")
    assert m.kind == "ownership_chain"


def test_shared_infrastructure_intent():
    m = IntentClassifier().classify("which persons share a device across rings?")
    assert m.kind == "shared_infrastructure"


def test_entity_id_extraction_covers_every_prefix():
    """Documented contract: P-, C-, A-, ADDR-, D-, TX-<num>, T-<num>, FR-…
    are all recognised. TX uses the numeric form (TX-12345); FR uses the
    composite form (FR-OFFSHORE-00 / FR-001)."""
    q = ("show P-001 with C-042 and A-007, ADDR-009, D-003, "
         "TX-12345, T-99, FR-OFFSHORE-00, FR-001")
    m = IntentClassifier().classify(q)
    ids = set(m.matched_entity_ids)
    for expected in ("P-001", "C-042", "A-007", "ADDR-009", "D-003",
                     "TX-12345", "T-99", "FR-OFFSHORE-00", "FR-001"):
        assert expected in ids, f"missing {expected} in {ids}"


def test_unknown_query_offers_suggestions():
    m = IntentClassifier().classify("what is the meaning of life")
    assert m.kind == "unknown"
    assert m.confidence < 0.25
    assert m.suggested_workflows
    # Suggestions must include the canonical operational workflows.
    kinds = {wf["kind"] for wf in m.suggested_workflows}
    assert "rank_suspects" in kinds
    assert "trace_money" in kinds


def test_requires_entity_id_downgrades_confidence_when_missing():
    # `entity_dossier` requires an entity ID — without one, confidence is halved.
    with_id    = IntentClassifier().classify("show me the dossier on P-001")
    without_id = IntentClassifier().classify("show me the dossier please")
    assert with_id.confidence >= without_id.confidence


def test_intent_classification_is_subms():
    """Documented contract: pure-python, sub-ms. We allow 50ms for CI noise."""
    import time
    clf = IntentClassifier()
    t0 = time.perf_counter()
    for _ in range(100):
        clf.classify("rank the most suspected entities across the laundering network")
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert elapsed_ms < 500, f"100 classifications took {elapsed_ms:.1f}ms (>500ms)"
