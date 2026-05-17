"""Smoke tests for `4_orchestrator_api.api.benchmark._shape_quantitative`.

This is the function the dashboard uses to render the benchmark table.
It must:
  • aggregate per-approach correctly (avg tokens / latency / retrieval / src)
  • compute token-reduction vs the heaviest pipeline correctly
  • surface scoring aggregates only when evaluations are present
  • mark zero-row approaches as `queries: 0` (no NaN, no missing keys)
  • include the disclosure block on every response

No network, no FastAPI startup — we import the helper directly.
"""
from importlib import import_module

bm = import_module("4_orchestrator_api.api.benchmark")


def _row(approach, total_tokens, prompt_tokens, latency_ms, retrieval_ms,
         sources_n=0, cost=0.0):
    return {
        "approach":          approach,
        "total_tokens":      total_tokens,
        "prompt_tokens":     prompt_tokens,
        "completion_tokens": total_tokens - prompt_tokens,
        "latency_ms":        latency_ms,
        "retrieval_ms":      retrieval_ms,
        "sources":           [{"id": f"s{i}"} for i in range(sources_n)],
        "cost_estimate":     cost,
        "error":             None,
    }


def test_basic_aggregation_matches_arithmetic():
    run = {
        "run_id":    "RUN_TEST_001",
        "profile":   "small",
        "config":    {"vector_provider": "chroma", "llm_provider": "mock"},
        "queries_run": 3,
        "results": {
            "pure_llm":   [
                _row("pure_llm",   20, 20, 50, 0, sources_n=0),
                _row("pure_llm",   24, 22, 50, 0, sources_n=0),
                _row("pure_llm",   22, 20, 50, 0, sources_n=0),
            ],
            "vector_rag": [
                _row("vector_rag", 500, 480, 50, 15, sources_n=10),
                _row("vector_rag", 550, 530, 50, 14, sources_n=10),
                _row("vector_rag", 600, 580, 50, 18, sources_n=10),
            ],
            "graph_rag":  [
                _row("graph_rag",   50, 40, 50, 8000, sources_n=1),
                _row("graph_rag",   55, 44, 50, 9000, sources_n=1),
                _row("graph_rag",   48, 38, 50, 7500, sources_n=1),
            ],
        },
        "evaluations": {},
    }

    out = bm._shape_quantitative(run)
    assert out["run_id"] == "RUN_TEST_001"
    by_approach = {p["approach"]: p for p in out["pipelines"]}

    # Arithmetic correctness.
    assert by_approach["pure_llm"]["avg_total_tokens"] == 22.0
    assert by_approach["vector_rag"]["avg_total_tokens"] == 550.0
    assert by_approach["graph_rag"]["avg_total_tokens"] == 51.0

    # avg_sources_retrieved
    assert by_approach["vector_rag"]["avg_sources_retrieved"] == 10.0
    assert by_approach["graph_rag"]["avg_sources_retrieved"] == 1.0

    # No evaluation block → judge aggregates absent.
    assert "avg_judge_overall" not in by_approach["pure_llm"]


def test_token_reduction_vs_heaviest_is_correct():
    run = {
        "queries_run": 1,
        "config":      {},
        "results": {
            "pure_llm":   [_row("pure_llm",   100, 100, 50, 0)],
            "vector_rag": [_row("vector_rag", 1000, 950, 50, 14)],
            "graph_rag":  [_row("graph_rag",  100, 80,  50, 8000)],
        },
        "evaluations": {},
    }
    out = bm._shape_quantitative(run)
    by_approach = {p["approach"]: p for p in out["pipelines"]}
    # vector_rag is heaviest → its reduction is 0; the others are 90% lighter.
    assert by_approach["vector_rag"]["token_reduction_pct_vs_heaviest"] == 0.0
    assert by_approach["pure_llm"]["token_reduction_pct_vs_heaviest"] == 90.0
    assert by_approach["graph_rag"]["token_reduction_pct_vs_heaviest"] == 90.0


def test_empty_approach_is_marked_zero():
    run = {
        "queries_run": 1,
        "config":      {},
        "results": {
            "pure_llm":   [_row("pure_llm", 20, 20, 50, 0)],
            # vector_rag and graph_rag are absent
        },
        "evaluations": {},
    }
    out = bm._shape_quantitative(run)
    by_approach = {p["approach"]: p for p in out["pipelines"]}
    assert by_approach["vector_rag"] == {"approach": "vector_rag", "queries": 0,
                                          "token_reduction_pct_vs_heaviest": 0}
    assert by_approach["graph_rag"]  == {"approach": "graph_rag",  "queries": 0,
                                          "token_reduction_pct_vs_heaviest": 0}


def test_disclosure_block_is_always_present():
    run = {"queries_run": 0, "config": {}, "results": {}, "evaluations": {}}
    out = bm._shape_quantitative(run)
    assert "disclosure" in out
    assert "latency_ms_is_mock_llm" in out["disclosure"]
    assert "tokens_are_real"       in out["disclosure"]
    assert "judge_is_llm"          in out["disclosure"]
    # retrieval_context block surfaces the corpus + provider knobs.
    assert "retrieval_context" in out
    # latency_context warns about cold-sweep semantics.
    assert "latency_context" in out
    assert "sweep_mode" in out["latency_context"]


def test_score_aggregates_pass_rate_threshold():
    """judge_pass_rate counts queries where overall >= 4 (4 or 5)."""
    evs = [
        {"judge_breakdown": {"overall": 5, "hallucination": 5, "relevance": 5,
                              "accuracy": 5, "completeness": 5, "clarity": 5},
         "entity_match": {"f1": 0.8, "precision": 0.9, "recall": 0.7, "path_coverage": 0.5},
         "semantic_score": 0.9, "accuracy": 0.8, "semantic_method": "bertscore",
         "failure_reasons": []},
        {"judge_breakdown": {"overall": 4, "hallucination": 4, "relevance": 4,
                              "accuracy": 4, "completeness": 4, "clarity": 4},
         "entity_match": {"f1": 0.7, "precision": 0.8, "recall": 0.6, "path_coverage": 0.4},
         "semantic_score": 0.8, "accuracy": 0.7, "semantic_method": "bertscore",
         "failure_reasons": []},
        {"judge_breakdown": {"overall": 2, "hallucination": 2, "relevance": 2,
                              "accuracy": 2, "completeness": 2, "clarity": 2},
         "entity_match": {"f1": 0.3, "precision": 0.4, "recall": 0.2, "path_coverage": 0.0},
         "semantic_score": 0.4, "accuracy": 0.3, "semantic_method": "bertscore",
         "failure_reasons": ["missed_topology"]},
    ]
    agg = bm._score_aggregates(evs)
    # 2 of 3 ≥4 → pass_rate ≈ 0.6667
    assert abs(agg["judge_pass_rate"] - (2 / 3)) < 1e-3
    assert agg["n_evaluated"] == 3
    assert agg["failure_counts"] == {"missed_topology": 1}
