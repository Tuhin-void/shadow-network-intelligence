# API Reference

Backend: FastAPI at `http://localhost:8000` · base prefix `/api/v1`.

**No authentication** in the local development build. Add it before public
deployment (the orchestrator exposes the engine directly).

OpenAPI/Swagger: **http://localhost:8000/docs**

## Operational endpoints

### `GET /api/v1/health`
Simple liveness probe.

```json
{"status": "healthy", "timestamp": "2026-05-17T01:50:54.997295", "version": "1.0.0"}
```

### `GET /api/v1/orchestrator/status`
Cache + prewarm + TigerGraph state.

```json
{
  "offline_mode": false,
  "session_count": 0,
  "prewarm": {"candidates": 138, "neighbors_warmed": 138, "topo_warmed": 90, "ms": 40412.9},
  "preset_prewarm": {},
  "cache_hits": 90,
  "cache_misses": 138,
  "result_cache": {
    "enabled": true,
    "entries": 0,
    "max_entries": 64,
    "ttl_seconds": 300,
    "hits": 0,
    "misses": 0,
    "evictions": 0,
    "hit_rate": 0.0
  }
}
```

## Investigation endpoints

### `POST /api/v1/investigate`
Synchronous investigation. Returns the 9-section structured report.

```json
{
  "query": "Identify members of fraud ring FR-002",
  "session_id": null,
  "top_k": 5,
  "depth": 2,
  "strategy": "auto"
}
```

Response includes: `suspects`, `hidden_relationships`, `ring_connections`,
`ownership_flow`, `transaction_flows`, `shared_infrastructure`,
`traversal_paths`, `structural_signals`, `evidence_chain`, `narrative`.

### `POST /api/v1/investigate/stream`
SSE stream of investigation events. Event kinds, in order:

```
session.started → query.received → (prewarm.done?)
entity.found × N
ring.discovered (if applicable)
hidden_relationship.found (if applicable)
ring.member_promoted (if applicable)
neighborhood.expanded
traversal.path × M (if paths surfaced)
evidence.collected
report.finalized
stream.end
```

## Cognitive endpoints (agent swarm + reasoning)

### `POST /api/v1/investigate/deep`
Synchronous deep investigation. Same body as `/investigate`. Returns:

```json
{
  "query": "...",
  "elapsed_ms": 8234,
  "investigation": { /* 9-section report */ },
  "swarm": {
    "agents": [
      {"agent": "retrieval_analyst", "confidence": 1.0, "summary": "5 suspects · 62 neighbors · 62 structural edges", "metrics": {...}},
      {"agent": "graph_topology_investigator", "confidence": 1.0, ...},
      {"agent": "sanctions_exposure_tracer", "confidence": 0.15, ...},
      {"agent": "fraud_ring_analyst", "confidence": 0.40, ...}
    ],
    "coordinator_summary": "Investigation surfaced 5 suspects across 62 neighbors with 62 structural edges. 1 ring(s) touched."
  },
  "reasoning": {
    "overall_confidence": 0.793,
    "headline": "...",
    "key_claims": [{"statement": "...", "basis": "ring", "confidence": 0.9, "refs": ["P-005027", "FR-002"]}],
    "contradictions": [],
    "explanations": {"P-005027": "rerank reason: member of ring FR-002 · ring proximity: 1"}
  },
  "metadata": {"engine_cache_hit": true, "agent_count": 4, "claim_count": 18, "contradiction_count": 0, "overall_confidence": 0.793}
}
```

### `POST /api/v1/investigate/deep/stream`
SSE deep stream. Investigation events + `agent.finished × 4` +
`reasoning.synthesized` + `deep_report.finalized`.

## Curated demo endpoints

### `GET /api/v1/demo/presets`
List of 8 curated demo investigations.

```json
{"presets": [
  {"key": "ring-identification", "title": "Identify members of fraud ring FR-002", "showcases": ["reverse-edge traversal", "ring-member promotion"]},
  {"key": "hidden-beneficial-owner", ...},
  ...
]}
```

### `POST /api/v1/demo/run/{preset_key}`
Synchronous run of a curated preset. Body: `{"session_id": null}`.

### `POST /api/v1/demo/stream/{preset_key}`
SSE variant of a curated preset.

### `POST /api/v1/demo/deep/{preset_key}`
Cognitive deep run for a curated preset.

## Session management

### `POST /api/v1/sessions`
Open a session.  Body: `{"title": "Investigation FR-002"}`.

### `GET /api/v1/sessions`
List active sessions.

### `GET /api/v1/sessions/{id}`
Session detail + last 10 reports.

### `DELETE /api/v1/sessions/{id}`
Close a session.

## Stubs (pre-existing, not yet wired to live data)

- `GET /api/v1/alerts` — stub
- `GET /api/v1/reports` — stub
- `POST /api/v1/benchmark` — stub (real benchmarks live in `scripts/` and `python -m 2_baseline_systems`)
- `POST /api/v1/search` — stub

## Error responses

```json
{"detail": "preset 'foo' not found"}
```

Standard FastAPI exception schema. HTTP codes: 200, 400, 404, 422, 500, 503
(orchestrator not initialized).

## Environment variables

| Var | Default | Effect |
|---|---|---|
| `SNI_PREWARM_ON_START` | `1` | Run entity prewarm at boot (~40s, recommended) |
| `SNI_PREWARM_TOP_N` | `30` | Entities to warm in the engine prewarm pass |
| `SNI_PRESET_PREWARM` | `0` | Run all 8 demo presets at boot (slow; cache warms on-demand instead) |
| `SNI_RESULT_CACHE_ENABLED` | `1` | LRU+TTL cache on `engine.query` |
| `SNI_RESULT_CACHE_SIZE` | `64` | Max cached entries |
| `SNI_RESULT_CACHE_TTL` | `300` | TTL in seconds |
