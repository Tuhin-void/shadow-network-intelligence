# Adversarial Benchmark Results

Profile: `small` · Queries: 12

## Summary Table

| ID | Category | GraphRAG entities | GraphRAG neighbors | GraphRAG evidence | GraphRAG structural-edges | Ring touch | VectorRAG (proxy) | PureLLM |
|---|---|---|---|---|---|---|---|---|
| ADV-RING-001 | ring_identification | 5 | 160 | 5 | 3 | 4 | docs=96 struct=0 | struct=0 |
| ADV-HIDDEN-002 | hidden_beneficial_owner | 5 | 187 | 5 | 3 | 0 | docs=0 struct=0 | struct=0 |
| ADV-COLLUSION-003 | shared_infrastructure | 5 | 145 | 5 | 3 | 0 | docs=0 struct=0 | struct=0 |
| ADV-DEVICE-004 | shared_device | 5 | 244 | 5 | 3 | 0 | docs=0 struct=0 | struct=0 |
| ADV-LAYERING-005 | multi_hop_laundering | 5 | 265 | 5 | 3 | 0 | docs=0 struct=0 | struct=0 |
| ADV-FUNNEL-006 | funnel_pattern | 5 | 244 | 5 | 3 | 0 | docs=0 struct=0 | struct=0 |
| ADV-OWNERSHIP-007 | circular_ownership | 5 | 409 | 5 | 3 | 0 | docs=96 struct=0 | struct=0 |
| ADV-CROSSRING-008 | cross_ring | 5 | 86 | 5 | 3 | 0 | docs=0 struct=0 | struct=0 |
| ADV-TXRING-009 | transaction_in_ring | 5 | 160 | 5 | 3 | 4 | docs=188 struct=0 | struct=0 |
| ADV-CONTROL-010 | hidden_controller | 5 | 207 | 5 | 3 | 0 | docs=0 struct=0 | struct=0 |
| ADV-DEGREE-011 | centrality | 5 | 49 | 5 | 3 | 0 | docs=0 struct=0 | struct=0 |
| ADV-PATH-012 | indirect_path | 1 | 33 | 4 | 3 | 0 | docs=0 struct=0 | struct=0 |

## Per-Query Detail

### ADV-RING-001 — ring_identification

**Question:** Identify all entities participating in fraud ring FR-001, including indirect members reachable through ring membership.

**Capability needed:** multi-hop ring traversal via *_MEMBER_OF_RING edges

**VectorRAG failure mode:** cannot enumerate ring members; can only return chunks that textually mention FR-001

**GraphRAG result:**

- entities: 5, neighbors: 160, evidence: 5, structural-edges in evidence: 3
- ring touch sum: 4, avg propagated risk: 0.0
- edge types surfaced: SENT_TRANSACTION
- latency: 8129.4 ms
```
SUSPECTS:
  • FraudRing layering_chain ring FR-001 (FR-001) — risk 0.00
  • Account A-006696 (A-006696) — risk 0.00 [in 1 ring(s)]
  • Account A-004548 (A-004548) — risk 0.00 [in 1 ring(s)]
  • Account A-007570 (A-007570) — risk 0.00 [in 1 ring(s)]
RING CONNECTIONS:
  • FraudRing FR-001 — ACCOUNT_MEMBER_OF_RING
  • FraudRing FR-001 — TRANSACTION_MEMBER_OF_RING
  • Account A-006696 — ACCOUNT_MEMBER
```

### ADV-HIDDEN-002 — hidden_beneficial_owner

**Question:** Who are the hidden beneficial owners of companies in the laundering network? Surface persons that benefit from companies without explicit ownership.

**Capability needed:** BENEFITS_FROM traversal — semantic similarity cannot infer this

**VectorRAG failure mode:** no textual mention of 'beneficial owner' on most rows — semantic search misses entirely

**GraphRAG result:**

- entities: 5, neighbors: 187, evidence: 5, structural-edges in evidence: 3
- ring touch sum: 0, avg propagated risk: 0.0
- edge types surfaced: OWNS, PERSON_MEMBER_OF_RING
- latency: 16520.0 ms
```
SUSPECTS:
  • FraudRing circular_ownership ring FR-014 (FR-014) — risk 0.00
  • FraudRing circular_ownership ring FR-011 (FR-011) — risk 0.00
  • FraudRing circular_ownership ring FR-005 (FR-005) — risk 0.00
  • FraudRing Offshore Routing 0 (FR-OFFSHORE-00) — risk 0.00
RING CONNECTIONS:
  • FraudRing FR-014 — PERSON_MEMBER_OF_RING
  • FraudRing FR-014 — COMPANY_MEMBER_OF_RING
  • FraudRing FR-011 
```

### ADV-COLLUSION-003 — shared_infrastructure

**Question:** Find pairs of persons that share addresses with shell-company controllers. These co-located individuals are likely co-conspirators.

**Capability needed:** SHARES_ADDRESS_WITH + OWNS traversal — graph join semantically invisible

**VectorRAG failure mode:** address strings rarely repeat verbatim across persons; semantic embedding clusters addresses by city not by exact match

**GraphRAG result:**

- entities: 5, neighbors: 145, evidence: 5, structural-edges in evidence: 3
- ring touch sum: 0, avg propagated risk: 0.0
- edge types surfaced: OWNS
- latency: 24215.9 ms
```
SUSPECTS:
  • Person John Petrov (P-004984) — risk 0.00 [4 fraud-edges]
  • Person Mary Petrov (P-004786) — risk 0.00 [4 fraud-edges]
  • Person Patricia Ivanov (P-004982) — risk 0.00 [3 fraud-edges]
  • Person Viktor Jones (P-004777) — risk 0.00
OWNERSHIP / FLOW:
  • OWNS: Company C-000637
  • OWNS: Company C-000527
  • HAS_ACCOUNT: Account A-002875
  • HAS_ACCOUNT: Account A-006984
SHARED INFRAS
```

### ADV-DEVICE-004 — shared_device

**Question:** Identify persons sharing devices — a strong coordination signal. Which person clusters reuse the same device infrastructure?

**Capability needed:** SHARES_DEVICE_WITH expansion

**VectorRAG failure mode:** device IDs are opaque (D-000003); embeddings cannot infer shared use

**GraphRAG result:**

- entities: 5, neighbors: 244, evidence: 5, structural-edges in evidence: 3
- ring touch sum: 0, avg propagated risk: 0.0
- edge types surfaced: OWNS
- latency: 16383.0 ms
```
SUSPECTS:
  • Person Mary Petrov (P-004786) — risk 0.00 [4 fraud-edges]
  • Person John Novak (P-004581) — risk 0.00 [4 fraud-edges]
  • Person Patricia Ivanov (P-004982) — risk 0.00 [3 fraud-edges]
  • Person Mary Jones (P-004569) — risk 0.00
OWNERSHIP / FLOW:
  • OWNS: Company C-003280
  • OWNS: Company C-004240
  • OWNS: Company C-004350
  • OWNS: Company C-003170
SHARED INFRASTRUCTURE:
  • LOC
```

### ADV-LAYERING-005 — multi_hop_laundering

**Question:** Trace a layering chain of 5+ accounts moving funds sequentially through a fraud ring. Output the chain in order.

**Capability needed:** TRANSFERRED_TO multi-hop traversal preserving order

**VectorRAG failure mode:** individual transaction documents have no notion of chain order; chunking fragments the sequence

**GraphRAG result:**

- entities: 5, neighbors: 265, evidence: 5, structural-edges in evidence: 3
- ring touch sum: 0, avg propagated risk: 0.0
- edge types surfaced: OWNS, PERSON_MEMBER_OF_RING
- latency: 19676.6 ms
```
SUSPECTS:
  • Company Titan Investments (C-004921) — risk 0.00
  • Company Strategic Holdings (C-004866) — risk 0.00
  • FraudRing circular_ownership ring FR-014 (FR-014) — risk 0.00
  • FraudRing funnel_account ring FR-006 (FR-006) — risk 0.00
RING CONNECTIONS:
  • FraudRing FR-014 — PERSON_MEMBER_OF_RING
  • FraudRing FR-014 — COMPANY_MEMBER_OF_RING
  • FraudRing FR-006 — ACCOUNT_MEMBER_OF_RING

```

### ADV-FUNNEL-006 — funnel_pattern

**Question:** Find a funnel-account pattern where 5+ source accounts feed a single destination account. List the destination and its sources.

**Capability needed:** fan-in degree analysis — purely structural

**VectorRAG failure mode:** no semantic feature corresponds to 'fan-in degree'; cannot rank accounts by structural centrality

**GraphRAG result:**

- entities: 5, neighbors: 244, evidence: 5, structural-edges in evidence: 3
- ring touch sum: 0, avg propagated risk: 0.0
- edge types surfaced: OWNS
- latency: 1716.7 ms
```
SUSPECTS:
  • Person Mary Petrov (P-004786) — risk 0.00 [4 fraud-edges]
  • Person John Novak (P-004581) — risk 0.00 [4 fraud-edges]
  • Person Patricia Ivanov (P-004982) — risk 0.00 [3 fraud-edges]
  • Person Mary Jones (P-004569) — risk 0.00
OWNERSHIP / FLOW:
  • OWNS: Company C-003280
  • OWNS: Company C-004240
  • OWNS: Company C-004350
  • OWNS: Company C-003170
SHARED INFRASTRUCTURE:
  • LOC
```

### ADV-OWNERSHIP-007 — circular_ownership

**Question:** Identify a circular ownership ring — a cycle of companies where each owns the next. List the cycle in order.

**Capability needed:** cycle detection via OWNS edges

**VectorRAG failure mode:** circles are topological structures; semantic search has no concept of cycle

**GraphRAG result:**

- entities: 5, neighbors: 409, evidence: 5, structural-edges in evidence: 3
- ring touch sum: 0, avg propagated risk: 0.0
- edge types surfaced: OWNS, PERSON_MEMBER_OF_RING
- latency: 16273.3 ms
```
SUSPECTS:
  • FraudRing circular_ownership ring FR-014 (FR-014) — risk 0.00
  • FraudRing circular_ownership ring FR-011 (FR-011) — risk 0.00
  • FraudRing circular_ownership ring FR-005 (FR-005) — risk 0.00
  • FraudRing funnel_account ring FR-006 (FR-006) — risk 0.00
RING CONNECTIONS:
  • FraudRing FR-014 — PERSON_MEMBER_OF_RING
  • FraudRing FR-014 — COMPANY_MEMBER_OF_RING
  • FraudRing FR-011 
```

### ADV-CROSSRING-008 — cross_ring

**Question:** Are there persons participating in multiple fraud rings simultaneously? Identify the most-connected persons across rings.

**Capability needed:** structural cross-reference of ring memberships

**VectorRAG failure mode:** ring membership is implicit in the graph, not in any document text

**GraphRAG result:**

- entities: 5, neighbors: 86, evidence: 5, structural-edges in evidence: 3
- ring touch sum: 0, avg propagated risk: 0.0
- edge types surfaced: SENT_TRANSACTION
- latency: 6476.4 ms
```
SUSPECTS:
  • Company Titan Investments (C-004921) — risk 0.00
  • Company Strategic Holdings (C-004866) — risk 0.00
  • Company Shadow Investments (C-004271) — risk 0.00
  • FraudRing circular_ownership ring FR-014 (FR-014) — risk 0.00
RING CONNECTIONS:
  • FraudRing FR-014 — PERSON_MEMBER_OF_RING
  • FraudRing FR-014 — COMPANY_MEMBER_OF_RING
  • Person Michael Garcia — PERSON_MEMBER_OF_RING (via
```

### ADV-TXRING-009 — transaction_in_ring

**Question:** List the suspicious transactions that are explicitly tagged as part of ring FR-001. Show their source and destination accounts.

**Capability needed:** TRANSACTION_MEMBER_OF_RING + SENT/RECEIVED_TRANSACTION joins

**VectorRAG failure mode:** individual transaction documents don't carry their ring metadata in a way semantic search can rank by

**GraphRAG result:**

- entities: 5, neighbors: 160, evidence: 5, structural-edges in evidence: 3
- ring touch sum: 4, avg propagated risk: 0.0
- edge types surfaced: SENT_TRANSACTION
- latency: 7649.1 ms
```
SUSPECTS:
  • FraudRing layering_chain ring FR-001 (FR-001) — risk 0.00
  • Account A-006696 (A-006696) — risk 0.00 [in 1 ring(s)]
  • Account A-004548 (A-004548) — risk 0.00 [in 1 ring(s)]
  • Account A-007570 (A-007570) — risk 0.00 [in 1 ring(s)]
RING CONNECTIONS:
  • FraudRing FR-001 — ACCOUNT_MEMBER_OF_RING
  • FraudRing FR-001 — TRANSACTION_MEMBER_OF_RING
  • Account A-006696 — ACCOUNT_MEMBER
```

### ADV-CONTROL-010 — hidden_controller

**Question:** Find the hidden controller of a shell-company cluster — a person who owns or benefits from multiple companies that share addresses.

**Capability needed:** 3-hop join: Person → OWNS/BENEFITS_FROM → Company → LOCATED_AT → Address ← LOCATED_AT ← Company

**VectorRAG failure mode:** the controller is not textually named as such; only the graph join reveals them

**GraphRAG result:**

- entities: 5, neighbors: 207, evidence: 5, structural-edges in evidence: 3
- ring touch sum: 0, avg propagated risk: 0.0
- edge types surfaced: OWNS
- latency: 22731.0 ms
```
SUSPECTS:
  • Person Mary Petrov (P-004786) — risk 0.00 [4 fraud-edges]
  • Person John Novak (P-004581) — risk 0.00 [4 fraud-edges]
  • Person Patricia Ivanov (P-004982) — risk 0.00 [3 fraud-edges]
  • Person Mary Jones (P-004569) — risk 0.00
OWNERSHIP / FLOW:
  • OWNS: Company C-003280
  • OWNS: Company C-004240
  • OWNS: Company C-004350
  • OWNS: Company C-003170
SHARED INFRASTRUCTURE:
  • LOC
```

### ADV-DEGREE-011 — centrality

**Question:** Which accounts are the most structurally central in the fraud topology, measured by number of fraud-relevant edges?

**Capability needed:** graph degree analysis on fraud-relevant edge subset

**VectorRAG failure mode:** centrality is a graph-theoretic measure; no text proxy

**GraphRAG result:**

- entities: 5, neighbors: 49, evidence: 5, structural-edges in evidence: 3
- ring touch sum: 0, avg propagated risk: 0.0
- edge types surfaced: SENT_TRANSACTION
- latency: 9662.6 ms
```
SUSPECTS:
  • FraudRing Offshore Routing 0 (FR-OFFSHORE-00) — risk 0.00
  • Company Titan Investments (C-004921) — risk 0.00
  • Company Strategic Holdings (C-004866) — risk 0.00
  • Company Shadow Investments (C-004271) — risk 0.00
OWNERSHIP / FLOW:
  • HAS_ACCOUNT: Account A-007083
  • HAS_ACCOUNT: Account A-001602
  • TRANSFERRED_TO: Account A-001606
SHARED INFRASTRUCTURE:
  • LOCATED_AT: Addre
```

### ADV-PATH-012 — indirect_path

**Question:** Show the indirect connection path between Person P-000001 and any other Person who shares a device with them.

**Capability needed:** specific named-entity multi-hop traversal

**VectorRAG failure mode:** no document mentions both persons together; semantic search returns docs about each in isolation

**GraphRAG result:**

- entities: 1, neighbors: 33, evidence: 4, structural-edges in evidence: 3
- ring touch sum: 0, avg propagated risk: 0.0
- edge types surfaced: OWNS, SENT_TRANSACTION
- latency: 14401.3 ms
```
SUSPECTS:
  • Person Raj Al-Hassan (P-000001) — risk 0.00
OWNERSHIP / FLOW:
  • OWNS: Company C-003508
  • OWNS: Company C-003398
  • HAS_ACCOUNT: Account A-005895
  • HAS_ACCOUNT: Account A-007481
SHARED INFRASTRUCTURE:
  • LOCATED_AT: Address ADDR-003416
  • LOCATED_AT: Address ADDR-000785
  • ASSOCIATED_WITH: Person P-000531
  • USES_DEVICE: Device D-000041
SIGNALS:
  • Entity mix: Person=1
```
