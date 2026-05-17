# 01 — Problem Space

## The fraud-investigation question

Financial-crime intelligence is a relationship problem disguised as a
search problem. A regulator does not ask *"give me documents about
this account"* — they ask *"who is laundering through this ring,
and how is the money moving."*

That kind of question has three properties that make traditional
retrieval the wrong tool:

1. **The answer is an edge, not a sentence.** "Person A controls
   Company B through Shell Company C" is not a fact stored in any
   document. It's a 3-hop join across `OWNS` and `BENEFITS_FROM`.
2. **The relevant entities don't appear together.** Two suspects in
   a laundering ring will rarely co-occur in any single document.
   Their connection is reachable only by traversal.
3. **Hidden relationships are typed, not textual.** `SHARES_DEVICE_WITH`,
   `SHARES_ADDRESS_WITH`, `BENEFITS_FROM` — these are inferred edges
   the platform materializes precisely because no document contains them.

## Why semantic similarity is structurally insufficient

VectorRAG retrieves chunks that *look like* the query, ranked by
cosine similarity in embedding space. That works when the answer
*is* a phrase. It fails when the answer is a path.

A representative example: *"who is the hidden controller of the
shell-company cluster around C-00412?"*

What VectorRAG returns:
- Chunks mentioning C-00412
- Chunks mentioning "controller" or "ultimate beneficial owner"
- Chunks with high keyword overlap

What it cannot return:
- The Person two hops away through `OWNS → OWNS → P-00782`
- The fact that P-00782 shares a residential address with P-00091
- The transaction chain that confirms control via `BENEFITS_FROM`

The graph join *is* the answer. No amount of context-window expansion
recovers it from chunked text. We measure this directly in
[04_vectorrag_limitations.md](./04_vectorrag_limitations.md).

## Why a synthetic AML dataset

Real bank data cannot be used for benchmarking — it is non-public,
non-shareable, and non-reproducible. So the platform ships its own
data engine (`1_data_engine/`) that generates dense, multi-ring
topologies with structurally-known fraud signal:

- 6 fraud-ring patterns (shell-network, layering, smurfing, structuring,
  funnel, circular)
- 6,000 Persons, 5,000 Companies, 10,000 Accounts, 150,000 Transactions
  in the `small` profile (175k+ vertices, 373k+ edges in live TG)
- Ground-truth fraud-ring membership recorded so we can score retrieval
  precisely

This is the same trade-off academic ML benchmarks make: synthetic
ground truth is the price of reproducibility.

## The platform's claim

Given that problem class, this platform argues:

1. The answer surface should be the **graph**, not text chunks.
2. Retrieval should be **typed-edge traversal** with topology-aware
   reranking, not embedding similarity.
3. Benchmark results should be **artifact-grounded** — reviewers
   read the same JSON the UI reads.
4. When TigerGraph is unreachable, the platform should degrade
   **honestly** — not fabricate results. See
   [09_failure_cases.md](./09_failure_cases.md).

The next document explains the mechanism — why typed-edge traversal
is the operative abstraction for this problem class.
