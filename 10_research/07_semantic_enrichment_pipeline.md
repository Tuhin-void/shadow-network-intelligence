# 07 — Semantic Enrichment Pipeline

The retrieval engine is structural — typed-edge traversal, topology
reranking, ring-member promotion. But the queries are natural language,
and that gap is closed by a separate semantic-enrichment layer that
runs **outside** the retrieval hot path.

This document explains what enrichment does, why it's external, and
where its outputs land.

## What enrichment is

Enrichment is the process of generating natural-language descriptions
and entity embeddings for the synthetic dataset. The output is:

1. **Per-entity descriptions** — a short narrative summary attached to
   each Person, Company, Account so that token-match retrievers can
   reason about entities that have no descriptive text in the raw CSV
2. **Per-entity embeddings** — vector representations used by:
   - The `EntityCentricRetriever` (semantic matching when token match
     produces no candidate)
   - The `SemanticScorer` (embedding-cosine fallback for benchmark
     scoring when `bert_score` isn't installed)
   - The VectorRAG pipeline (its document chunks)
3. **Cross-references** — pre-computed adjacency snapshots that
   accelerate prewarm

## Why it lives outside the retrieval engine

Two reasons:

**1. Determinism of retrieval.**
Retrieval must be reproducible. Embeddings depend on the embedder
provider; running enrichment on every query would make every benchmark
non-deterministic. Enrichment runs **once** (at data-engine output
time, or once per profile), and the retrieval engine reads the
materialized output.

**2. Pipeline parity.**
The VectorRAG baseline pipeline needs the same enriched corpus
GraphRAG sees. If enrichment lived inside GraphRAG, the comparison
would be unfair — VectorRAG would be retrieving from raw CSV while
GraphRAG would have semantic context. By extracting enrichment, both
pipelines start from the same enriched substrate.

## Where the outputs land

```
outputs/{profile}/
├── csv/                          ← data engine raw output
├── json/                         ← per-entity JSON (with descriptions)
├── cross_refs/                   ← pre-computed adjacency
└── chroma_db/                    ← VectorRAG vector store (Chroma)

2_baseline_systems/outputs/
└── chromadb/                     ← benchmark-runner vector store
```

These directories are referenced at runtime — see the cleanup section
of [`08_system_evolution.md`](./08_system_evolution.md). They are
**not** safe to delete.

## What enrichment is NOT

- It is **not** a join precomputation. Joins happen at query time via
  TigerGraph traversal.
- It is **not** a knowledge graph extraction. The graph is the source
  of truth; enrichment adds text *over* the graph, not derived *from*
  text.
- It is **not** an LLM-generated narrative summary of investigations.
  Those are produced at query time by the reasoning engine.

## When you re-run enrichment

You only need to re-run enrichment when:

1. The data profile changes (new entity counts, new ring patterns)
2. The embedder model changes (NIM → Ollama, for example) — and only
   if you want the VectorRAG baseline to use the new embedder
3. The schema changes (new vertex types that need descriptions)

For a normal benchmark run against an unchanged profile, enrichment
is read-only.

## The embedder provider choice

The platform supports multiple embedder providers, all gated by the
`Embedder(provider=...)` constructor:

| Provider | When to use |
|---|---|
| `nim` | Production — NVIDIA NIM `nvidia/llama-nemotron-embed-1b-v2` (2048-dim) |
| `ollama` | Local development — `nomic-embed-text` (768-dim) |
| `openai` | Cloud — `text-embedding-3-large` (3072-dim) |
| `mock` | CI / deterministic benchmarks — seeded random (768-dim) |

The provider is configured per-run via the `BenchmarkRunner` config or
via env vars (`SNI_BENCHMARK_*` family). The benchmark JSON records the
provider, so a reviewer can verify which embedder produced the numbers.

## The cost surface

NIM embeddings cost the most in actual latency (network round-trip per
call). For benchmarks we prefer:

- **NIM** for the entity-centric retrieval pass (one call per query)
- **Mock** for the VectorRAG document corpus when the goal is to measure
  retrieval *substrate*, not embedder quality

The cost surface is honest: we don't claim "free retrieval" anywhere.
The `cost_estimate` field on every PipelineResult records the LLM cost
from `TokenTracker._get_pricing(model)`. For mock providers it's $0
(disclosed). For real providers it's a pricing-table lookup.
