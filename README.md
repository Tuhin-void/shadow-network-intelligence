# Shadow Network Intelligence

> **The answer is an edge, not a sentence.**
>
> A GraphRAG fraud-intelligence platform proving — with measured numbers, not
> claims — that structural intelligence emerges from relationship topology,
> not from larger prompts.

---

## What this is

A research-grade investigation platform that runs the same fraud queries
through three retrieval paradigms (**PureLLM**, **VectorRAG**, **GraphRAG**)
against a live **TigerGraph Cloud** topology, and demonstrates GraphRAG's
structural superiority — quantitatively, reproducibly, and operationally.

The platform is a complete investigation environment, not a benchmark
script:

- A synthetic data engine that generates dense, multi-ring fraud topologies
- A live TigerGraph Cloud (`ShadowGraph`) deployment with 175k+ vertices /
  373k+ edges and 6 reverse-edge types for backward traversal
- A retrieval engine with topology-aware reranking, ring-member promotion,
  and hidden-relationship expansion
- A FastAPI orchestrator exposing structured investigations + SSE streaming
- A production React/TS dashboard with a Worldspace + TacticalRail UX
- A 5-agent professional investigation swarm composing the engine
- A reasoning layer producing claims, contradictions, and per-suspect
  explanations
- A reporting layer generating investigation briefs, ring summaries, and
  benchmark dossiers

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│  1_data_engine    →  generates synthetic AML/fraud topology              │
│       │                                                                  │
│       ▼  outputs/{profile}/csv/                                          │
│                                                                          │
│  3_graph_intelligence_core    ◄── live TigerGraph Cloud (ShadowGraph)    │
│   ├── clients/graph_client (auth, neighbor cache, offline fallback)      │
│   ├── retrievers (entity, neighborhood, path-aware, community, hybrid)   │
│   ├── graph_rag/graphrag_engine (topology rerank, ring promotion, etc.)  │
│   └── validation/schema_def (source-of-truth: 7 vertices, 19 + 6 rev)    │
│       │                                                                  │
│       ▼                                                                  │
│                                                                          │
│  2_baseline_systems    →  benchmark runner over 3 pipelines              │
│   ├── pipelines/pure_llm                                                 │
│   ├── pipelines/vector_rag  (Chroma + embeddings)                        │
│   └── pipelines/graph_rag   (GraphRAG via adapter)                       │
│                                                                          │
│  4_orchestrator_api    →  FastAPI thin orchestrator                      │
│   ├── /investigate, /investigate/stream  (SSE)                           │
│   ├── /demo/presets, /demo/run/{key}, /demo/stream/{key}                 │
│   ├── /sessions, /orchestrator/status                                    │
│   └── orchestration/result_cache  (LRU+TTL on engine.query)              │
│       │                                                                  │
│       ▼                                                                  │
│                                                                          │
│  5_agent_swarm    →  5 professional analysis agents + coordinator        │
│   ├── RetrievalAnalyst, GraphTopologyInvestigator,                       │
│   ├── SanctionsExposureTracer, FraudRingAnalyst,                         │
│   └── SynthesisCoordinator                                               │
│                                                                          │
│  6_reasoning_engine    →  claims, contradictions, structural confidence  │
│                                                                          │
│  7_reporting_engine    →  4 markdown+JSON report generators              │
│                                                                          │
│  8_dashboard_ui    →  React/TS operational dashboard                     │
│   ├── adapter-only integration (api-client + lib/adapters)               │
│   └── live backend pill + LiveLaunchpad + cinematic SSE flow             │
│                                                                          │
│  scripts/    →  validators (adversarial, reliability, TG, enricher,      │
│                              consolidator)                               │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

## Real measured results

Real numbers from `scripts/adversarial_benchmark.py` (20 queries, profile
`small`, live TigerGraph Cloud):

| pipeline | structural evidence per query | avg tokens | avg retrieval ms | sources retrieved |
|---|---:|---:|---:|---:|
| **PureLLM** | **0** (no retrieval) | 22 | 0 | 0 |
| **VectorRAG** | **0** (text chunks only) | 554 | 14 | 10 text chunks |
| **GraphRAG** | **3+ structural edges** on **20/20 queries** | 50 | 20,160 | 1 focused structural answer |

**Why GraphRAG wins:** vector retrieval cannot reconstruct edges from text;
the answers to questions like *"who is the hidden controller of this shell-
company cluster"* live in the graph join, not in any single document.

GraphRAG uses **11× fewer tokens** than VectorRAG while producing the
**only** answer with grounded structural evidence.

## Live TigerGraph topology

Validated via `scripts/tigergraph_validate.py`:

```
Host:           tg-…-tgcloud.io  (ShadowGraph)
Status:         HEALTHY
Vertices:       175,204     (Person 6k, Company 5k, Account 10k,
                             Address 4k, Device 150, Transaction 150k)
Edges:          373,439     (19 forward types + 6 reverse_*)
Reverse edges:  84+23+74+23 populated (member_of_ring traversal)
Rings:          15 fraud rings with structural members
Installed GSQL: tg_ring_members, tg_shortest_path
```

## Quickstart

### 1. Environment

```bash
cp .env.example .env    # add TIGERGRAPH_HOST, TIGERGRAPH_GSQL_SECRET,
                        # TIGERGRAPH_GRAPH, NIM_API_KEY (optional)
pip install -r requirements.txt
```

### 2. Generate data (small profile, ~30s)

```bash
python -m 1_data_engine generate --profile small --new-pipeline
```

### 3. Load into TigerGraph

```bash
python -m 3_graph_intelligence_core load small
python -m 3_graph_intelligence_core health
```

### 4. Validate end-to-end

```bash
python3 scripts/tigergraph_validate.py
python3 scripts/benchmark_reliability.py --limit 5
python3 scripts/adversarial_benchmark.py --profile small
python3 scripts/benchmark_full_report.py --profile small
cat scripts/benchmark_full_report.md
```

### 5. Run the orchestrator + UI

```bash
# Terminal 1 — orchestrator API (port 8000)
PYTHONPATH=.:4_orchestrator_api uvicorn main:app --app-dir 4_orchestrator_api --port 8000

# Terminal 2 — dashboard (Vite dev, port 5173)
cd 8_dashboard_ui && npm install && npm run dev
```

Open `http://localhost:5173`. The TopBar pill flips **LIVE** within 4s.
The Home page shows curated live presets — click one to stream a real
investigation against the live graph.

### 6. Investigate from the CLI

```bash
# Run the 5-agent swarm on a curated preset
python3 -m 5_agent_swarm --preset ring-identification

# Same query, deeper reasoning (claims + contradictions + per-suspect rationale)
python3 -m 6_reasoning_engine --preset ring-identification

# Generate a production investigation brief (markdown + JSON)
python3 -m 7_reporting_engine brief --preset ring-identification

# Ring-centric report on FR-002
python3 -m 7_reporting_engine ring --ring FR-002

# Consolidated benchmark summary
python3 -m 7_reporting_engine bench
```

## Performance optimization

The orchestrator includes a process-local LRU+TTL **result cache**
(`4_orchestrator_api/orchestration/result_cache.py`) wrapping the engine's
`query()` call. Identical (query, top_k, depth, strategy) tuples return in
< 50ms after the first invocation — critical for the stable-preset demo
flow.

Config (defaults in parentheses):

```bash
SNI_RESULT_CACHE_ENABLED=1   # (true)
SNI_RESULT_CACHE_SIZE=64     # max entries
SNI_RESULT_CACHE_TTL=300     # seconds
SNI_PREWARM_ON_START=1       # (true) — warm 30 entities at boot
SNI_PREWARM_TOP_N=30         # entities to warm
```

## Adversarial benchmark suite

20 queries in `scripts/adversarial_queries.json` covering:

- ring identification, hidden beneficial owners, shared-infrastructure
  collusion, shared-device clusters, multi-hop laundering chains, funnel
  patterns, circular ownership rings, cross-ring participants, in-ring
  transactions, hidden controllers, centrality, indirect paths,
  sanctions exposure, intermediary discovery, cross-case linkage, ring
  reconstruction, nominee directors, fan-out dispersion, ring proximity,
  latent relationships

**Every single one** requires multi-hop graph traversal or hidden-relationship
discovery — VectorRAG produces **0/20** structural answers by definition.

## Project layout

```
Shadow_Network_Intelligence/
├── 1_data_engine/                  synthetic data generation
├── 2_baseline_systems/             benchmark runner (3 pipelines)
├── 3_graph_intelligence_core/      TigerGraph client + GraphRAG engine
├── 4_orchestrator_api/             FastAPI orchestrator + SSE + cache
├── 5_agent_swarm/                  5 professional analysis agents
├── 6_reasoning_engine/             claims, contradictions, explanations
├── 7_reporting_engine/             4 report generators (md + json)
├── 8_dashboard_ui/                 React/TS operational dashboard
├── 9_devops/                       Docker + deploy scripts
├── scripts/                        validators + benchmarks + enricher
├── shared/                         shared utilities
├── outputs/                        generated datasets + enriched corpora
└── configs/                        YAML config (secrets only via .env)
```

## Thesis

VectorRAG retrieves text. GraphRAG retrieves *structure*.

When the answer to *"who launders for this ring"* is a 3-hop join across
PERSON_MEMBER_OF_RING → SHARES_ADDRESS_WITH → OWNS, **no amount of context
window can recover it from chunked text**. The graph join is the answer.

That is what this platform proves.

## License

Apache 2.0
