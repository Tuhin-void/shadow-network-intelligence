# 02 — Why GraphRAG

This document explains the *mechanism*, not just the slogan. Why is
typed-edge traversal the right primitive for relationship questions?

## The retrieval substrate matters

Every retrieval system makes a choice about what unit is retrievable:

| System | Unit | What it preserves |
|---|---|---|
| Lexical (BM25) | document | exact lexical match |
| VectorRAG | chunk | semantic locality |
| **GraphRAG** | **typed subgraph** | **structural reachability** |

The choice of unit determines what questions can be answered. A document
retrieval system cannot answer "how is X connected to Y across N hops"
because the unit it returns has no notion of N hops. A vector retrieval
system cannot expose typed edges because there are no typed edges in
text. A graph retrieval system can, because it operates on the same
substrate the question is asking about.

This is not an efficiency argument. It is a representation argument.

## What the engine actually does

`GraphRAGEngine.query()` (in
[`3_graph_intelligence_core/graph_rag/graphrag_engine.py`](../3_graph_intelligence_core/graph_rag/graphrag_engine.py))
is a small pipeline:

1. **Entity retrieval** (`EntityCentricRetriever`)
   Token + semantic match against entity name/description fields. Returns
   candidate entities ranked by a composite topology-aware score:

   ```
   final_score = 0.30 · base_score        (token / semantic match)
               + 0.20 · raw_risk          (precomputed risk field)
               + 0.20 · propagated_risk   (neighborhood-weighted)
               + 0.15 · ring_touch_count  (membership across rings)
               + 0.15 · fraud_degree      (fraud-relevant edge density)
   ```

2. **Neighborhood expansion**
   For each candidate, traverse typed edges up to `depth` hops.
   Edge types matter — we don't follow arbitrary edges; we expand along
   fraud-relevant types (`OWNS`, `TRANSFERRED_TO`, `MEMBER_OF_RING`,
   `SHARES_DEVICE_WITH`, etc.).

3. **Hidden-relationship promotion**
   `BENEFITS_FROM`, `SHARES_ADDRESS_WITH`, `SHARES_DEVICE_WITH`,
   `ASSOCIATED_WITH` are inferred edges materialized at load time. They
   represent the joins a human investigator would compute manually.

4. **Ring-member promotion**
   When any traversed entity is a ring member, sibling members get
   promoted into the candidate set with a `rerank_reason` explaining
   why ("member of ring FR-002").

5. **Context construction**
   The final payload is a structured subgraph (entities + context edges +
   evidence + paths). The LLM call that follows is a *projection* of the
   graph answer, not a retrieval.

## Why this is structurally different from VectorRAG

VectorRAG cannot:

- Follow a typed edge — there are no edges to follow
- Promote a sibling by ring membership — it has no notion of ring
- Compute `propagated_risk` — that requires a graph
- Materialize a `BENEFITS_FROM` inferred edge — that's a join
- Distinguish `Person OWNS Company` from `Company OWNS Person` —
  edges are directional; embeddings are not

The 20-query adversarial suite measures exactly this: GraphRAG produces
structural evidence on 20/20 queries, VectorRAG on 0/20 — not because
of tuning, but because of substrate.

## What we trade for it

GraphRAG is **slower** on cold paths: a real cold-cache investigation
takes 7–23 seconds against live TigerGraph. We accept that and offset
it with:

- A process-local **result cache** (LRU 64 entries × TTL 300s) wrapping
  `engine.query` — warm replays return in <50ms
- A **prewarm** step at boot (top 30 entities warmed by neighbor)
- An **adapter layer** so the benchmark runner uses the same engine,
  not a re-implementation

The platform's cost surface is honest: slow first-call, fast everywhere
else. We never claim sub-second cold latency.

## When GraphRAG is the wrong tool

There are problems VectorRAG handles better:

- Free-text Q&A over policy documents
- Email-thread summarization
- Code search by intent
- Any question whose answer is a phrase in a corpus

GraphRAG's value proposition only applies when the answer is a join.
We make this claim narrowly on purpose. See
[04_vectorrag_limitations.md](./04_vectorrag_limitations.md) for the
specific categories.
