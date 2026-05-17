# 06 — Operational Investigations

This document covers how the platform turns analyst queries into
investigations: intent classification, ranked structural output,
the disk-backed archive, replay semantics, and the ad-hoc
3-pipeline comparison.

## The flow

```
analyst types question
  ↓
IntentChip (debounced live preview)
  ↓
POST /investigate/deep/stream     ← SSE
  ↓
orchestrator
  ├─ EVENT_SESSION_STARTED
  ├─ EVENT_QUERY_RECEIVED
  ├─ EVENT_INTENT_DETECTED         ← intent classifier
  ├─ engine.query (cache-aware)
  ├─ EVENT_ENTITY_FOUND × N
  ├─ EVENT_RING_DISCOVERED
  ├─ EVENT_HIDDEN_RELATION
  ├─ EVENT_RING_MEMBER_PROMO
  ├─ EVENT_NEIGHBORHOOD_DONE
  ├─ EVENT_TRAVERSAL_PATH × ≤3
  ├─ EVENT_EVIDENCE_COLLECTED
  ├─ EVENT_REPORT_FINALIZED        ← structured report
  │     stamps intent on payload
  │     records to disk archive
  ├─ agent.finished × 4            ← swarm
  ├─ reasoning.synthesized
  └─ deep_report.finalized         ← swarm + reasoning
        attaches to archive record
```

The SSE stream is consumed by the dashboard's `runCustomDeepStream`
action in the Zustand store, which projects events into the live graph
canvas, the timeline, and the cognitive panel.

## Intent classification

`IntentClassifier` ([`orchestration/intent.py`](../4_orchestrator_api/orchestration/intent.py))
maps natural-language queries to 8 first-class workflows:

| Workflow | Triggers |
|---|---|
| `rank_suspects` | "who is the most suspected", "highest risk", "rank ..." |
| `find_ring` | "show hidden rings", "fraud rings", "syndicate" |
| `trace_money` | "trace laundering", "follow the money", "transaction flow" |
| `ownership_chain` | "who owns", "beneficial owner", "who's behind" |
| `shared_infrastructure` | "shared device", "common address" |
| `hidden_relationships` | "hidden link", "uncover relationship" |
| `entity_dossier` | "tell me about P-...", "dossier for ..." |
| `neighborhood_expansion` | "connected to FR-...", "what's around ..." |

Output: a structured `IntentMatch` with `confidence`, matched entity
IDs, and (when intent is unknown) a list of suggested workflows + an
operational hint. **No LLM call, sub-millisecond, deterministic.**

When intent is unknown, the UI surfaces operational suggestions —
the platform refuses to be a chatbot. From
[`02_why_graphrag.md`](./02_why_graphrag.md): the platform's
vocabulary is small enough that rules outperform an LLM on latency
and predictability.

## Ranked structural output

A "rank_suspects" query like *"who is the most suspected"* doesn't
return prose. It returns a ranked list of suspects with topology evidence:

```json
{
  "v_id": "P-004777",
  "type": "Person",
  "risk_score": 70.0,
  "ring_touch_count": 0,
  "fraud_degree": 2,
  "rerank_reason": "2 fraud-relevant edges"
}
```

The ranking is the composite topology score from
[`02_why_graphrag.md`](./02_why_graphrag.md#what-the-engine-actually-does).
The `rerank_reason` is the *operational* explanation — why this entity
surfaced — not generated prose.

## The investigation archive

`InvestigationArchive` ([`orchestration/archive.py`](../4_orchestrator_api/orchestration/archive.py))
persists every investigation to disk under
`4_orchestrator_api/outputs/investigations/`. One JSON file per
investigation.

Each record contains:

- `investigation_id`, `session_id`, `query`, `created_at`
- `intent` (full IntentMatch)
- `top_k`, `depth`, `strategy`
- `elapsed_ms`, `cache_hit`, `offline_mode`
- `environment` snapshot at investigation time (`tigergraph_online`,
  `vertex_counts`, `total_vertices`, `environment_kind`, `captured_at`)
- `report` (full InvestigationReport payload, including intent)
- `deep_report` (attached after the cognitive layer finishes)

The archive is bounded at 200 entries (configurable via
`SNI_INVESTIGATION_ARCHIVE_MAX`). Older entries are pruned automatically.

### Why disk and not Redis

The platform runs on a single host (live demo, local research). Disk
JSON is simpler, debuggable, and inspectable with `cat | jq`. A Redis
backend would be a future-work choice; the interface is narrow enough
that swapping the store is one class.

## Recent Investigations panel

[`RecentInvestigationsPanel.tsx`](../8_dashboard_ui/src/components/investigation/RecentInvestigationsPanel.tsx)
reads `GET /investigations` and renders each archived investigation as
an operational row:

- Intent badge + display name + confidence
- Query text (the original analyst question)
- Surfaced suspect / ring / neighbor / evidence counts
- Cognitive layer chip (when `deep_report` is attached)
- Environment snapshot total + drift vs current live graph
- Elapsed time + relative timestamp
- Offline tag (when the investigation was run in offline mode)

**Click any row → replay** by re-running the original query through
GraphRAG. The result cache returns the same surface in <50ms.

The "env drift" chip is the honest replay caveat: if the graph has
changed since this investigation was archived, the replay will see
different data and the chip is amber with the delta. See
[09_failure_cases.md](./09_failure_cases.md#replay-against-changed-graphs).

## Replay semantics

We replay **the query**, not the engine state. There is no snapshot
restoration — the archived `report` and `deep_report` are read for the
UI to display historically, but clicking "replay" runs the question
fresh against current TigerGraph.

This is honest by design:

- A snapshot replay would require freezing graph state at investigation
  time. We don't have that infrastructure.
- A "show me what was returned then" view is available — open the
  archived record via `GET /investigations/{id}`.
- A "replay now" view is the right primitive for an active analyst who
  wants to see how the answer has changed.

## Ad-hoc 3-pipeline comparison

The Manual workstation includes a `compare · 3 pipelines` tab
([`AdHocComparisonPanel.tsx`](../8_dashboard_ui/src/components/investigation/AdHocComparisonPanel.tsx))
that runs the **current investigation's query** through PureLLM,
VectorRAG, and GraphRAG on demand.

This is causally tied to whatever the analyst is investigating, not to
the curated benchmark suite. Same code path as the batch benchmark, same
output JSON shape — numbers are directly comparable.

The panel surfaces:
- Per-pipeline aggregates (tokens, retrieval ms, sources, cost)
- A "measured insight" footer grounded entirely in the actual numbers
- Optional partial scoring (judge + semantic; no ground truth)

## Environment snapshot

Every archived investigation captures a snapshot of graph state at
investigation time. This is the single piece of context that lets
the Recent Investigations panel honestly tell the analyst *"this
investigation was archived when the graph had X vertices; the live
graph now has Y — a replay will see different data."*

The snapshot is cheap (the GraphClient caches vertex counts) and
non-fatal (failures return an empty snapshot rather than skipping the
archive write).
