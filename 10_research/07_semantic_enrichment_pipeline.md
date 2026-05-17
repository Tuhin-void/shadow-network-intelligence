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

## The semantic-intelligence corpus

`scripts/semantic_intelligence_corpus.py` is a deterministic, template-
driven generator that materialises a LARGE volume of operational AML/
compliance-style documents from the existing graph data. **No LLM
calls, no API cost, no graph mutation.**

### What it produces

Per entity type:

| Entity      | Docs per entity | Doc types                                          |
|---          |---              |---                                                  |
| Person      | 2               | `subject_brief`, `behavior_narrative`              |
| Company     | 2               | `corporate_dossier`, `beneficial_ownership`        |
| Account     | 1               | `account_intelligence`                              |
| Ring        | 3               | `ring_operational_summary`, `laundering_pathway`, `cross_entity_analysis` |
| Address     | 1 (top-collision) | `infra_overlap`                                  |
| Device      | 1 (top-collision) | `device_fingerprint`                             |
| Suspicious Tx | 1             | `transaction_intelligence`                          |
| Ring key entities | 1         | `neighborhood_walk` (depth-2)                       |

### Output structure

```
outputs/{profile}/enriched_corpus/
├── {profile}_intelligence.jsonl   ← primary chunk-ready output
├── manifest.json                   ← doc counts, token estimates, ring coverage
└── sample_markdown/                ← 12 human-readable sample docs
```

Each JSONL record carries chunk-ready metadata:

```json
{
  "doc_id":             "SUBJ-P-000001",
  "doc_type":           "subject_brief",
  "primary_entity":     "P-000001",
  "related_entities":   ["A-005895", "ADDR-000785", "C-003398", "P-000531"],
  "topology_tags":      ["degree=5", "tier=monitored"],
  "risk_tags":          ["monitored"],
  "edge_types":         ["ASSOCIATED_WITH", "HAS_ACCOUNT", "LOCATED_AT", ...],
  "ring_id":            null,
  "investigation_type": "subject_review",
  "retrieval_keywords": ["P-000001", "Raj Al-Hassan", ...],
  "narrative":          "Operational note on subject P-000001 ...",
  "token_estimate":     167,
  "chunk_size_chars":   668
}
```

### Grounding contract

Every doc references **real entity IDs from the source CSVs** and
walks **real edges from `edges.csv`** / the ring-membership tables.
No invented topology. The grounding check at the bottom of this section
verifies this on every run.

Validation method:
```bash
python3 -c "
import json, csv
ids = set()
for f in ['persons','companies','accounts','addresses','devices','transactions','fraud_rings']:
    for row in csv.DictReader(open(f'outputs/small/csv/{f}.csv')):
        ids.add(row['id'])
bad = 0
for line in open('outputs/small/enriched_corpus/small_intelligence.jsonl'):
    d = json.loads(line)
    for r in [d['primary_entity']] + d['related_entities']:
        if r and r.startswith(('P-','C-','A-','ADDR-','D-','TX-','FR-')) and r not in ids:
            bad += 1
print('invalid:', bad)
"
```

### How it's consumed

`DocumentBuilder.build_with_enrichment(jsonl_path)` is the opt-in path
on the VectorRAG baseline. When the enriched JSONL exists for the
active profile, it is automatically merged into the indexed corpus.
When it doesn't, the builder falls back to `build_all()` — backward
compatible, no behavioural change.

Wiring (in `2_baseline_systems/pipelines/vector_rag.py`):

```python
candidate = (REPO_ROOT / "outputs" / profile / "enriched_corpus" /
             f"{profile}_intelligence.jsonl")
docs = builder.build_with_enrichment(
    jsonl_path=candidate if candidate.exists() else None,
)
```

### Determinism + reproducibility

- Seeded by `(entity_id, doc_type, slot_name)` per-template pick →
  identical inputs produce identical text across runs
- `--seed N` flag overrides the default seed (42)
- No randomness leaks into the manifest — re-running with the same
  inputs produces an identical JSONL

### Usage

```bash
# Smoke test: 50 docs per entity-type pass (~70k tokens, <1s)
make enrich-corpus-test
# or directly:
python3 scripts/semantic_intelligence_corpus.py --profile small --limit 50

# Full corpus generation (small profile → ~6M tokens estimated, ~37k docs)
make enrich-corpus
# or directly:
python3 scripts/semantic_intelligence_corpus.py --profile small

# Dry run: compute manifest stats without writing JSONL
python3 scripts/semantic_intelligence_corpus.py --profile small --dry-run

# Larger profile
python3 scripts/semantic_intelligence_corpus.py --profile benchmark_dense
```

### Relationship to `scripts/data_corpus_enricher.py`

The older enricher produces 89 markdown narratives focused on ring
dossiers and high-collision infrastructure briefs (~17k tokens). The
new generator is a strict superset: same grounding contract, same
markdown style, plus many more entity-type passes, plus chunk-ready
JSONL output. Both are kept; the new one is the default consumer for
the VectorRAG baseline.

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
