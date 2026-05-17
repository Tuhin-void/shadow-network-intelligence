# 10 — Future Work

Items we deferred, with the reasoning for deferral. Each entry is
scoped tightly enough that a follow-on engineer could pick it up
without re-discovering the constraints.

## A — Intent-aware rerank weights

**What:** The intent classifier emits a `kind` (e.g. `rank_suspects`,
`trace_money`, `shared_infrastructure`). Today, that label is reported
in the UI and stored on the archive record — but the retriever's
rerank weights are uniform across all intents.

**The change:** `EntityCentricRetriever._topology_rerank()` would
accept an optional `weight_override: dict | None` parameter and the
orchestrator would derive it from the intent.

```python
INTENT_WEIGHT_OVERRIDES = {
    "rank_suspects":         {"propagated_risk": 0.30, "ring_touch": 0.30},
    "find_ring":             {"ring_touch": 0.45, "fraud_degree": 0.25},
    "trace_money":           {"fraud_degree": 0.35, "base_score": 0.25},
    "shared_infrastructure": {"fraud_degree": 0.40, "base_score": 0.30},
    # ...
}
```

**Why deferred:** the uniform weights already produce strong rankings
on the adversarial suite. Adding per-intent weights without a holdout
test set would be over-fitting. Need to design a small held-out set first.

## B — Real BERTScore in CI

**What:** The semantic scorer prefers true BERTScore F1 if `bert_score`
is installed, else falls back to embedding-cosine. Today neither CI
nor the default install includes `bert_score` (~500MB of HuggingFace
deps).

**The change:** add `bert_score` to a `requirements-eval.txt` extras
file. CI runs benchmarks with the extras installed. Production runs
without (cheaper).

**Why deferred:** doubles the container size. The embedding-cosine
fallback gives directionally-correct signal at near-zero marginal cost.

## C — Snapshot replay (not "re-run replay")

**What:** Today "replay" re-runs the query against the current TG
graph. A true snapshot replay would freeze graph state at investigation
time and replay the engine against that snapshot.

**The change:** the archive record would include `vertex_ids_touched`
+ `edge_ids_touched`. Replay would project a `SnapshotGraphClient` over
those IDs (with cached attribute values) and re-run the engine.

**Why deferred:** requires a non-trivial cached-attribute layer over
TG. The current drift indicator (env-snapshot chip) gives enough
honesty for the analyst use case.

## D — Redis-backed session + archive

**What:** Session memory is per-process; investigation archive is local
disk JSON. Multi-instance deployment requires a shared store.

**The change:** the `SessionStore` and `InvestigationArchive` classes
have small, narrow interfaces. A Redis backend would be one class each,
gated by an env var.

**Why deferred:** the platform is a research repo, not a multi-instance
production deployment. Disk JSON is simpler for inspection.

## E — Multi-environment isolation (vertex tagging)

**What:** Today all uploads land in the same TG graph. True
multi-tenancy would require tagging each vertex with an
`environment_id` and constraining traversals to that tag.

**The change:** schema-level addition. Every vertex gets an
`environment_id` attribute (default: "primary"). All retrievers
filter on it. Promotion accepts an `environment_id` parameter.

**Why deferred:** out of scope for this research repo. Documented
as a non-claim in [09_failure_cases.md](./09_failure_cases.md#no-fake-multi-tenancy)
so we never silently introduce theater.

## F — Pipeline-aware ad-hoc benchmark scoring

**What:** The `/benchmark/ad-hoc` endpoint runs the analyst's current
question through 3 pipelines. With `with_scoring=true` it produces
partial scoring (judge + semantic only — no entity F1 because no
ground truth).

**The change:** when an analyst confirms an answer ("this is correct"),
the platform could capture that as ad-hoc ground truth and start
scoring entity F1 on future runs of similar questions.

**Why deferred:** requires a user-feedback UI element. Out of scope
for the current submission pass.

## G — Real GraphRAG vs. text-embedding-on-graph baseline

**What:** Our VectorRAG baseline is ChromaDB over chunked text. A
stronger comparison would be ChromaDB over **graph-walk-encoded**
text (random walks → tokenized paths → embedded chunks). That's
how some commercial knowledge-graph + LLM products work.

**The change:** add `2_baseline_systems/pipelines/graph_walk_rag.py`
that pre-computes random walks over the schema, encodes each walk as
a sentence, and indexes them. Compare directly.

**Why deferred:** the current comparison already proves the substrate
claim. A graph-walk baseline would be more *fair* but produce the same
verdict — paths aren't sentences.

## H — Native GSQL pre-warm queries

**What:** GraphRAGEngine prewarm walks 138 entities at boot, paying
per-entity round-trips. A native GSQL query could pre-compute
neighborhoods server-side and return them in one trip.

**The change:** add an installed GSQL `tg_warmup` procedure.
GraphRAGEngine calls it once at boot.

**Why deferred:** boot is already <40s with the current approach
(once per backend process). Optimization for a non-hot path.

## I — Time-windowed investigation filters

**What:** A laundering analyst cares about recent transactions, not
all-time. Today the engine treats all edges as equally current.

**The change:** add a `time_range` parameter to investigation requests.
The traversal filters edges by `created_at`.

**Why deferred:** requires time attributes on every edge type. The
data engine produces them but the schema doesn't surface them yet.

## J — Federated query across multiple TG graphs

**What:** A bank with multiple TG instances per region would want a
federated investigation that fans out to each and aggregates.

**The change:** a `GraphClientPool` layer. Each instance is a single
`GraphClient`; the pool routes traversals.

**Why deferred:** entirely out of scope for a research repo. Listed
here for completeness — interested production deployers should know
the architecture supports it.

## What we will not build (decisions, not just deferrals)

- **LLM-based intent routing.** Rules are faster and more predictable
  for this vocabulary.
- **Vector-only investigation mode.** The platform's claim is that
  GraphRAG and VectorRAG are different tools for different question
  classes. We won't ship a mode that pretends otherwise.
- **Free-text "explain this answer" chat.** The platform refuses to
  drift into chatbot UX. Explanations come from the reasoning engine
  as structured claims, not from a dialog.
- **Fake real-time dashboards** (auto-refreshing fraud alerts from
  nowhere). Alerts must come from a real signal source; we don't
  invent them.
