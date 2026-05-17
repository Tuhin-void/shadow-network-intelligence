# Quick Start

A 6-step path from clone to a live investigation. See [README.md](../README.md)
for the platform overview and thesis.

## Prerequisites

- Python 3.10+ (project tested on 3.14)
- Node.js 18+
- A TigerGraph Cloud workspace (or set `TIGERGRAPH_*` env vars to `OFFLINE` to
  use the file-based fallback)
- Optional: NVIDIA NIM API key for production-grade embeddings

## 1. Install dependencies

```bash
pip install -r requirements.txt
cd 8_dashboard_ui && npm install && cd ..
```

## 2. Configure secrets

The single source of truth for secrets is `.env` at the project root.
`config.yaml` placeholder fields stay empty.

```bash
# minimum required
TIGERGRAPH_HOST=https://<your-instance>.i.tgcloud.io
TIGERGRAPH_GSQL_SECRET=<from-portal>
TIGERGRAPH_GRAPH=ShadowGraph

# optional
NIM_API_KEY=<for-real-embeddings>
SNI_RESULT_CACHE_ENABLED=1
SNI_PREWARM_ON_START=1
SNI_PRESET_PREWARM=0   # leave 0 unless you want a slow boot
```

## 3. Generate the dataset (small profile, ~30s)

```bash
python -m 1_data_engine generate --profile small --new-pipeline
```

Outputs land in `outputs/small/csv/` (14 CSVs) and `outputs/small/json/`.

## 4. Load + validate TigerGraph

```bash
python -m 3_graph_intelligence_core load small
python -m 3_graph_intelligence_core health
```

Expected: `Mode: ONLINE` and vertex counts matching the small profile.

## 5. Boot the orchestrator API (port 8000)

```bash
PYTHONPATH=.:4_orchestrator_api \
SNI_RESULT_CACHE_ENABLED=1 \
SNI_PRESET_PREWARM=0 \
uvicorn main:app --app-dir 4_orchestrator_api --host 0.0.0.0 --port 8000
```

Verify:

```bash
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/orchestrator/status
```

## 6. Boot the dashboard (port 5173)

```bash
cd 8_dashboard_ui
npm run dev
```

Open **http://localhost:5173/**. The TopBar pill flips **LIVE** within 4s if
the orchestrator is reachable, **TG-OFF** if TigerGraph is in offline
fallback, **OFFLINE** if the API can't be reached.

## Verify the full benchmark

```bash
python3 scripts/tigergraph_validate.py
python3 scripts/benchmark_reliability.py --limit 5
python3 scripts/adversarial_benchmark.py --profile small
python3 scripts/benchmark_full_report.py --profile small
cat scripts/benchmark_full_report.md
```

## Quick CLI investigation

```bash
python3 -m 5_agent_swarm   --preset ring-identification
python3 -m 6_reasoning_engine --preset ring-identification
python3 -m 7_reporting_engine brief --preset ring-identification
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Pill shows `OFFLINE` | API not running on port 8000 | Re-run step 5; check `/health` |
| Pill shows `TG-OFF` | TigerGraph workspace paused or token rotated | Unpause workspace; restart orchestrator (it re-probes) |
| `python -m 1_data_engine` errors | wrong CWD | Run from project root |
| Boot is slow (>30s) | `SNI_PRESET_PREWARM=1` is running 8 demos at startup | Set `SNI_PRESET_PREWARM=0`; cache warms on-demand |
| `No module named '1_data_engine'` | running as script instead of module | Use `python -m 1_data_engine`, not `python 1_data_engine/main.py` |
