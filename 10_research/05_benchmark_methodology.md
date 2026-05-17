# 05 — Benchmark Methodology (philosophy)

The mechanical methodology — what scripts run, what they emit — is in
[`../docs/BENCHMARK_METHOD.md`](../docs/BENCHMARK_METHOD.md). This
document covers the *philosophy*: what we measure, what we won't claim,
and why every number is artifact-grounded.

## The reproducibility contract

Every reported number on this platform must satisfy:

1. **Artifact-grounded.** The number originates in a JSON file on disk
   (`scripts/adversarial_results.json`,
   `2_baseline_systems/outputs/benchmark_results/benchmark_RUN_*.json`,
   etc.). The UI reads JSON. The README reads JSON. We never paste
   metrics into prose without a generating artifact.
2. **Reproducible.** The user can run one command to regenerate the
   artifact. The API returns HTTP 404 with that command when the
   artifact is missing — not a synthesized fallback.
3. **Auditable.** Per-pipeline aggregates can be cross-checked against
   the raw per-query records in the same file. Frontend transforms are
   pure projection — no synthesis in the adapters.
4. **Honestly labelled.** Mock LLM latency is disclosed as mock;
   embedding-cosine semantic scoring is labelled `embedding_cosine`
   not `bertscore` (unless `bert_score` is actually installed).

## What we measure

| Signal | Source | Why this and not something else |
|---|---|---|
| `structural_edges` per query | adversarial JSON | proves traversal happened |
| `neighbors` per query | adversarial JSON | retrieval surface size |
| `evidence` per query | adversarial JSON | items in EvidenceChainBuilder |
| `ring_touch_sum` | adversarial JSON | ring connectivity |
| `prompt/completion/total_tokens` | benchmark RUN JSON | real tokenizer counts |
| `latency_ms` | benchmark RUN JSON | LLM call (mock by default) |
| `retrieval_ms` | benchmark RUN JSON | **real** retrieval cost |
| `cost_estimate` | TokenTracker | pricing table; $0 for mock |
| LLM-judge breakdown (1–5 per dim) | LLMJudge | when scored |
| Entity F1 / precision / recall | EntityMatcher | regex vs ground truth |
| Semantic score | SemanticScorer | bertscore OR embedding cosine |
| Hallucination resistance rate | derived from judge | fraction with hallucination ≥ 4/5 |
| Judge pass rate | derived from judge | fraction with overall ≥ 4/5 |

## What we will not claim

These are explicit non-claims. Saying them with hand-waved evidence
would weaken the credible claims:

- **"GraphRAG is faster than VectorRAG"** — it isn't, on first call.
  GraphRAG pays 7–23s of real traversal latency cold. We expose this
  honestly via `avg_retrieval_ms` rather than hiding it.
- **"GraphRAG achieves >X% accuracy"** — accuracy against what
  ground truth? We don't fabricate a held-out test set. We report
  structural recovery, which is verifiable per query.
- **"GraphRAG hallucinates less"** — when judged by a mock LLM, this
  number is meaningless. We surface the judge breakdown when a real
  judge is configured and label the mock case honestly.
- **"GraphRAG works on every query"** — there are query classes
  GraphRAG is wrong for. See [02_why_graphrag.md](./02_why_graphrag.md#when-graphrag-is-the-wrong-tool).

## How latency is reported

Two different latency numbers, both real, neither hidden:

- **`avg_latency_ms`** — the LLM call (mock 50ms placeholder unless a
  real provider is configured). Disclosed in every response.
- **`avg_retrieval_ms`** — the real measured retrieval cost (vector
  search OR graph traversal). This is the *operational* latency signal.

The disclosure is in the endpoint payload itself:

```json
"disclosure": {
  "latency_ms_is_mock_llm": "avg_latency_ms reflects the LLM call which
    is mock unless a real provider is configured. avg_retrieval_ms is
    the real measured retrieval cost.",
  "tokens_are_real": "Token counts come from actual prompt construction
    even with mock LLM — they measure exactly what each pipeline injects
    into the LLM context.",
  ...
}
```

A reviewer reading the API response sees the caveat next to the number.

## LLM-as-judge

`LLMJudge` (`2_baseline_systems/evaluation/llm_judge.py`) scores 1–5 on
6 dimensions per answer:

- Relevance — does it address the question
- Accuracy — are stated facts correct in context
- Completeness — are all relevant entities/relationships covered
- Hallucination — 5 = no hallucinations, 1 = major hallucinations
- Clarity — well-structured and explainable
- Overall — composite

The judge runs against a separate LLM client when configured
(`judge_llm_client`) — same-LLM judging is logged as a warning because
the judge would share the pipeline's biases.

Aggregates:
- **Judge pass rate** = fraction of queries with overall ≥ 4
- **Hallucination resistance rate** = fraction with hallucination ≥ 4
- **Failure counts** = categorical breakdown
  (`hallucination`, `missed_topology`, `context_pollution`,
  `retrieval_irrelevance`, `context_overload`)

## Semantic scoring

`SemanticScorer` (`2_baseline_systems/evaluation/semantic_scorer.py`)
prefers **true BERTScore F1** when `bert_score` is installed, falls back
to **embedding-cosine** otherwise. The method used is reported in the
response (`semantic_method`) — never silently swapped.

The reference is synthesized from the BenchmarkQuery's
`ground_truth_entities` + `ground_truth_paths` (a natural-language
projection of structured truth). Empty answers return 0; missing
ground truth returns the neutral 0.5 with method labelled
`<method>:no_reference`.

## Entity matching

`EntityMatcher` extracts entity IDs from the model's answer text using a
regex covering the platform's prefixes (`P-`, `C-`, `A-`, `ADDR-`, `D-`,
`TX-`, `T-`, `FR-`), then computes precision / recall / F1 against the
query's `ground_truth_entities` set. This is the most direct signal we
have: did the model name the entities it should have named.

## Reproducibility checklist

The reviewer can re-derive every number on the platform with three
commands:

```bash
# Live TG sanity check
python3 scripts/tigergraph_validate.py

# Drift check (run the suite twice, compare)
python3 scripts/benchmark_reliability.py --limit 5

# The full adversarial suite
python3 scripts/adversarial_benchmark.py --profile small

# Optional: aggregate into one executive dossier
python3 scripts/benchmark_full_report.py --profile small
```

If TG is unreachable, every script exits non-zero with a clear message.
Nothing fabricates numbers.

## Why we ship a separate `LiveBenchmarkConsole`

`8_dashboard_ui/src/components/benchmark/LiveBenchmarkConsole.tsx`
triggers benchmark runs from the UI via `POST /benchmark/run/stream`.
It does NOT bypass the script-based path — it uses the same
`BenchmarkRunner` and writes the same JSON shape. The point is
**observability**: a reviewer who can't run Python from a laptop can
still re-execute the benchmark and inspect aggregates.

Same artifact path, different trigger surface.

## Post-enrichment benchmark contract

After the semantic intelligence corpus is hydrated (see
[`07_semantic_enrichment_pipeline.md`](./07_semantic_enrichment_pipeline.md)),
the `/benchmark/quantitative` endpoint surfaces two additional context
blocks so the UI can frame numbers honestly:

### `retrieval_context`

Tells the reviewer what each pipeline would index against in
production:

```json
{
  "vector_provider":      "mock" | "chroma",
  "llm_provider":         "mock" | "ollama" | "openai" | "anthropic",
  "graph_provider":       "tigergraph",
  "embedder_provider":    "nim" | "ollama" | "mock",
  "vectorrag_mode":       "mock (deterministic, returns no results)" | "real_chroma_search",
  "graphrag_mode":        "live_tigergraph_traversal",
  "semantic_corpus_size": 35402,       // from outputs/{profile}/enriched_corpus/manifest.json
  "enrichment_token_count": 6097207,
  "enriched_doc_types":   ["subject_brief", "behavior_narrative", ...]
}
```

The frontend uses `semantic_corpus_size` to honestly show
**"VectorRAG indexed 35,402 semantic chunks"** even when the live sweep
returned 0 sources via the mock provider. The phrasing on the UI is
"0 structural edges by definition — text chunks ≠ graph joins" rather
than the misleading bare "0 sources."

### `latency_context`

Explicitly frames benchmark sweeps as **cold**:

```json
{
  "sweep_mode":          "cold",
  "explanation":         "Benchmark sweeps run every query through a cold engine path so each measurement is independent. Steady-state operational latency is <50ms warm-cache (see /investigate in the orchestrator).",
  "cold_avg_retrieval_ms": 3073.1,
  "warm_replay_ms":      "<50ms (orchestrator ResultCache hit)"
}
```

This prevents the common misreading that `avg_retrieval_ms` ≈ user-
facing latency. It is not — it is the per-query cold cost of a
benchmark sweep. Real user latency on the warm-cache path is <50ms.

## The structural-verdict explainer

`StructuralVerdictExplainer` (in
[`../8_dashboard_ui/src/components/benchmark/StructuralVerdictExplainer.tsx`](../8_dashboard_ui/src/components/benchmark/StructuralVerdictExplainer.tsx))
is a single UI surface that teaches the central thesis: **semantic
similarity is not structural continuity**. It cross-references the
actual benchmark numbers (structural recovery per pipeline) and ties
them to a substrate-level explanation:

- PureLLM → "model priors" → "disconnected"
- VectorRAG → "text chunks" → "related but fragmented"
- GraphRAG → "typed-edge subgraphs" → "continuous multi-hop"

Every claim made in the explainer is grounded in a number already in
the response — no rhetoric without an artifact reference.
