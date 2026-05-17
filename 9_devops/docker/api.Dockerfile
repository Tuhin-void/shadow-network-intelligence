# Shadow Network Intelligence — Orchestrator API
#
# Builds the FastAPI orchestrator (4_orchestrator_api/main.py).
# The leading-digit package name means uvicorn must be invoked with
# `--app-dir 4_orchestrator_api` (see project Makefile).
FROM python:3.11-slim

WORKDIR /code

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Cache pip layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the full repository — the orchestrator imports cross-module
# packages (2_baseline_systems, 3_graph_intelligence_core, shared) at
# runtime via the same `sys.path` and `importlib` paths the CLI uses.
COPY . .

ENV PYTHONPATH=/code
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "main:app", "--app-dir", "4_orchestrator_api", \
     "--host", "0.0.0.0", "--port", "8000"]
