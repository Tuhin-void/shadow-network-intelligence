# 04 — VectorRAG Limitations

This document is the concrete contrast. For each query class, we show
*why* vector retrieval fails by construction — not by tuning, not by
embedding model, not by context size.

## The categorical claim

VectorRAG cannot expose:

1. **Typed edges.** Edges aren't in text.
2. **Multi-hop joins.** Each hop is a separate retrieval problem.
3. **Reverse traversal.** Document chunks don't encode edge direction.
4. **Membership topology.** "Member of ring FR-002" is a row, not a sentence.
5. **Inferred relationships.** `BENEFITS_FROM` doesn't exist as a sentence
   anywhere.

The adversarial benchmark (`scripts/adversarial_benchmark.py`) tests
each of these against 20 queries. **VectorRAG scores 0/20 on structural
recovery.** Not 0% accuracy — 0 structural edges in evidence. The
information necessary to produce one is not in the substrate.

## Query class A — Ring identification

> *"Identify all members of fraud ring FR-002."*

**What GraphRAG does:** one-hop reverse traversal from `FraudRing FR-002`
along `PERSON_MEMBER_OF_RING_reverse`, `COMPANY_MEMBER_OF_RING_reverse`,
etc. Returns the typed member list. Latency 2-4s warm.

**What VectorRAG does:** retrieves chunks containing "FR-002". Returns
documents that *mention* the ring, often missing members who appear in
the ring index but not in any narrative document. **No edges surfaced.**

Why it fails: ring membership is a row in an edge table, not a fact in
a document.

## Query class B — Hidden beneficial owner

> *"Who is the ultimate beneficial owner of C-00412?"*

**What GraphRAG does:** traverses `OWNS_reverse → OWNS_reverse → ...`
until reaching a Person vertex with no further owners. Optionally
augments with `BENEFITS_FROM` for nominee-director patterns.

**What VectorRAG does:** retrieves chunks mentioning C-00412 and the
phrase "beneficial owner". Cannot identify the Person two hops back
unless that exact name appears in a chunk that also mentions C-00412 —
which it usually doesn't.

Why it fails: the answer is reachable only by traversing the ownership
chain. Each hop is a join the embedder doesn't perform.

## Query class C — Shared infrastructure

> *"Who shares devices/addresses with the suspects already in FR-001?"*

**What GraphRAG does:** for each member of FR-001, traverse
`USES_DEVICE → SHARES_DEVICE_WITH` and `LOCATED_AT → SHARES_ADDRESS_WITH`.
Returns persons co-using the same infrastructure. Surfaces silent
collaborators not in the ring index.

**What VectorRAG does:** Cannot return them. Two people sharing a device
will almost never co-occur in any text document — that's the point of
materializing the inferred edge in the first place.

Why it fails: `SHARES_DEVICE_WITH` is an inferred edge — a join we
compute at load time precisely because no document records it.

## Query class D — Multi-hop laundering chain

> *"Trace the money flow from A-00043 to A-09812."*

**What GraphRAG does:** runs `tg_shortest_path` over `TRANSFERRED_TO`
edges, returning the ordered chain of intermediate accounts.

**What VectorRAG does:** retrieves transactions involving A-00043 OR
A-09812. Cannot order them, cannot identify intermediates that share no
keyword with either endpoint.

Why it fails: a path is an ordered sequence of edges. Bag-of-chunks
retrieval has no ordering primitive.

## Query class E — Cross-ring participation

> *"Find Persons who are members of more than one fraud ring."*

**What GraphRAG does:** aggregates membership edges grouped by Person,
filters for count > 1.

**What VectorRAG does:** can return persons mentioned alongside multiple
ring IDs in a chunk — but a person whose ring memberships are spread
across separate documents will be missed.

Why it fails: aggregation across the corpus requires the corpus to be
indexed by entity, which vector retrieval doesn't do — it indexes by
chunk.

## What we measure

`scripts/adversarial_results.json` records per-query for each pipeline:

- `structural_edges`: count of typed edges in the evidence chain
- `neighbors`: vertices traversed
- `evidence`: items in the EvidenceChainBuilder output
- `ring_touch_sum`: ring-membership ties surfaced

For VectorRAG, the relevant column is `vectorrag_proxy.structural_signal`.
It is **0 on every query** in the suite. This is not a tuning failure —
it is a property of the retrieval substrate.

## What VectorRAG would need to do this

To recover the missing answers, VectorRAG would need to:

1. Pre-compute every join we'd ever ask about (combinatorial explosion).
2. Materialize the result of each join as a synthetic text chunk
   (which would be… a graph encoded as text).
3. Or retrieve from a *graph index*, which is what GraphRAG already is.

The platform's claim isn't "GraphRAG is better." It's:

> For relationship questions, GraphRAG and VectorRAG aren't
> alternatives — they answer different question classes.

For sentence-shaped answers, VectorRAG remains correct. For edge-shaped
answers, it cannot apply.

## How we kept the comparison fair

The benchmark contract (documented in
[`../docs/BENCHMARK_METHOD.md`](../docs/BENCHMARK_METHOD.md)):

- Same query set
- Same corpus (the data engine's CSV output indexed both ways)
- Same embedder + LLM provider knobs
- Same query budget
- No special filters on either side

If we tilted the comparison, we'd be reporting an embedding-model failure,
not a substrate failure. The substrate failure is the actual finding.
