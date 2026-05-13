"""
Shadow Network Intelligence — Orchestrator API
FastAPI main entry point.

The InvestigationOrchestrator is constructed once at startup, performs
cache prewarm, and is reused across all requests via app.state.
"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from shared.logging_utils.logwriter import info, error as log_error
from shared.config import PATH_PREFIX

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Construct the InvestigationOrchestrator at startup; warm caches."""
    info("Shadow Network Intelligence API starting — initializing orchestrator...")
    try:
        # Local import keeps boot fast for `--help` / docs-only runs.
        from orchestration import InvestigationOrchestrator
        prewarm = os.environ.get("SNI_PREWARM_ON_START", "1") != "0"
        top_n = int(os.environ.get("SNI_PREWARM_TOP_N", "30"))
        app.state.orchestrator = InvestigationOrchestrator(
            prewarm_on_init=prewarm, prewarm_top_n=top_n,
        )
        info(f"Orchestrator ready: {app.state.orchestrator.status()}")
    except Exception as e:
        log_error(f"Orchestrator init failed: {e}")
        app.state.orchestrator = None
    yield
    info("Shadow Network Intelligence API shutting down...")


app = FastAPI(
    title="Shadow Network Intelligence",
    description="GraphRAG-powered fraud investigation platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers — investigate + demo are the canonical orchestrator surface;
# the rest are pre-existing stubs that are kept for backwards-compatibility.
from api import investigate, demo, alerts, reports, benchmark, search, health

app.include_router(investigate.router, prefix=PATH_PREFIX, tags=["Investigate"])
app.include_router(demo.router,        prefix=PATH_PREFIX, tags=["Demo"])
app.include_router(alerts.router,      prefix=PATH_PREFIX, tags=["Alerts"])
app.include_router(reports.router,     prefix=PATH_PREFIX, tags=["Reports"])
app.include_router(benchmark.router,   prefix=PATH_PREFIX, tags=["Benchmark"])
app.include_router(search.router,      prefix=PATH_PREFIX, tags=["Search"])
app.include_router(health.router,      prefix=PATH_PREFIX, tags=["Health"])

@app.get("/")
async def root():
    return {
        "name": "Shadow Network Intelligence",
        "version": "1.0.0",
        "status": "running"
    }

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )
