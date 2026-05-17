# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Generate synthetic data
python -m 1_data_engine generate --profile small --new-pipeline   # fast, ~25k entities
python -m 1_data_engine generate --profile hackathon_default      # full dataset

# Run the benchmark (primary workflow)
python -m 2_baseline_systems benchmark --profile small --limit 5 \
  --approaches pure_llm vector_rag graph_rag \
  --embedder nim --llm mock \
  --vector-provider chroma --graph-provider tigergraph

# Mock everything locally (no external deps)
python -m 2_baseline_systems benchmark --profile small --limit 3 \
  --embedder mock --llm mock --vector-provider mock --graph-provider mock

# TigerGraph health / schema / load
python -m 3_graph_intelligence_core health
python -m 3_graph_intelligence_core validate
python -m 3_graph_intelligence_core load small
python -m 3_graph_intelligence_core stats
python -m 3_graph_intelligence_core query "Find accounts connected to fraud rings"

# Benchmark utilities
python -m 2_baseline_systems graph-stats --profile small
python -m 2_baseline_systems list
python -m 2_baseline_systems report --run-id RUN_<id>

# Run tests
pytest tests/ -v
pytest tests/unit/ -v
pytest tests/integration/ -v

# Make shortcuts
make generate-data       # small profile
make docker-up           # start TigerGraph + ChromaDB via Docker
make clean               # wipe __pycache__, outputs, cache
```

## Environment Setup

The canonical secrets file is `.env` at the project root. Secrets are **never** in `config.yaml` — that file has empty strings as placeholders.

Required `.env` keys:
- `TIGERGRAPH_GSQL_SECRET` — TigerGraph Cloud RESTPP secret (from portal → Graph Settings → RESTpp)
- `TIGERGRAPH_HOST` — Cloud instance URL
- `NIM_API_KEY` — NVIDIA NIM embeddings + LLM

Config is loaded by `3_graph_intelligence_core/configs/config.py` via `load_config()`, which reads `config.yaml` then overlays all `TIGERGRAPH_*`, `NIM_API_KEY`, `OLLAMA_*` env vars. The config object is a singleton — call `get_config()` after first load.

## Architecture

The system has three independently runnable modules that interact through explicit interfaces:

```
1_data_engine/          → generates synthetic AML/fraud CSVs + JSONs
        ↓ outputs/{profile}/csv/
2_baseline_systems/     → benchmark harness (PureLLM vs VectorRAG vs GraphRAG)
        ↑ adapters via 3_graph_intelligence_core/adapters/tigergraph_adapter.py
3_graph_intelligence_core/  → TigerGraph client + GraphRAG engine
```

### 1_data_engine

Two generation pipelines exist:
- **New pipeline** (preferred): `--new-pipeline` flag → `orchestration/PipelineOrchestrator` → writes to `outputs/{profile}/csv/` and `outputs/{profile}/json/`
- **Legacy pipeline**: older path through `generators/entity_factory.py`

Output CSVs are the sync point. `2_baseline_systems` reads them via `AdaptiveDataLoader`, which auto-invokes `1_data_engine/main.py` if data is missing. Profiles (`small`, `medium`, `hackathon_default`) control entity counts.

### 2_baseline_systems

The benchmark runner (`benchmarking/BenchmarkRunner`) orchestrates three pipelines against the same query set from `benchmarking/query_loader.py`:

| Pipeline | Class | Provider arg |
|----------|-------|-------------|
| PureLLM | `pipelines/pure_llm.py` | (no retrieval) |
| VectorRAG | `pipelines/vector_rag.py` | `--vector-provider chroma\|mock` |
| GraphRAG | `pipelines/graph_rag.py` | `--graph-provider tigergraph\|mock` |

`shared/` contains the components shared across all pipelines: `AdaptiveDataLoader`, `Embedder` (ollama/openai/nim/mock), `LLMClient` (ollama/openai/anthropic/mock), `VectorStore` (chroma/mock), `DocumentBuilder`, `TokenTracker`.

GraphRAG connects to `3_graph_intelligence_core` via `3_graph_intelligence_core/adapters/tigergraph_adapter.py::GraphRAGAdapter`, which wraps `GraphRAGEngine` to match the `search(query, top_k, depth) → {subgraph, vector_results, context}` interface.

### 3_graph_intelligence_core

The graph intelligence layer. Key files:

- **`clients/graph_client.py`** — `GraphClient` wraps pyTigerGraph. Has `OfflineFallback` that activates automatically when TigerGraph is unreachable (500/403/network error). Auth: `gsqlSecret + tgCloud=True`; **must call `conn._refresh_auth_headers()` after `conn.getToken()`** due to a pyTigerGraph v2.0.3 bug where `_cached_auth` is not updated post-`getToken`.
- **`configs/config.py`** — `Config` dataclass singleton. `load_config()` reads YAML then env. `get_config()` returns cached instance.
- **`graph_rag/graphrag_engine.py`** — `GraphRAGEngine.query(text)` is the main retrieval entry point: entity extraction → graph traversal → context compression → answer.
- **`retrievers/`** — pluggable retrieval strategies: `EntityCentricRetriever`, `NeighborhoodRetriever`, `PathAwareRetriever`, `HybridRetriever`, `CommunityRetriever`.
- **`ingestion/loader.py`** — `GraphLoader.load_profile(profile)` reads from `outputs/{profile}/csv/` and upserts via `GraphClient`.
- **`validation/schema_def.py`** — **canonical schema source of truth**. `VERTEX_TYPES` list and `EDGE_TYPES` list define the live TigerGraph schema. All layers must stay in sync with this file.
- **`validation/schema_validator.py`** — `SchemaValidator` compares live TigerGraph schema against `schema_def.py`.

### TigerGraph Cloud (ShadowGraph)

Live instance: TigerGraph Cloud, graph name `ShadowGraph`.

**Current live schema** (7 vertices, 19 edges) — kept in `3_graph_intelligence_core/validation/schema_def.py`:

Vertices: `Person`, `Company`, `Account`, `Address`, `Device`, `Transaction`, `FraudRing`

FraudRing membership edges use per-type explicit edges (not polymorphic):
- `PERSON_MEMBER_OF_RING`, `COMPANY_MEMBER_OF_RING`, `ACCOUNT_MEMBER_OF_RING`
- `TRANSACTION_MEMBER_OF_RING`, `DEVICE_CONNECTED_TO_RING`, `ADDRESS_CONNECTED_TO_RING`

**Deprecated edges** (removed from live schema, must not exist in code): `MEMBER_OF_RING`, `CONNECTED_TO_RING`, `PART_OF`.

### Offline Fallback

`GraphClient` silently switches to `OfflineFallback` on any connection failure. Health check will report `Mode: OFFLINE` with `healthy: True`. The benchmark still runs in this mode using local dataset data. This is intentional — never remove it.

### Data Profiles

| Profile | Persons | Companies | Accounts | Use |
|---------|---------|-----------|---------|-----|
| `small` | 6,000 | 5,000 | 10,000 | dev/CI, adversarial benchmark default |
| `hackathon_default` | 6,000 | 5,000 | 10,000 | demo |
| `benchmark_dense` | 12,000 | 8,000 | 20,000 | 1.2M–2.4M token corpus, adversarial-grade |

## Key Constraints

- `schema_def.py` is the single source of truth for schema. Any TigerGraph schema change must be reflected here first.
- `AdaptiveDataLoader` (in `2_baseline_systems/shared/`) is the only correct way to load data for benchmarks — it handles caching and auto-generation.
- Benchmark results are saved to `2_baseline_systems/outputs/benchmark_results/benchmark_<RUN_ID>.json` and are immutable after creation.
- All three pipelines must run the same queries for benchmark comparability. Never add pipeline-specific query filtering that isn't applied to all pipelines.
- `config.yaml` passwords/secrets are always empty strings — real values come only from `.env`.
