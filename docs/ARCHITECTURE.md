# Architecture

> The system is 10 numbered modules. Each is independently runnable and
> communicates with its neighbors through narrow, typed interfaces.

```
┌───────────────────────────────────────────────────────────────────────────┐
│   8_dashboard_ui                                                          │
│   React + TS · Vite · Worldspace + TacticalRail UX · Cognitive panel      │
│   Adapter-only integration  →  /lib/api-client + /lib/adapters/*          │
└─────────────────────────────────┬─────────────────────────────────────────┘
                                  │ HTTP + SSE
┌─────────────────────────────────▼─────────────────────────────────────────┐
│   4_orchestrator_api  (FastAPI)                                           │
│   ├── api/investigate      (/investigate, /investigate/stream, /sessions) │
│   ├── api/demo             (/demo/presets, /demo/run|stream/{key})        │
│   ├── api/cognitive        (/investigate/deep, /investigate/deep/stream)  │
│   ├── api/health, alerts, reports, benchmark, search                      │
│   └── orchestration/       (lifecycle, sessions, result_cache, presets)   │
└─────────────────────────────────┬─────────────────────────────────────────┘
                                  │
       ┌──────────────────┬───────┴────────┬──────────────────┐
       ▼                  ▼                ▼                  ▼
┌──────────────┐  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ 5_agent_     │  │ 6_reasoning_ │ │ 7_reporting_ │ │ 3_graph_     │
│   swarm      │  │   engine     │ │   engine     │ │ intelligence_│
│              │  │              │ │              │ │   core       │
│ 5 narrow     │  │ Claims +     │ │ 4 markdown + │ │              │
│ analysis     │  │ contra-      │ │ JSON gens:   │ │ GraphRAG     │
│ agents +     │  │ dictions +   │ │ brief, ring, │ │ engine,      │
│ coordinator  │  │ confidence + │ │ sanc, bench  │ │ retrievers,  │
│              │  │ explanations │ │              │ │ TG client    │
└──────────────┘  └──────────────┘ └──────────────┘ └──────┬───────┘
                                                            │
                          ┌─────────────────────────────────┴──┐
                          ▼                                    ▼
                 ┌──────────────────┐                ┌──────────────────┐
                 │  TigerGraph      │                │  outputs/        │
                 │  Cloud           │                │  {profile}/csv/  │
                 │  (ShadowGraph)   │                │  + json/         │
                 │  7 v · 19+6 e    │                │  + cross_refs/   │
                 └──────────────────┘                └──────────────────┘
                          ▲                                    ▲
                          │ load_profile                       │ generates
                 ┌────────┴────────┐                           │
                 │  ingestion/     │ ◄── 1_data_engine + scripts/data_corpus_enricher.py
                 │  loader         │
                 └─────────────────┘

   2_baseline_systems     →   benchmark runner  (PureLLM | VectorRAG | GraphRAG)
                              uses 3_graph_intelligence_core/adapters/tigergraph_adapter

   scripts/               →   adversarial benchmark, reliability,
                              TG validation, consolidator, enricher
```

## Module responsibilities

| Module | Owns | Doesn't own |
|---|---|---|
| `1_data_engine/` | synthetic AML topology generation, fraud-ring patterns, CSV/JSON export | retrieval, LLM, UI |
| `2_baseline_systems/` | benchmark orchestration over 3 pipelines, query loader, scoring | graph engine internals (uses adapter) |
| `3_graph_intelligence_core/` | TigerGraph client, schema, GraphRAG engine, retrievers, GSQL queries | benchmark orchestration, UI |
| `4_orchestrator_api/` | FastAPI app, session lifecycle, SSE streaming, result cache, preset routes | retrieval (delegates to 3_), agents (delegates to 5_) |
| `5_agent_swarm/` | 5 narrow analysis agents + SynthesisCoordinator (composes the engine) | LLM agents — these are deterministic Python passes |
| `6_reasoning_engine/` | claim extraction, contradiction detection, structural confidence, entity explainer | retrieval, UI |
| `7_reporting_engine/` | 4 production report generators (markdown + JSON) | retrieval, agents — pure projection |
| `8_dashboard_ui/` | React workspace, Worldspace + TacticalRail, cognitive panel, adapters | backend — only consumes API |
| `9_devops/` | Docker compose, deploy scripts | runtime logic |
| `scripts/` | benchmark runners, validators, consolidator, corpus enricher | platform code |

## Cross-module rules

- **Schema source of truth:** `3_graph_intelligence_core/validation/schema_def.py`.
  Any schema change is reflected here first.
- **Data sync point:** `outputs/{profile}/csv/`. `2_baseline_systems` reads
  here via `AdaptiveDataLoader`.
- **No direct backend ↔ frontend coupling:** frontend imports only through
  `8_dashboard_ui/src/lib/api-client.ts` + `lib/adapters/*`. Backend never
  imports frontend code.
- **Secrets:** only in `.env` at the project root. `config.yaml` placeholders
  are empty strings.
- **Cache layers (in process):**
  1. GraphClient neighbor cache (60s TTL)
  2. GraphRAGEngine prewarm (138 entities at boot)
  3. Orchestrator result cache (LRU 64 × TTL 300s) ← wraps `engine.query`

## TigerGraph schema (live)

7 vertex types · 19 forward edges · 6 reverse edges (for backward traversal
from FraudRing).

```
Person ── OWNS / BENEFITS_FROM ─────────► Company
Person ── HAS_ACCOUNT ─────────────────► Account
Account ── TRANSFERRED_TO ────────────► Account
Account ── SENT/RECEIVED_TRANSACTION ─► Transaction
Person / Company ── LOCATED_AT ───────► Address
Person ── USES_DEVICE ────────────────► Device
Person / Company / Account / Transaction ── *_MEMBER_OF_RING ──► FraudRing
Device / Address ── *_CONNECTED_TO_RING ──► FraudRing
+ reverse_* edges enable FraudRing → members traversal
```

All 6 explicit ring-membership edge types (not polymorphic) and reverse
edges materialized at load time.

## Performance characteristics

| Operation | Cold | Warm (cache hit) |
|---|---:|---:|
| Boot (orchestrator + entity prewarm) | ~40s | n/a |
| Boot (with preset prewarm) | 60-180s | n/a |
| `engine.query` | 7-23s | n/a (cached at orchestrator level) |
| `orchestrator.investigate` | 7-23s | **<50ms** |
| `agent_swarm.run` | adds ~50ms | adds ~50ms |
| `reasoning.synthesize` | adds ~10ms | adds ~10ms |
| `reporting brief` | adds ~50ms file write | <60ms total |

## Stack

| Layer | Technology |
|---|---|
| Graph DB | TigerGraph Cloud (Savannah) |
| Graph client | pyTigerGraph 2.0.3 (with explicit token-refresh workaround) |
| Vector store | ChromaDB (for VectorRAG baseline) |
| Embeddings | NVIDIA NIM (default), Ollama or mock supported |
| LLM | Mock by default (for deterministic benchmarks); Anthropic/Ollama/OpenAI supported via `LLMClient` |
| API | FastAPI + uvicorn + SSE via StreamingResponse |
| Frontend | React 19 + TypeScript + Vite 8 + zustand + cytoscape + framer-motion |
| Deploy | Docker Compose (`9_devops/`) |
