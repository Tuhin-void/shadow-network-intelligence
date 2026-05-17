# Demo Flow

A 5-minute live demonstration of GraphRAG structural superiority. Built around
the curated preset suite that ships in
`4_orchestrator_api/orchestration/presets.py` and the adversarial benchmark
in `scripts/adversarial_queries.json`.

## Setup (before the demo)

Before the talk track starts:

```bash
# 1. Backend (port 8000) — leave running
PYTHONPATH=.:4_orchestrator_api \
SNI_RESULT_CACHE_ENABLED=1 \
SNI_PRESET_PREWARM=0 \
uvicorn main:app --app-dir 4_orchestrator_api --host 0.0.0.0 --port 8000

# 2. Frontend (port 5173) — leave running
cd 8_dashboard_ui && npm run dev

# 3. Warm the cache for the first preset you intend to demo (optional)
curl -X POST http://localhost:8000/api/v1/demo/run/ring-identification \
  -H "Content-Type: application/json" -d '{}'
```

Open **http://localhost:5173/**. The TopBar pill should read **LIVE**.

## Talk track (5 minutes)

### Minute 1 — The thesis (Home page)

> **"Traditional retrieval preserves documents. GraphRAG preserves relationships."**

Point at the Home page Stat strip:

- 8 cases · ~26,000 entities · 15+ rings · hidden ties · paths surfaced

Click the methodology pip at the top → opens the thesis page.

### Minute 2 — Live investigation (Manual workstation)

In the **Live orchestrator** launchpad section, click **ring-identification**.

The graph + 9-section IntelligencePanel populate from real TigerGraph
traversal. The SSE event ticker shows the structural moments unfolding:

```
session.started → query.received
entity.found × 5
ring.discovered → ring.member_promoted
neighborhood.expanded → evidence.collected
report.finalized
```

Highlight the **suspects** section: FR-002 plus 4 Person ring members
with `rerank_reason = "member of ring FR-002"`. **Every entity ID is grounded
in the live graph.**

### Minute 3 — The cognitive layer (right-side tab `3`)

Press `3` (or click **cognitive · reasoning** tab).

Show:
- 4 investigation agents with grounded confidence scores
- 18 key structural claims tagged by basis (ring / ownership / flow / infra)
- Per-suspect explanations referencing real edges
- **Overall structural confidence: ~0.79** — derived from edge density, not invented

Point at the Sanctions Tracer agent at 0.15 confidence — *"This isn't a bug.
The graph doesn't have sanctions data on these entities, so the agent
correctly scores low. The system never invents signal."*

### Minute 4 — The contrast (Benchmark page)

Navigate to `/benchmark`. Show the adversarial results table:

| Pipeline | Structural evidence | Avg tokens |
|---|---:|---:|
| GraphRAG | **3+ structural edges** on **20/20** queries | 50 |
| VectorRAG | **0** structural evidence (text chunks only) | 554 |
| PureLLM | **0** (no retrieval) | 22 |

> **"VectorRAG uses 11× more tokens than GraphRAG and still cannot answer the
> question. Why? Because the answer is an edge, not a sentence."**

### Minute 5 — Generate a report (CLI)

```bash
python3 -m 7_reporting_engine brief --preset ring-identification
```

Opens a markdown investigation brief with structured suspects, claims, agent
findings, contradictions, and per-suspect rationales. **Production-grade
artifact, generated in < 2 seconds.**

## Preset rotation (8 options)

| key | what it demonstrates |
|---|---|
| `ring-identification` | reverse-edge traversal + ring-member promotion |
| `hidden-beneficial-owner` | BENEFITS_FROM traversal + topology-aware reranking |
| `shared-address-collusion` | SHARES_ADDRESS_WITH + multi-hop join |
| `shared-device-cluster` | SHARES_DEVICE_WITH + hidden coordination |
| `layering-chain` | TRANSFERRED_TO multi-hop + TRANSACTION_MEMBER_OF_RING |
| `funnel-pattern` | fan-in degree analysis |
| `circular-ownership` | cycle detection via OWNS |
| `hidden-controller` | 3-hop Person → Company → Address ← Company join |

Every preset answers a question that VectorRAG cannot.

## If TigerGraph is down

The orchestrator gracefully drops into offline fallback. The platform still
renders, the cognitive layer still runs, but graph traversal returns minimal
results (CSV-only lookups). The TopBar pill shows **TG-OFF**.

## Stopping the demo

```bash
pkill -f "uvicorn main:app"   # backend
pkill -f "vite"               # frontend
```
