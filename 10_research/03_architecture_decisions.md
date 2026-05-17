# 03 — Architecture Decisions

Each decision below records *what was chosen* and *what was traded away*.
Architecture is a series of accepted constraints; this document makes them
explicit.

## D1 — Numbered, independently runnable modules

The repo is organized as `1_data_engine/`, `2_baseline_systems/`,
`3_graph_intelligence_core/`, etc. Numbers establish dependency direction.

**Why:**
- Each module can be exercised in isolation via `python -m <module>`
- A reviewer can read modules in order without losing causality
- Inter-module contracts are narrow — typed dataclasses or HTTP

**What we traded:**
- Module names lead with digits, which annoys Python tooling that expects
  importable package names. We work around this with `sys.path` injection
  at runtime entrypoints — never inside business logic.

## D2 — TigerGraph as the source of structural truth

All graph state lives in a live TigerGraph Cloud instance. The platform
doesn't carry a parallel in-memory graph.

**Why:**
- TG enforces typed edges, reverse-traversal indexes, and GSQL-installed
  procedures (`tg_ring_members`, `tg_shortest_path`)
- Schema changes go through one file —
  [`schema_def.py`](../3_graph_intelligence_core/validation/schema_def.py)
- Reverse edges (`member_of_ring_reverse`, etc.) are materialized at
  load time so backward traversal from `FraudRing` works in one hop

**What we traded:**
- Cold-cache investigations have to pay 7–23s of real network +
  traversal latency. We accept this and use a result cache for warm
  paths (see D5).

## D3 — Schema definition is one file, not a database introspection

`schema_def.py` exports `VERTEX_TYPES` and `EDGE_TYPES` as Python
constants. The schema validator (`SchemaValidator`) compares this against
the live TG schema and surfaces drift.

**Why:**
- A code review on a schema change has one diff to look at
- Tests can run against a fake schema without a TG connection
- The data engine, the loader, and the retrievers all read from the
  same source

**What we traded:**
- Anybody adding a new edge type in TG without updating `schema_def.py`
  will see a validator failure. Good — the source of truth catches drift.

## D4 — Offline fallback is a first-class mode, not an error path

When TigerGraph is unreachable, `GraphClient` silently switches to
`OfflineFallback` (backed by the local CSV dataset). Investigations
still run, just against the in-memory shadow graph.

**Why:**
- A demo with the network down should still demonstrate the engine
- Local development doesn't require a TG instance
- CI can run benchmarks without secrets

**What we traded:**
- We document this prominently so it's never mistaken for live data
  (status pill shows `Mode: OFFLINE`, healthy=true). See
  [09_failure_cases.md](./09_failure_cases.md#offline-fallback).

## D5 — Three layers of caching, each with a job

| Layer | What it caches | Why |
|---|---|---|
| GraphClient neighbor cache (60s TTL) | per-vertex neighbor lookups | repeated traversals from same entity |
| GraphRAGEngine prewarm (138 entities at boot) | initial entity scoring | first preset click is fast |
| Orchestrator `ResultCache` (LRU 64 × TTL 300s) | full `engine.query` results | preset re-runs are <50ms |

**Why three?**
Different access patterns. Per-vertex lookups deduplicate within one
query; result cache deduplicates across queries.

**What we traded:**
- Stale-cache risk when the underlying graph mutates. We accept this for
  short-lived caches (≤300s) and document the env-snapshot drift indicator
  in the Recent Investigations panel for longer-lived staleness.

## D6 — Frontend is adapter-only

The React app imports backend types only through
`8_dashboard_ui/src/lib/api-client.ts` and the shape-narrowing adapters
in `lib/adapters/`. It never imports Python.

**Why:**
- Frontend and backend can evolve independently
- Type drift is caught at the adapter boundary, not deep in components
- Backend can ship language-independent contracts (JSON over HTTP/SSE)

**What we traded:**
- Some types are written twice (Python dataclass + TS interface). The
  cost is repetitive but the gain in decoupling justifies it.

## D7 — Result-cache wraps `engine.query`, not individual retrievers

The cache key is `(query, top_k, depth, strategy)`. We cache the
**full engine output**, not the retriever outputs.

**Why:**
- A single cache hit short-circuits the entire pipeline
- Retriever-level caching would still pay rerank + context-build cost
- The orchestrator's `investigate_stream` and the cognitive layer's
  `_build_deep_report` both go through the same cache key, so a warm
  preset is warm everywhere

**What we traded:**
- We cannot cache "this retriever, this query" independently. Acceptable.

## D8 — Investigation archive is disk-backed, append-only

`InvestigationArchive` (in
[`4_orchestrator_api/orchestration/archive.py`](../4_orchestrator_api/orchestration/archive.py))
writes one JSON file per investigation under
`outputs/investigations/`.

**Why:**
- Survives backend restart
- Browsable by an analyst from the Recent Investigations panel
- Independent of session memory — sessions still exist for short-lived
  state, but the long-term record is on disk

**What we traded:**
- 200-entry bounded prune. Older investigations are dropped automatically.
  Acceptable for an analyst workstation; not acceptable for a regulator
  archive (which is out of scope for this platform).

## D9 — Intent classifier is pure-python, no LLM

`IntentClassifier` ([`orchestration/intent.py`](../4_orchestrator_api/orchestration/intent.py))
maps analyst queries to first-class workflows using regex + token rules.
Sub-millisecond, deterministic.

**Why:**
- LLM-based intent routing would add ~500ms per query
- Classification logic must be auditable
- 8 workflows cover the analyst surface; unknown queries get suggested
  workflows (operational, not chatbot)

**What we traded:**
- No nuanced intent understanding. We accept this — the workflows are a
  small enough vocabulary that rules outperform an LLM on latency and
  predictability.

## D10 — Benchmark JSON files are immutable

`benchmark_RUN_<ID>.json` files are write-once. The API reads them; nothing
mutates them after creation.

**Why:**
- A reviewer can re-derive any reported number from the same artifact
- Cross-validating frontend → backend → JSON is one round of `cat | jq`
- We don't have to worry about "did this metric drift since I last read it"

**What we traded:**
- Disk grows monotonically until the user prunes. We expose the directory
  size + cap recommendations via `/benchmark/runs` for self-management.

## D11 — Honest readiness signals, never optimistic

The `/ingest/environment` endpoint returns a structured `readiness` block
(graph / topology / retrieval / benchmark / reasoning) with per-signal
`reason` strings. The UI never fabricates green dots.

**Why:**
- "Connected" should not appear when the underlying surface is broken
- A reviewer can click any dot and see *why* it's claiming ready
- When TG flips offline, the UI invalidates immediately — no stale optimism

**What we traded:**
- More fields on the env endpoint. Acceptable; payload stays under 2KB.

## What we did NOT do (and why)

- **No fake multi-environment isolation.** The platform has one live TG
  graph. Adding an environment selector that does nothing would be
  theater. See [09_failure_cases.md](./09_failure_cases.md).
- **No agentic intent router.** Rules outperform LLMs on this vocabulary.
- **No semantic answer re-ranking with a reranker model.** Topology rerank
  is the structural answer; we don't muddy it with a secondary lexical pass.
- **No "switch back to sample only" affordance.** TG upserts are
  idempotent merges, not isolated namespaces — rollback would require
  schema-level vertex tagging that's out of scope.
