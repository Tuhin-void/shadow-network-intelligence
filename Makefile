.PHONY: help install install-all setup dev_setup run dev-backend dev-frontend dev-instructions run-demo clean test benchmark smoke-test type-check enrich-corpus enrich-corpus-test

help:
	@echo "Shadow Network Intelligence — Available Commands"
	@echo ""
	@echo "  ── Setup ────────────────────────────────────────────────"
	@echo "  make install          - Install Python deps"
	@echo "  make install-all      - Install Python + frontend deps"
	@echo "  make setup            - Initial setup (folders + scripts chmod)"
	@echo "  make dev_setup        - Full development environment setup"
	@echo ""
	@echo "  ── Run (two terminals recommended) ──────────────────────"
	@echo "  make dev-backend      - Start orchestrator API (port 8000)"
	@echo "  make demo-backend     - Backend with activation reset (clean demo landing)"
	@echo "  make dev-frontend     - Start dashboard dev server (port 5173)"
	@echo "  make dev-instructions - Print run instructions for both"
	@echo "  make run              - Same as dev-backend (alias)"
	@echo "  make run-demo         - Start demo environment"
	@echo ""
	@echo "  ── Data + corpus ────────────────────────────────────────"
	@echo "  make generate-data    - Generate small synthetic profile"
	@echo "  make enrich-corpus    - Build semantic intelligence corpus (~6M tokens)"
	@echo "  make enrich-corpus-test - Smoke test corpus build (--limit 50)"
	@echo "  make hydrate          - Load CSVs into TigerGraph"
	@echo ""
	@echo "  ── Quality ──────────────────────────────────────────────"
	@echo "  make benchmark        - Run benchmark comparison"
	@echo "  make smoke-test       - Quick API health + endpoint sanity check"
	@echo "  make test             - Run pytest suite"
	@echo "  make type-check       - tsc --noEmit on the dashboard"
	@echo ""
	@echo "  ── Cleanup ──────────────────────────────────────────────"
	@echo "  make clean            - Remove __pycache__, .pyc, generated_reports"
	@echo ""
	@echo "  ── Docker ───────────────────────────────────────────────"
	@echo "  make docker-up | docker-down | docker-logs"

install:
	pip install -r requirements.txt

install-all: install
	cd 8_dashboard_ui && npm install

# Optional: BERTScore for the semantic-similarity scorer. Without it,
# 2_baseline_systems/evaluation/semantic_scorer.py honestly reports
# "embedding_cosine" as the method instead. Heavy install (transformers + torch).
install-bertscore:
	pip install 'bert-score>=0.3.13'

setup:
	@echo "Setting up project structure..."
	@chmod +x 9_devops/scripts/*.sh 2>/dev/null || true
	@echo "Project structure created."

dev_setup:
	@echo "Setting up development environment..."
	@bash 9_devops/scripts/dev_setup.sh

# Canonical backend entrypoint. PYTHONPATH=. is required — without it
# imports like `from shared.logging_utils.logwriter import info` fail.
dev-backend:
	PYTHONPATH=. uvicorn main:app --app-dir 4_orchestrator_api --host 0.0.0.0 --port 8000 --reload

# Demo-mode backend — same as dev-backend but forces a fresh `empty`
# activation state on every boot. Use this when recording demo videos
# or sharing the dashboard with evaluators so the landing experience
# is the deliberate "click Launch Sample Ecosystem" CTA rather than
# whatever state was persisted from the previous session.
demo-backend:
	PYTHONPATH=. SNI_ENV_ACTIVATION_RESET=1 SNI_PREWARM_ON_START=0 \
		uvicorn main:app --app-dir 4_orchestrator_api --host 0.0.0.0 --port 8000 --reload

# Alias kept for backwards compatibility.
run: dev-backend

dev-frontend:
	cd 8_dashboard_ui && npm run dev

dev-instructions:
	@echo "Run these in TWO terminals:"
	@echo ""
	@echo "  Terminal 1:  make dev-backend     # API on http://localhost:8000"
	@echo "  Terminal 2:  make dev-frontend    # Dashboard on http://localhost:5173"
	@echo ""
	@echo "Then open http://localhost:5173 — the TopBar pill flips LIVE within seconds."

run-demo:
	@echo "Starting demo environment..."
	@bash 9_devops/scripts/run_demo.sh

benchmark:
	cd 2_baseline_systems && python benchmark_runner.py

# Re-run the GraphRAG structural-recovery evaluation against the live TG graph.
# Writes scripts/adversarial_results.{md,json}. Requires TG online.
benchmark-full:
	python3 scripts/adversarial_benchmark.py --profile small

# Re-run the 3-pipeline measured benchmark — the one whose numbers are
# cited in the README's "Real measured results" table. Real ChromaDB +
# TigerGraph + mock LLM (deterministic).
benchmark-measured:
	python -m 2_baseline_systems benchmark --profile small --limit 5 \
		--approaches pure_llm vector_rag graph_rag \
		--vector-provider chroma --graph-provider tigergraph \
		--embedder nim --llm mock

# Tests need PYTHONPATH=. so cross-module packages (3_graph_intelligence_core,
# 4_orchestrator_api.api.benchmark) resolve the same way they do at runtime.
# `python -m pytest` is more portable than `pytest` (works even when the
# script-installed entry point is missing from PATH).
test:
	PYTHONPATH=. python -m pytest tests/unit/ -v

test-unit:
	PYTHONPATH=. python -m pytest tests/unit/ -v

test-integration:
	PYTHONPATH=. python -m pytest tests/integration/ -v

# Quick post-startup sanity check — assumes backend is on :8000.
# Fails loud if any expected endpoint returns non-2xx.
smoke-test:
	@echo "  → /health"
	@curl -fsS http://localhost:8000/api/v1/health > /dev/null && echo "    ✓ healthy" || (echo "    ✗ backend not responding"; exit 1)
	@echo "  → /orchestrator/status"
	@curl -fsS http://localhost:8000/api/v1/orchestrator/status > /dev/null && echo "    ✓ ok" || (echo "    ✗ orchestrator status failed"; exit 1)
	@echo "  → /ingest/environment"
	@curl -fsS http://localhost:8000/api/v1/ingest/environment > /dev/null && echo "    ✓ ok" || (echo "    ✗ environment endpoint failed"; exit 1)
	@echo "  → /benchmark/service/status"
	@curl -fsS http://localhost:8000/api/v1/benchmark/service/status > /dev/null && echo "    ✓ ok" || (echo "    ✗ benchmark service failed"; exit 1)
	@echo "  → /orchestrator/intent (rank_suspects)"
	@curl -fsS -X POST http://localhost:8000/api/v1/orchestrator/intent \
		-H 'Content-Type: application/json' \
		-d '{"query":"who is the most suspected"}' | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['kind']=='rank_suspects', d; print('    ✓ intent=rank_suspects')"
	@echo "  → frontend (Vite dev server, optional)"
	@curl -fsS --max-time 2 http://localhost:5173/ > /dev/null 2>&1 && echo "    ✓ vite up" || echo "    ⚠ vite not running (start with: make dev-frontend)"

# Frontend type check — useful before committing UI changes.
type-check:
	cd 8_dashboard_ui && npx tsc --noEmit

# CAREFUL: does NOT wipe outputs/ (which contains the data engine output,
# enriched corpus, and investigation archive — too expensive to regenerate
# accidentally). Use `make reset` for a full wipe.
clean:
	@echo "Cleaning ephemeral artifacts..."
	@find . -type d -name "__pycache__" -not -path "./venv/*" -not -path "./node_modules/*" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -not -path "./venv/*" -not -path "./node_modules/*" -delete 2>/dev/null || true
	@rm -rf .pytest_cache 2>/dev/null || true
	@rm -rf 8_dashboard_ui/dist 2>/dev/null || true
	@rm -rf generated_reports/* 2>/dev/null || true
	@echo "Clean complete. (outputs/, cache/, and corpus are preserved — use 'make reset' for a full wipe.)"

# Docker commands
docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

# Generate sample data. Canonical entrypoint is the `1_data_engine` package
# (see 1_data_engine/__main__.py). The legacy `generators/main_generator.py`
# script was removed when the new pipeline was promoted; this target uses
# the new pipeline exclusively.
generate-data:
	python -m 1_data_engine generate --profile small --new-pipeline

generate-data-full:
	python -m 1_data_engine generate --profile hackathon_default --new-pipeline

# Build the semantic intelligence corpus (deterministic, no LLM calls).
# Reads outputs/{profile}/csv/, writes outputs/{profile}/enriched_corpus/.
enrich-corpus:
	python3 scripts/semantic_intelligence_corpus.py --profile small

enrich-corpus-test:
	python3 scripts/semantic_intelligence_corpus.py --profile small --limit 50

# Load data into TigerGraph
hydrate:
	@bash 9_devops/scripts/hydrate.sh

# Reset everything
reset:
	@bash 9_devops/scripts/reset.sh
