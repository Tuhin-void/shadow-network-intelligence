# Shadow Network Intelligence — Consolidated Benchmark Report

_Generated: 2026-05-16T20:47:58Z · profile: `small`_

## 1. TigerGraph operational state

**Status:** `HEALTHY`
- Vertex total: **175,204**
- Edge total:   **373,439**
- Reverse edges observed: **6**
- Rings with members: **4** / 5 sampled
- Installed queries: `tg_ring_members`, `tg_shortest_path`

## 2. Reliability (two-trial reproducibility)

**Verdict:** `STABLE`
- Queries: 5 × 2 trials
- Structural drift: **0** (target: 0)
- Latency outliers (>90.0%): **0**
- Empty answers: **0** (target: 0)

## 3. Adversarial benchmark (GraphRAG vs VectorRAG vs PureLLM)

Summary (full detail in `scripts/adversarial_results.md`):


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
| ADV-SANCTIONS-013 | sanctions_exposure | 5 | 145 | 5 | 3 | 0 | docs=0 struct=0 | struct=0 |
| ADV-INTERMEDIARY-014 | intermediary_discovery | 5 | 404 | 5 | 3 | 0 | docs=0 struct=0 | struct=0 |
| ADV-CROSSCASE-015 | cross_case_linkage | 5 | 298 | 5 | 3 | 0 | docs=96 struct=0 | struct=0 |
| ADV-RING-RECONSTRUCT-016 | fraud_ring_reconstruction | 5 | 62 | 5 | 3 | 4 | docs=96 struct=0 | struct=0 |
| ADV-NOMINEE-017 | nominee_director | 5 | 160 | 5 | 3 | 0 | docs=0 struct=0 | struct=0 |
| ADV-FANOUT-018 | fan_out_distribution | 5 | 307 | 5 | 3 | 0 | docs=0 struct=0 | struct=0 |
| ADV-PROXIMITY-019 | ring_proximity | 5 | 407 | 5 | 3 | 0 | docs=96 struct=0 | struct=0 |
| ADV-LATENT-020 | latent_relationship | 1 | 33 | 4 | 3 | 0 | docs=0 struct=0 | struct=0 |


## 4. Corpus enrichment manifest

- Documents emitted: **89**
- Estimated tokens:  **17,740**
- Output dir:         `outputs/small/documents/cross_refs`

| kind | count |
|---|---|
| `ring_dossier` | 15 |
| `address_brief` | 60 |
| `device_brief` | 14 |

## 5. Synthesis

TigerGraph=HEALTHY · Reliability=STABLE · Adversarial=PRESENT

The combined signal: GraphRAG superiority emerges from the dataset's topology, not from model choice — vector retrieval cannot reconstruct ring membership, hidden ownership, or multi-hop laundering chains from chunked text alone.