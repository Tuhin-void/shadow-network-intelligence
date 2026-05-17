"""Smoke tests for the regex-based EntityMatcher.

EntityMatcher feeds avg_entity_f1 / precision / recall in the benchmark
aggregator. These tests lock in:
  • the documented ID prefixes (P-, C-, A-, ADDR-, D-, TX-, T-, FR-…)
  • set semantics: precision/recall/F1 computed on intersection cardinality
  • empty ground truth yields the documented (1.0, 1.0, 1.0) convention
  • the matcher tolerates None / empty answers without raising
"""
from importlib import import_module

em_mod = import_module("2_baseline_systems.evaluation.entity_matcher")
schemas = import_module("2_baseline_systems.shared.schemas")
EntityMatcher = em_mod.EntityMatcher
BenchmarkQuery = schemas.BenchmarkQuery


def _q(ground_truth):
    return BenchmarkQuery(
        id="Q1", question="?", query_type="ring", required_hops=2,
        tier=1, ground_truth_entities=list(ground_truth),
        ground_truth_paths=[], complexity_score=0.0,
    )


def test_extract_covers_every_documented_prefix():
    m = EntityMatcher()
    text = ("found P-001 C-042 A-007 ADDR-009 D-003 TX-12 T-99 "
            "FR-OFFSHORE-00 noise FR-FUNNEL-01")
    ids = m.extract_entity_ids(text)
    for expected in ("P-001", "C-042", "A-007", "ADDR-009",
                     "D-003", "TX-12", "T-99",
                     "FR-OFFSHORE-00", "FR-FUNNEL-01"):
        assert expected in ids, f"missed {expected} in {ids}"


def test_perfect_recall_perfect_precision():
    m = EntityMatcher()
    result = m.match("answer references P-001 and P-002",
                     _q({"P-001", "P-002"}))
    assert result.precision == 1.0
    assert result.recall == 1.0
    assert result.f1 == 1.0
    assert result.false_positives == 0


def test_partial_recall_drops_f1():
    m = EntityMatcher()
    result = m.match("only mentions P-001", _q({"P-001", "P-002"}))
    assert result.true_positives == 1
    assert result.false_negatives == 1
    assert result.recall == 0.5
    assert 0 < result.f1 < 1


def test_false_positive_drops_precision():
    m = EntityMatcher()
    result = m.match("mentions P-001 P-002 P-099", _q({"P-001", "P-002"}))
    assert result.true_positives == 2
    assert result.false_positives == 1
    assert result.recall == 1.0
    assert abs(result.precision - (2 / 3)) < 1e-3


def test_empty_ground_truth_uses_documented_convention():
    m = EntityMatcher()
    result = m.match("mentions P-001 P-002", _q(set()))
    # Documented contract: empty ground truth → (1.0, 1.0, 1.0)
    assert result.precision == 1.0
    assert result.recall == 1.0
    assert result.f1 == 1.0


def test_empty_answer_does_not_raise():
    m = EntityMatcher()
    result = m.match("", _q({"P-001"}))
    # No predictions → tp=0, fn=1, recall=0
    assert result.true_positives == 0
    assert result.false_negatives == 1
    assert result.recall == 0.0
