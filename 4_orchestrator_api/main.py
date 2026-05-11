"""
Shadow Network Intelligence - Orchestrator API
FastAPI main entry point
"""
import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from shared.logging_utils.logwriter import info, error as log_error, warning
from shared.config import PATH_PREFIX

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    info("Shadow Network Intelligence API starting...")
    yield
    info("Shadow Network Intelligence API shutting down...")

app = FastAPI(
    title="Shadow Network Intelligence",
    description="AI-powered fraud detection using GraphRAG",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
from api import investigate, alerts, reports, benchmark, search, health

app.include_router(investigate.router, prefix=PATH_PREFIX, tags=["Investigate"])
app.include_router(alerts.router, prefix=PATH_PREFIX, tags=["Alerts"])
app.include_router(reports.router, prefix=PATH_PREFIX, tags=["Reports"])
app.include_router(benchmark.router, prefix=PATH_PREFIX, tags=["Benchmark"])
app.include_router(search.router, prefix=PATH_PREFIX, tags=["Search"])
app.include_router(health.router, prefix=PATH_PREFIX, tags=["Health"])

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
