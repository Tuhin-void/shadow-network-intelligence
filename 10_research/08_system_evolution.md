# 08 — System Evolution

How the platform grew. Each phase below records *what problem it solved*
and *what it left in place*. Reading this gives a maintainer the causal
chain — why systems exist the way they do.

## Phase 1 — Data engine + 3-pipeline benchmark

**What was built:**
- `1_data_engine/` — synthetic AML topology generator
- `2_baseline_systems/` — three pipelines (PureLLM, VectorRAG, GraphRAG)
  + a `BenchmarkRunner` that runs the same queries through all three
- `3_graph_intelligence_core/` — initial GraphRAG engine with entity-
  centric retrieval and basic neighborhood expansion

**What it proved:**
The mechanical comparison works. GraphRAG returns structural evidence;
VectorRAG returns text chunks; PureLLM returns priors. The substrate
choice dominates.

**What it left in place:**
The benchmark was a CLI-only artifact. Reviewers had to read JSON.

## Phase 2 — Live TigerGraph deployment

**What was built:**
- Live TigerGraph Cloud (`ShadowGraph`) instance
- `GraphClient` with pyTigerGraph + offline fallback
- Per-process neighbor cache (60s TTL)
- 19 forward + 6 reverse edge types
- GSQL installed procedures (`tg_ring_members`, `tg_shortest_path`)
- `SchemaValidator` to compare live schema vs `schema_def.py`

**What it solved:**
Made the comparison reproducible against real graph infrastructure, not
just an in-memory simulation.

**What it left in place:**
The 7–23s cold latency for graph traversal. Acceptable — the result
cache (Phase 3) addresses this on the warm path.

## Phase 3 — Orchestrator + SSE streaming

**What was built:**
- `4_orchestrator_api/` (FastAPI) with `/investigate`, `/investigate/stream`
- `InvestigationOrchestrator` (thin layer over GraphRAGEngine)
- Result cache (LRU 64 × TTL 300s) wrapping `engine.query`
- Per-process prewarm (top 30 entities at boot)
- Session lifecycle (open / record reports / list / close)
- Investigation events emitted in order so a UI can render the
  investigation "unfolding"

**What it solved:**
Made the platform feel like a live system. SSE streaming lets the UI
render an investigation as it happens.

**What it left in place:**
Sessions were process-local. A backend restart lost session memory.
Phase 5 addressed this with the disk-backed archive.

## Phase 4 — Cognitive layer + agent swarm

**What was built:**
- `5_agent_swarm/` — 5 narrow analysis agents + `SynthesisCoordinator`
  (composes the engine, doesn't re-implement retrieval)
- `6_reasoning_engine/` — claim extraction, contradiction detection,
  structural confidence, per-suspect explanations
- `7_reporting_engine/` — 4 production report generators (briefs, ring
  summaries, sanctions exposure, benchmark dossiers)
- `/investigate/deep` and `/investigate/deep/stream` — composed
  retrieval + swarm + reasoning over the SAME engine_result (no
  duplicate retrieval cost)

**What it solved:**
A standard investigation now has a structured explanation, not just a
list of entities. Reasoning surfaces *why* an entity is a suspect.

**What it left in place:**
The cognitive layer was not stored with the investigation. A session
could be replayed for graph events but not for cognitive findings.
Phase 5 attached `deep_report` to the archive.

## Phase 5 — Persistent intelligence archive

**What was built:**
- `InvestigationArchive` (disk-backed, append-only)
- `IntentClassifier` (pure-python, 8 first-class workflows)
- Investigation record stamped with intent + environment snapshot
- Recent Investigations panel in the UI
- `compare · 3 pipelines` tab — ad-hoc 3-pipeline comparison on the
  current analyst query (`POST /benchmark/ad-hoc`)
- Frontend `IntentChip` (debounced live intent preview)

**What it solved:**
Custom investigations became persistent operational artifacts. The
analyst now has memory across sessions and restarts.

**What it left in place:**
Replay is "re-run the query," not "restore the snapshot." Honest by
design — we document drift via the env-snapshot chip.

## Phase 6 — Operational environment system

**What was built:**
- `EnvironmentReadinessStrip` — single operational verdict
  (graph/topology/retrieval/benchmark/reasoning)
- `SourceHandoffStrip` — operational transitions from Sources page
  into investigate/benchmark/topology with `?q=` seed
- `OperationalConnectorPanel` — TigerGraph + CSV connectors expose real
  actions; planned connectors are labelled "planned" (no fake LIVE chip)
- Auto-poll of `/ingest/environment` every 15s + instant invalidation
  when `tigergraphOffline` flips
- `?probe=true` parameter on `/ingest/environment` for forced TG
  round-trip (catches "cached online flag is stale" cases)

**What it solved:**
The Sources page stopped being a static gallery and became the
operational launcher into the rest of the platform. The "connected"
badge stopped being optimistic.

**What it left in place:**
The platform has one TG graph. No multi-environment isolation. See
[09_failure_cases.md](./09_failure_cases.md#no-fake-multi-tenancy).

## What we have now

Reading the phases backwards, the platform is:
- A live GraphRAG engine on real TigerGraph
- A benchmark that compares it honestly against VectorRAG and PureLLM
- An orchestrator that turns analyst questions into ranked structural
  output via SSE
- A disk-backed archive of every investigation
- A UI that surfaces all of this without inventing what isn't there

The numbered modules (`1_..` through `10_..`) reflect this growth.
Each module is independently runnable, and the inter-module contracts
have stayed narrow throughout — typed dataclasses or HTTP, nothing else.

## What we'd do differently

Smaller items, recorded for an eventual rewrite:

- **Session store would be Redis-backed from the start.** Disk JSON
  is fine for a research repo; production would want sub-ms session
  reads across multiple backend instances.
- **Embeddings would be cached in TG itself** (a TG vertex attribute)
  rather than in a separate Chroma index. That removes the parity
  problem between VectorRAG and GraphRAG corpora.
- **The intent classifier would emit a `workflow_id`** that the engine
  reads and uses to bias rerank weights. Today the intent label is
  reported but not yet wired into the retriever's rerank function.
  See [10_future_work.md](./10_future_work.md).
