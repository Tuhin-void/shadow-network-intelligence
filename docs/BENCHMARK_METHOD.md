# Benchmark Methodology

## Thesis under test

> **Traditional retrieval preserves documents. GraphRAG preserves relationships.**

A query whose answer lives on a graph edge (ring membership, hidden ownership,
multi-hop laundering chain, shared infrastructure) cannot be reconstructed
from semantically-similar text chunks — no matter how good the embedding
model or how large the context window.

## Three pipelines, identical query set, identical corpus

| Pipeline | Source code | Retrieval mechanism |
|---|---|---|
| **PureLLM** | `2_baseline_systems/pipelines/pure_llm.py` | none — direct prompt to the LLM |
| **VectorRAG** | `2_baseline_systems/pipelines/vector_rag.py` | ChromaDB semantic search over chunked entity + transaction documents |
| **GraphRAG** | `2_baseline_systems/pipelines/graph_rag.py` → `3_graph_intelligence_core/graph_rag/graphrag_engine.py` | TigerGraph multi-hop traversal with topology-aware reranking, hidden-relationship expansion, ring-member promotion |

The fairness contract:
- Same queries (`scripts/adversarial_queries.json`, 20 queries)
- Same dataset (`outputs/{profile}/csv/`)
- Same embedder + LLM provider knobs
- Same query budget
- No special filters on either side

## Two complementary benchmark runners

### A. Adversarial benchmark (`scripts/adversarial_benchmark.py`)

20 queries explicitly designed to require multi-hop traversal or
hidden-relationship discovery. Measures:

- **GraphRAG structural metrics:** entities surfaced, neighbors traversed,
  structural edges in evidence, ring-touch sum, propagated risk, latency
- **VectorRAG proxy:** keyword-document hit count (definitional upper bound;
  vector retrieval cannot expose structural edges)
- **PureLLM:** retrieval = none (definitional)

Output: `scripts/adversarial_results.md` (per-query detail) +
`scripts/adversarial_results.json` (machine-readable).

### B. Full 3-pipeline runner (`python -m 2_baseline_systems benchmark`)

Runs the full pipeline orchestration over the standard query set (loaded by
`2_baseline_systems/benchmarking/query_loader.py`). Measures:

- `prompt_tokens`, `completion_tokens`, `total_tokens` per query per pipeline
- `latency_ms`, `retrieval_ms` per pipeline
- Number of sources retrieved
- Per-query answer text + traversal trace

Output: `2_baseline_systems/outputs/benchmark_results/benchmark_<RUN_ID>.json`
(immutable after creation).

## Reliability validation (`scripts/benchmark_reliability.py`)

Runs the adversarial suite **twice** against the same engine and asserts:

| Metric | Target |
|---|---|
| Structural drift (entity / neighbor / evidence count mismatch t1 vs t2) | 0 |
| Empty answers | 0 |
| Latency variance | within configured tolerance (default 80%) |

Output: `scripts/benchmark_reliability.{md,json}`.

## What we DO NOT claim

The benchmark **does not** claim:
- ">80% accuracy" against a fabricated ground truth
- "<500ms latency" on graph traversal (real cold latency is 7-23s; warm cache
  is <50ms)
- "GraphRAG is faster than VectorRAG" (it isn't, on first call)
- A subjective judge-LLM score

The benchmark **does** claim, with measured numbers:
- GraphRAG produces structural evidence on every adversarial query
- VectorRAG cannot — by definition, edges are not in text chunks
- GraphRAG uses ~11× fewer tokens per answer than VectorRAG
- Structural retrieval is reproducible (0 drift across trials)

## How to interpret the result table

| Column | What it means |
|---|---|
| `GraphRAG entities` | distinct entities surfaced as suspects (post-rerank) |
| `GraphRAG neighbors` | total graph neighbors traversed for context |
| `GraphRAG evidence` | items in the EvidenceChainBuilder output |
| `GraphRAG structural-edges` | count of typed structural edges in the answer |
| `Ring touch` | ring-membership ties surfaced across suspects |
| `VectorRAG (proxy)` | `docs=N struct=0` — N text-only matches, 0 edges (definitional) |
| `PureLLM` | always `struct=0` — no retrieval |

A high `structural-edges` count is the proof: the answer was a traversal,
not a text-similarity search.

## Reproducibility checklist

```bash
# Required: live TigerGraph (or accept offline-fallback graceful degradation)
python3 scripts/tigergraph_validate.py

# Run the validators
python3 scripts/benchmark_reliability.py --limit 5
python3 scripts/adversarial_benchmark.py --profile small

# Aggregate into one executive-grade dossier
python3 scripts/benchmark_full_report.py --profile small
cat scripts/benchmark_full_report.md
```

If TigerGraph is offline, scripts exit non-zero with a clear message — they
do not fabricate numbers.

## The 20 adversarial queries (categories)

`scripts/adversarial_queries.json` covers:

| # | Category | What it forces |
|---|---|---|
| 1 | ring_identification | reverse-edge traversal from FraudRing |
| 2 | hidden_beneficial_owner | BENEFITS_FROM expansion |
| 3 | shared_infrastructure | SHARES_ADDRESS_WITH + OWNS join |
| 4 | shared_device | SHARES_DEVICE_WITH expansion |
| 5 | multi_hop_laundering | TRANSFERRED_TO ordered chain |
| 6 | funnel_pattern | fan-in degree |
| 7 | circular_ownership | cycle detection via OWNS |
| 8 | cross_ring | participants in multiple rings |
| 9 | transaction_in_ring | TRANSACTION_MEMBER_OF_RING |
| 10 | hidden_controller | 3-hop Person → Company → Address ← Company |
| 11 | centrality | fraud-relevant degree |
| 12 | indirect_path | named-entity multi-hop |
| 13 | sanctions_exposure | flag + flow trace |
| 14 | intermediary_discovery | 2-hop transfer between two rings |
| 15 | cross_case_linkage | structural join across investigations |
| 16 | fraud_ring_reconstruction | reverse-edge across 6 edge types |
| 17 | nominee_director | OWNS aggregation + shell filter |
| 18 | fan_out_distribution | fan-out degree |
| 19 | ring_proximity | 2-hop ring-neighbor |
| 20 | latent_relationship | named entity → FraudRing transitive |

Every one of them requires traversal. None of them are answerable by
chunk-similarity alone.
