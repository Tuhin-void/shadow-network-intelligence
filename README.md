# Shadow Network Intelligence

> **The answer is an edge, not a sentence.**
>
> A GraphRAG fraud-intelligence platform demonstrating — with measured
> numbers and live TigerGraph traversal — that structural intelligence
> emerges from relationship topology, not from larger prompts.

---

## TL;DR

A research-grade investigation platform that runs the same fraud queries
through three retrieval paradigms — **PureLLM**, **VectorRAG**,
**GraphRAG** — against a live **TigerGraph Cloud** instance with
175k+ vertices / 373k+ edges, and demonstrates GraphRAG's structural
superiority quantitatively and operationally.

- **20-query adversarial benchmark:** GraphRAG produces structural
  evidence on 20/20 queries · VectorRAG on **0/20** (by definition —
  edges aren't in text chunks)
- **11× fewer tokens per answer** than VectorRAG while producing the
  only answer with grounded structural evidence
- **<50 ms warm-cache replay** on identical queries (vs 7–23 s cold)
- **Semantic enrichment corpus:** 35,402 grounded intelligence
  documents · ~6.1M tokens · 25,238 real graph IDs referenced ·
  generated deterministically from the live topology, no LLM cost
  (see [`make enrich-corpus`](#5-run-the-orchestrator--ui))
- **Honest disclosures:** mock LLM is labelled mock; offline-fallback
  is labelled offline; planned connectors are labelled planned; no
  fabricated metrics anywhere

---

## What this is

A complete investigation environment, not a benchmark script:

- **Data engine** generating dense, multi-ring fraud topologies
- **Live TigerGraph Cloud** (`ShadowGraph`) with 7 vertex types, 19
  forward edges, 6 reverse edges for backward traversal from fraud rings
- **Retrieval engine** with topology-aware reranking, ring-member
  promotion, and hidden-relationship expansion
- **FastAPI orchestrator** with SSE streaming and a process-local
  result cache
- **React/TypeScript dashboard** with cinematic SSE flow, intent-aware
  custom investigations, and a disk-backed investigation archive
- **5-agent professional swarm** composing the engine (no duplicate
  retrieval)
- **Reasoning layer** producing claims, contradictions, and per-suspect
  explanations
- **Reporting layer** generating investigation briefs, ring summaries,
  and benchmark dossiers

---

## Why this matters

**Financial-crime intelligence is a relationship problem disguised as a
search problem.** A regulator does not ask *"give me documents about
this account"* — they ask *"who is laundering through this ring, and
how is the money moving."* That question has three properties that
make traditional retrieval the wrong tool:

1. The answer is an **edge**, not a sentence
2. The relevant entities **don't appear together** in any single document
3. Hidden relationships are **typed, not textual** (`SHARES_DEVICE_WITH`,
   `BENEFITS_FROM`)

VectorRAG retrieves chunks that *look like* the query. It cannot follow
typed edges, cannot promote ring siblings, cannot materialize the
join that *is* the answer.

The full reasoning is in [`10_research/01_problem_space.md`](./10_research/01_problem_space.md)
and [`10_research/04_vectorrag_limitations.md`](./10_research/04_vectorrag_limitations.md).

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│  8_dashboard_ui  (React/TS · Vite)                                       │
│  cinematic SSE flow · intent chip · recent investigations · benchmarks   │
└─────────────────────────────────┬────────────────────────────────────────┘
                                  │ HTTP + SSE
┌─────────────────────────────────▼────────────────────────────────────────┐
│  4_orchestrator_api  (FastAPI)                                           │
│  ├── /investigate, /investigate/stream            (SSE)                  │
│  ├── /investigate/deep, /investigate/deep/stream  (+ swarm + reasoning)  │
│  ├── /orchestrator/intent                         (pure-python)          │
│  ├── /investigations, /investigations/{id}        (disk archive)         │
│  ├── /benchmark/run|run/stream|ad-hoc|runs        (live benchmark)       │
│  ├── /ingest/environment, /ingest/sample, /promote                       │
│  └── orchestration/{sessions, result_cache, intent, archive, presets}    │
└─────────────────────────────────┬────────────────────────────────────────┘
                                  │
       ┌──────────────────┬───────┴────────┬──────────────────┐
       ▼                  ▼                ▼                  ▼
┌──────────────┐  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ 5_agent_     │  │ 6_reasoning_ │ │ 7_reporting_ │ │ 3_graph_     │
│   swarm      │  │   engine     │ │   engine     │ │ intelligence_│
│ 5 analysis   │  │ claims +     │ │ briefs +     │ │   core       │
│ agents +     │  │ contra-      │ │ ring +       │ │ engine +     │
│ coordinator  │  │ dictions     │ │ benchmark    │ │ retrievers + │
│              │  │              │ │              │ │ TG client    │
└──────────────┘  └──────────────┘ └──────────────┘ └──────┬───────┘
                                                            │
                          ┌─────────────────────────────────┴──┐
                          ▼                                    ▼
                 ┌──────────────────┐                ┌──────────────────┐
                 │  TigerGraph      │                │  outputs/        │
                 │  Cloud           │                │  {profile}/      │
                 │  (ShadowGraph)   │                │  csv + json      │
                 │  7v · 19+6e      │                │  + cross_refs    │
                 └──────────────────┘                └──────────────────┘
                          ▲                                    ▲
                          │ load_profile                       │ generates
                          │                                    │
   2_baseline_systems     │                                    │
   benchmark runner       └──────── 1_data_engine ─────────────┘
   (PureLLM | VectorRAG | GraphRAG · uses 3_/adapter)
```

Per-module responsibilities are documented in
[`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md). The design rationale —
why each decision was made and what was traded away — is in
[`10_research/03_architecture_decisions.md`](./10_research/03_architecture_decisions.md).

---

## Real measured results

From `scripts/adversarial_benchmark.py` (20 queries, profile `small`,
live TigerGraph Cloud):

| pipeline | structural evidence per query | avg tokens | avg retrieval ms | sources |
|---|---:|---:|---:|---:|
| **PureLLM** | **0** (no retrieval) | 22 | 0 | 0 |
| **VectorRAG** | **0** (text chunks only) | 554 | 14 | 10 text chunks |
| **GraphRAG** | **3+ structural edges on 20/20 queries** | 50 | 20,160 | 1 focused structural answer |

**The verdict:**
- **Substrate, not tuning.** VectorRAG cannot expose typed edges by
  definition. No embedding model recovers what isn't in the chunks.
- **GraphRAG pays real cost.** 20 s of real TigerGraph traversal per cold
  query, transparently surfaced as `avg_retrieval_ms`. The result cache
  brings warm replays to <50 ms.
- **GraphRAG uses 11× fewer tokens** than VectorRAG because the answer
  is a compact edge set, not a chunk pile.

Full methodology + non-claims: [`docs/BENCHMARK_METHOD.md`](./docs/BENCHMARK_METHOD.md)
and [`10_research/05_benchmark_methodology.md`](./10_research/05_benchmark_methodology.md).

---

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

The canonical schema source of truth is
[`3_graph_intelligence_core/validation/schema_def.py`](./3_graph_intelligence_core/validation/schema_def.py).

---

## Demo flow (5 min)

Detailed walkthrough in [`docs/DEMO_FLOW.md`](./docs/DEMO_FLOW.md).
Quick version:

1. **Sources page** (`/sources`) — environment readiness strip shows
   graph / topology / retrieval / benchmark / reasoning each as
   ready or honestly degraded. Click "investigate" to hand off into
   the workstation with a pre-seeded query.
2. **Home page** (`/home`) — type *"who is the most suspected"*
   into the custom investigation input. The intent chip surfaces
   `rank_suspects · 100%` instantly (pure-python). Submit.
3. **Workstation** (`/investigate`) — graph unfolds via SSE. Ranked
   suspects with topology evidence in the report panel. Press `4`
   to open `compare · 3 pipelines` and run the SAME question through
   all three pipelines.
4. **Benchmark page** (`/benchmark`) — `LiveBenchmarkConsole` runs
   the adversarial benchmark with one click; per-pipeline aggregates
   include judge scores and entity F1 when scoring is enabled.
5. **Recent investigations** (under custom input on `/home`) — disk-
   backed archive of every prior investigation, with env-snapshot
   chips showing graph drift vs current.

---

## Quickstart

> `make help` lists every target. The flow below is what a new engineer
> would run on first clone.

### 1. Environment

```bash
cp .env.example .env    # fill in TIGERGRAPH_HOST, TIGERGRAPH_GSQL_SECRET,
                        # TIGERGRAPH_GRAPH, optionally NIM_API_KEY
make install-all        # pip install + npm install in 8_dashboard_ui/
```

`.env.example` is the canonical source of every env var the platform
reads. Required vs optional is clearly marked.

### 2. Generate data (small profile, ~30 s)

```bash
make generate-data
# or: python -m 1_data_engine generate --profile small --new-pipeline
```

### 3. Build the enriched intelligence corpus (~1.5 s, free)

```bash
make enrich-corpus
# Output: outputs/small/enriched_corpus/small_intelligence.jsonl
#         35,402 grounded AML/compliance documents, ~6.1M tokens
```

Pure-python templates, deterministic, no LLM calls. Re-runs are
idempotent (same seed → identical output). See
[`10_research/07_semantic_enrichment_pipeline.md`](./10_research/07_semantic_enrichment_pipeline.md).

### 4. Load into TigerGraph

```bash
python -m 3_graph_intelligence_core load small
python -m 3_graph_intelligence_core health
```

### 5. Validate end-to-end

```bash
python3 scripts/tigergraph_validate.py
python3 scripts/benchmark_reliability.py --limit 5
python3 scripts/adversarial_benchmark.py --profile small
python3 scripts/benchmark_full_report.py --profile small
cat scripts/benchmark_full_report.md
```

### 6. Run the orchestrator + UI

```bash
# Terminal 1 — orchestrator API on :8000
make dev-backend

# Terminal 2 — dashboard dev server on :5173
make dev-frontend

# Optional: quick sanity check across all endpoints
make smoke-test
```

Open `http://localhost:5173`. The TopBar pill flips **LIVE** within
seconds. Use the Sources page (`/sources`) to verify environment
readiness, then run a custom investigation from Home (`/home`).

### 7. Investigate from the CLI

```bash
# Run the 5-agent swarm on a curated preset
python3 -m 5_agent_swarm --preset ring-identification

# Same query, deeper reasoning (claims + contradictions + rationale)
python3 -m 6_reasoning_engine --preset ring-identification

# Generate a production investigation brief (markdown + JSON)
python3 -m 7_reporting_engine brief --preset ring-identification
python3 -m 7_reporting_engine ring --ring FR-002
python3 -m 7_reporting_engine bench
```

A more detailed onboarding flow is in [`docs/QUICK_START.md`](./docs/QUICK_START.md).

---

## Repository structure

```
Shadow_Network_Intelligence/
├── 1_data_engine/                synthetic AML topology generator
├── 2_baseline_systems/           3-pipeline benchmark runner + scoring
├── 3_graph_intelligence_core/    TigerGraph client + GraphRAG engine + retrievers
├── 4_orchestrator_api/           FastAPI orchestrator · SSE · session · intent · archive
├── 5_agent_swarm/                5 analysis agents + SynthesisCoordinator
├── 6_reasoning_engine/           claims · contradictions · per-suspect rationale
├── 7_reporting_engine/           4 production report generators (md + json)
├── 8_dashboard_ui/               React/TS operational dashboard (Vite)
├── 9_devops/                     Docker compose + deploy scripts
├── 10_research/                  design philosophy · architecture decisions · failure register
│
├── scripts/                      adversarial benchmark · reliability · TG validation · enricher
├── docs/                         API reference · architecture · benchmark method · quick start · demo flow
├── shared/                       cross-module utilities (constants, prompts, logging)
├── cache/                        graph_cache · reports_cache · vector_cache (runtime)
├── outputs/                      generated data + benchmark artifacts + uploads (runtime)
├── configs/                      JSON/nginx configs (no secrets — those live in .env)
├── tests/                        unit + integration tests
│
├── .env.example                  template for required secrets
├── CLAUDE.md                     guidance for Claude Code agents
├── docker-compose.yml            Docker orchestration
├── Makefile                      dev shortcuts
└── requirements.txt              Python dependencies
```

---

## Documentation

Two layers:

**[`docs/`](./docs/)** — technical reference (what to call, how it works):
- [`API_REFERENCE.md`](./docs/API_REFERENCE.md) — orchestrator + benchmark endpoints
- [`ARCHITECTURE.md`](./docs/ARCHITECTURE.md) — module responsibilities + cross-module rules
- [`BENCHMARK_METHOD.md`](./docs/BENCHMARK_METHOD.md) — mechanical methodology + reproducibility checklist
- [`DEMO_FLOW.md`](./docs/DEMO_FLOW.md) — 5-minute live demo script
- [`QUICK_START.md`](./docs/QUICK_START.md) — onboarding

**[`10_research/`](./10_research/)** — design philosophy (why decisions were made):
- [`01_problem_space.md`](./10_research/01_problem_space.md)
- [`02_why_graphrag.md`](./10_research/02_why_graphrag.md)
- [`03_architecture_decisions.md`](./10_research/03_architecture_decisions.md)
- [`04_vectorrag_limitations.md`](./10_research/04_vectorrag_limitations.md)
- [`05_benchmark_methodology.md`](./10_research/05_benchmark_methodology.md) (philosophy)
- [`06_operational_investigations.md`](./10_research/06_operational_investigations.md)
- [`07_semantic_enrichment_pipeline.md`](./10_research/07_semantic_enrichment_pipeline.md)
- [`08_system_evolution.md`](./10_research/08_system_evolution.md)
- [`09_failure_cases.md`](./10_research/09_failure_cases.md) — operational honesty register
- [`10_future_work.md`](./10_research/10_future_work.md)

---

## What this platform does NOT do

A reviewer should know the non-claims as clearly as the claims. The
full register is in [`10_research/09_failure_cases.md`](./10_research/09_failure_cases.md);
the headline non-claims:

- **No fake multi-tenancy.** One live TG graph; uploads merge by vertex ID
- **No fake rollback.** Promoted uploads are non-reversible
- **No fake connector simulation.** Planned connectors are labelled
  "planned · adapter not enabled" with no action buttons
- **No invented graph replay.** Replay re-runs the query against the
  current graph; drift is honestly surfaced via the env-snapshot chip
- **No fabricated metrics.** Mock LLM is labelled mock; offline fallback
  is labelled offline; missing benchmark artifacts return HTTP 404 with
  the regeneration command
- **No chatbot drift.** Unmapped queries get a structured "intent
  unknown" response with operational suggestions — never free-form prose

---

## Performance characteristics

| Operation | Cold | Warm (cache hit) |
|---|---:|---:|
| Boot (orchestrator + entity prewarm) | ~40 s | n/a |
| Boot (with preset prewarm) | 60–180 s | n/a |
| `engine.query` | 7–23 s | n/a (cached at orchestrator level) |
| `orchestrator.investigate` | 7–23 s | **<50 ms** |
| `agent_swarm.run` | +50 ms | +50 ms |
| `reasoning.synthesize` | +10 ms | +10 ms |
| `reporting brief` | +50 ms | <60 ms total |

Tuning knobs:

```bash
SNI_RESULT_CACHE_ENABLED=1   # default true
SNI_RESULT_CACHE_SIZE=64     # LRU max entries
SNI_RESULT_CACHE_TTL=300     # seconds
SNI_PREWARM_ON_START=1       # default true
SNI_PREWARM_TOP_N=30         # entities to warm
SNI_INVESTIGATION_ARCHIVE_MAX=200   # disk-backed cap
```

---

## Adversarial benchmark suite

20 queries in `scripts/adversarial_queries.json` covering:

ring identification · hidden beneficial owners · shared-infrastructure
collusion · shared-device clusters · multi-hop laundering chains ·
funnel patterns · circular ownership rings · cross-ring participants ·
in-ring transactions · hidden controllers · centrality · indirect paths
· sanctions exposure · intermediary discovery · cross-case linkage ·
ring reconstruction · nominee directors · fan-out dispersion · ring
proximity · latent relationships

**Every single one requires multi-hop graph traversal or hidden-
relationship discovery.** VectorRAG produces 0/20 structural answers
by definition. See [`10_research/04_vectorrag_limitations.md`](./10_research/04_vectorrag_limitations.md)
for the categorical reasoning.

---

## Tech stack

| Layer | Technology |
|---|---|
| Graph DB | TigerGraph Cloud (Savannah) |
| Graph client | pyTigerGraph 2.0.3 (with explicit token-refresh workaround) |
| Vector store | ChromaDB (VectorRAG baseline) |
| Embeddings | NVIDIA NIM (default), Ollama or mock supported |
| LLM | Mock by default (deterministic); Anthropic/OpenAI/Ollama via `LLMClient` |
| API | FastAPI + uvicorn + SSE via StreamingResponse |
| Frontend | React 19 + TypeScript + Vite 8 + zustand + cytoscape + framer-motion |
| Deploy | Docker Compose ([`9_devops/`](./9_devops/)) |

---

## Thesis

VectorRAG retrieves text. GraphRAG retrieves *structure*.

When the answer to *"who launders for this ring"* is a 3-hop join
across `PERSON_MEMBER_OF_RING → SHARES_ADDRESS_WITH → OWNS`, no
amount of context window can recover it from chunked text. The graph
join is the answer.

That is what this platform proves — quantitatively, reproducibly,
and operationally.

---

## License

Apache 2.0
