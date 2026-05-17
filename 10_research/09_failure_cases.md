# 09 — Failure Cases (operational honesty register)

This document is the **non-claims register**. Every "we don't do this"
is intentional, scoped, and documented here so a reviewer can verify
the claim surface is honest.

Operational honesty is part of the architecture.

## No fake multi-tenancy

**The platform has one live TigerGraph graph.**

Sample data and promoted uploads merge by vertex ID into the same
instance. There is no environment selector, no namespace isolation,
no per-tenant graph.

We chose this honestly because:
- The platform runs on a single TigerGraph Cloud deployment
- Adding an "environment selector" that does nothing would be theater
- True multi-tenancy requires schema-level vertex tagging that's out
  of scope for a research repo

**What the UI does instead:** the `environment_kind` field on
`/ingest/environment` reflects what's loaded right now (`empty` /
`sample` / `uploaded`). Recent Investigations records a snapshot of
graph state at investigation time so the analyst can see drift on
replay.

See [03_architecture_decisions.md](./03_architecture_decisions.md) D11.

## No fake rollback

Once an upload is promoted via `POST /ingest/promote/{id}`, its
vertices are merged into the live TG graph via `upsert_batch_vertices`.

We do not offer:
- A "reset to sample only" button
- An "undo this promotion" affordance
- Promotion-level rollback transactions

We could fake these (show a confirmation, do nothing), but that would
mislead an analyst into thinking the operation is reversible. TG
upserts are idempotent merges, not isolated transactions.

**What the UI does instead:** the promotion confirmation says
"promoted to live tigergraph" and the analyst can see the new
vertex counts immediately. The action is honestly described as
non-reversible.

## No fake connector simulation

The Sources page's connector panel includes:
- **TigerGraph** — real (actions: investigate, validate, reconnect)
- **CSV** — real (actions: upload, validate, promote)
- **JSON / PostgreSQL / Kafka / Snowflake** — labelled "planned ·
  adapter not enabled," collapsed by default, **no action buttons**

We never show a fake "Connect" button next to a connector that doesn't
have an adapter. The planned-connector list exists for honest scope
disclosure, not for theater.

See `8_dashboard_ui/src/components/sources/OperationalConnectorPanel.tsx`.

## No invented graph replay

When the analyst clicks "replay" on a Recent Investigation, we
**re-run the query** against the current TG graph. We do not:
- Restore graph state from a snapshot
- Replay archived events as if they were live
- Pretend the graph hasn't changed

**What the UI does instead:** the `env_total_vertices` chip shows the
graph size at the time the investigation was archived, with a `Δ +N`
or `Δ −N` badge in amber when the live graph has changed (>1%
delta). The analyst sees the drift honestly before clicking replay.

See [06_operational_investigations.md](./06_operational_investigations.md#replay-semantics).

### Replay against changed graphs

If you promoted a CSV upload between when an investigation was archived
and now, replaying that investigation will see *more* vertices. The
chip says so. We don't filter or freeze.

## Offline fallback (documented as a feature, not hidden)

When TigerGraph is unreachable, `GraphClient` switches to
`OfflineFallback` (backed by the local CSV dataset). Investigations
still run, the API still answers, the benchmark still produces JSON.

**This is intentional and prominently disclosed:**

- Health check returns `Mode: OFFLINE, healthy: true`
- The status pill in the UI shows `TG-OFF` not `LIVE`
- The Sources readiness strip flips every signal to amber/rose
- Archived investigations record `offline_mode: true` so a reviewer
  can filter them out

The fallback exists for two specific cases:
1. Local development without TG credentials
2. Demo continuity when TG happens to be down (the engine still runs
   the same code paths, just against shadow data)

We never let the UI claim "connected" when the underlying surface is
fallback. See [03_architecture_decisions.md](./03_architecture_decisions.md) D4.

## Mock LLM is the default, and disclosed

`LLMClient(provider="mock")` is the default for the benchmark runner.
It returns a deterministic string: `"[MOCK] Processed query with N
prompt tokens, generated M completion tokens."`

**Why this is honest:**
- Real LLM cost is variable and not the point of the benchmark
- The benchmark measures *retrieval* — token counts, retrieval ms,
  source counts, structural recovery
- A mock LLM keeps the benchmark deterministic across runs

**What is disclosed:**
- Every API response includes a `disclosure.latency_ms_is_mock_llm`
  field
- The `avg_latency_ms` field shows the mock 50ms placeholder
- The `avg_retrieval_ms` field shows the real measured retrieval cost
- The model name is reported as `"mock"` in every PipelineResult

If you configure a real provider (`SNI_BENCHMARK_LLM_PROVIDER=anthropic`,
etc.), the same code paths run with real LLM cost, and the disclosure
text updates accordingly.

## LLM judge is mock by default (and we say so)

When `LLMJudge` runs with a mock LLM, the judge's response is unparseable
JSON ("[MOCK] Processed...") and the judge gracefully falls back to a
neutral score of 3/5 on every dimension.

This shows up in the API as:
- `avg_judge_overall: 3.0` (every pipeline)
- `judge_pass_rate: 0.0` (nobody scored ≥4)
- `hallucination_resistance_rate: 0.0` (same)

A reviewer might mistake this for "GraphRAG has 0% hallucination
resistance." It isn't — it's "the mock judge can't produce useful
scores." The disclosure block in the response explicitly says so:

```json
"judge_is_llm": "avg_judge_* and judge_pass_rate come from LLMJudge — a
real LLM evaluation against the answer + context. Disabled when
with_scoring=False."
```

To get real judge scores, configure a separate judge LLM:

```bash
SNI_BENCHMARK_JUDGE_PROVIDER=anthropic
SNI_BENCHMARK_JUDGE_MODEL=claude-haiku-4-5
```

## Stale cache is possible and bounded

The result cache (LRU 64 × TTL 300s) is process-local. If the
underlying graph mutates within 300s of a query, a subsequent identical
query gets the stale result.

**Bounded:** TTL ensures eviction within 5 minutes. For the analyst
workstation use case (where a person is investigating one thing at a
time), this is acceptable.

**For benchmark runs:** the benchmark runner does NOT use the result
cache — it runs each query fresh. See
`2_baseline_systems/benchmarking/runner.py`.

## Benchmark service runs one job at a time

`BenchmarkService` uses a threading lock around runs. If a second
benchmark is requested while one is running, the second returns
HTTP 409 (`{"detail": "another benchmark run is in progress"}`).

This is honest by design — we don't queue silently and pretend things
are fast.

## What we do not measure

Per [05_benchmark_methodology.md](./05_benchmark_methodology.md#what-we-will-not-claim):

- We do not measure "accuracy" against a fabricated ground truth
- We do not measure judge scores with the same LLM that produced the answer
- We do not claim sub-second cold latency
- We do not claim GraphRAG is faster than VectorRAG (it isn't, cold)
- We do not claim "less hallucination" without a real judge

## What this register is for

If a reviewer can trace any claim on the platform back to either:
- a concrete measurement in an artifact file, OR
- an honest "we don't claim this" entry here,

then the operational surface is internally consistent. That's the goal.
