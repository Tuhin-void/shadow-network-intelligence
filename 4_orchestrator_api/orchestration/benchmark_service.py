"""
BenchmarkService — in-process bridge from the orchestrator API to the
real 3-pipeline BenchmarkRunner in 2_baseline_systems.

Goals:
  • Honest. Every metric routed through this service is computed by the
    same code path the CLI uses. No frontend-synthesized numbers.
  • Reusable. The underlying BenchmarkRunner is heavy to construct
    (embedder, vector store, GraphRAG retriever). We build it lazily,
    once per process, and reuse across requests.
  • Serializable. Only one benchmark can run at a time. Concurrent
    callers either get a 409 (sync API) or join the live stream of the
    in-flight run (SSE API surface — currently single-tenant; the lock
    blocks the start of a second SSE while the first runs).
  • Streamable. `run_stream(...)` yields events as they happen so the
    UI can render per-query progress in real time. Events come from the
    runner's optional on_event callback dispatched onto a Queue.
"""
from __future__ import annotations

import logging
import os
import queue
import sys
import threading
import time
from pathlib import Path
from typing import Iterator, Optional

logger = logging.getLogger(__name__)

# Make the repo root importable at runtime. We MUST NOT add
# `2_baseline_systems` directly to sys.path — that would expose its
# `shared/` subpackage as the top-level `shared`, shadowing the project's
# root-level `shared/` package and breaking re-exports like
# `from shared.constants.entity_types import ENTITY_TYPES` that
# `2_baseline_systems/shared/constants.py` relies on.
#
# The CLI works because `python -m 2_baseline_systems` keeps the repo
# root on sys.path and treats `2_baseline_systems` strictly as a package.
# We mirror that here.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_root_str = str(_REPO_ROOT)
if _root_str not in sys.path:
    sys.path.insert(0, _root_str)

# Imports must come AFTER sys.path injection.
from importlib import import_module  # noqa: E402

# These pulls resolve through the leading-digit package names.
_baseline = import_module("2_baseline_systems.benchmarking.runner")
_eval = import_module("2_baseline_systems.evaluation")
_query_loader_mod = import_module("2_baseline_systems.benchmarking.query_loader")
_schemas = import_module("2_baseline_systems.shared.schemas")
_data_loader_mod = import_module("2_baseline_systems.shared.data_loader")
_llm_client_mod = import_module("2_baseline_systems.shared.llm_client")
_embedder_mod = import_module("2_baseline_systems.shared.embedder")

BenchmarkRunner = _baseline.BenchmarkRunner
BenchmarkScorer = _eval.BenchmarkScorer
SemanticScorer = _eval.SemanticScorer
QueryLoader = _query_loader_mod.QueryLoader
BenchmarkQuery = _schemas.BenchmarkQuery  # noqa: F401
AdaptiveDataLoader = _data_loader_mod.AdaptiveDataLoader
LLMClient = _llm_client_mod.LLMClient
Embedder = _embedder_mod.Embedder


_VALID_APPROACHES = {"pure_llm", "vector_rag", "graph_rag"}
_MAX_LIMIT = 20  # hard cap for live runs; CLI is unaffected.


def _resolve_providers() -> dict:
    """Pick provider defaults from the live environment without imposing
    expensive dependencies. NIM is used for embeddings if NIM_API_KEY is
    set; otherwise mock. LLM defaults to mock so the live benchmark does
    not require Ollama / OpenAI / Anthropic. The graph provider is
    tigergraph (the same one the investigation orchestrator uses)."""
    has_nim = bool(os.environ.get("NIM_API_KEY"))
    return {
        "embedder_provider":  "nim" if has_nim else "mock",
        "embedder_model":     "nvidia/llama-nemotron-embed-1b-v2" if has_nim else "mock",
        "llm_provider":       os.environ.get("SNI_BENCHMARK_LLM_PROVIDER", "mock"),
        "llm_model":          os.environ.get("SNI_BENCHMARK_LLM_MODEL", "mock"),
        "judge_llm_provider": os.environ.get("SNI_BENCHMARK_JUDGE_PROVIDER", "mock"),
        "judge_llm_model":    os.environ.get("SNI_BENCHMARK_JUDGE_MODEL", "mock"),
        "vector_provider":    os.environ.get("SNI_BENCHMARK_VECTOR_PROVIDER", "mock"),
        "graph_provider":     os.environ.get("SNI_BENCHMARK_GRAPH_PROVIDER", "tigergraph"),
        "top_k":              int(os.environ.get("SNI_BENCHMARK_TOP_K", "8")),
        "chunk_size":         int(os.environ.get("SNI_BENCHMARK_CHUNK_SIZE", "500")),
    }


class BenchmarkService:
    """Singleton-style service. Build once at app startup, reuse forever."""

    def __init__(self, profile: str = "small") -> None:
        self.profile = profile
        self.config = _resolve_providers()
        self._runner: Optional[BenchmarkRunner] = None
        self._scorer: Optional[BenchmarkScorer] = None
        self._semantic_scorer: Optional[SemanticScorer] = None
        self._lock = threading.Lock()
        self._busy = False
        self._last_run_id: Optional[str] = None
        self._last_run_at: Optional[float] = None

    # ── Lazy construction ────────────────────────────────────────────────

    def _ensure_runner(self) -> BenchmarkRunner:
        if self._runner is None:
            logger.info("Constructing BenchmarkRunner (profile=%s, config=%s)",
                        self.profile, {k: v for k, v in self.config.items()
                                       if "key" not in k})
            data_loader = AdaptiveDataLoader(profile=self.profile)
            self._runner = BenchmarkRunner(
                profile=self.profile,
                data_loader=data_loader,
                config=self.config,
            )
        return self._runner

    def _ensure_scorer(self) -> BenchmarkScorer:
        if self._scorer is None:
            runner = self._ensure_runner()
            self._semantic_scorer = SemanticScorer(
                embedder=runner.embedder,
                prefer_bertscore=True,  # uses bert_score if available, else cosine
            )
            self._scorer = BenchmarkScorer(
                llm_client=runner.llm,
                judge_llm_client=runner.judge_llm,  # may be None — scorer warns
                semantic_scorer=self._semantic_scorer,
            )
            logger.info("BenchmarkScorer ready. Semantic method: %s",
                        self._semantic_scorer.method)
        return self._scorer

    # ── Public state ─────────────────────────────────────────────────────

    def status(self) -> dict:
        scorer_ready = self._scorer is not None
        return {
            "profile":             self.profile,
            "providers":           {k: v for k, v in self.config.items() if "key" not in k},
            "runner_initialized":  self._runner is not None,
            "scorer_initialized":  scorer_ready,
            "semantic_method":     self._semantic_scorer.method if scorer_ready else None,
            "busy":                self._busy,
            "last_run_id":         self._last_run_id,
            "last_run_at":         self._last_run_at,
            "max_limit_per_request": _MAX_LIMIT,
        }

    # ── Sync run ─────────────────────────────────────────────────────────

    def run(
        self,
        approaches: list[str],
        limit: int,
        tier: Optional[int] = None,
        with_scoring: bool = True,
    ) -> dict:
        """Foreground execution. Returns the BenchmarkRun.to_dict()."""
        approaches = _normalize_approaches(approaches)
        limit = _normalize_limit(limit)
        with self._guard():
            runner = self._ensure_runner()
            scorer = self._ensure_scorer() if with_scoring else None
            ql = QueryLoader(runner.data_loader)
            queries = ql.load_queries(tier=tier)
            run = runner.run(
                queries=queries,
                approaches=approaches,
                limit=limit,
                scorer=scorer,
                on_event=None,
                parallel=False,  # serialize for predictable in-API behavior
            )
            self._last_run_id = run.run_id
            self._last_run_at = time.time()
            return run.to_dict()

    # ── Ad-hoc query (single analyst question, all 3 pipelines) ─────────

    def run_ad_hoc(
        self,
        question: str,
        approaches: Optional[list[str]] = None,
        with_scoring: bool = False,
    ) -> dict:
        """Run a single analyst question through PureLLM / VectorRAG /
        GraphRAG and return per-pipeline PipelineResult dicts.

        Hard contracts:
          • No ground truth → entity_match has empty references; we
            disable entity scoring by default (still surfaced if
            `with_scoring=True`). The semantic scorer falls back to
            embedding-cosine without a reference (returns 0.5 neutral).
          • Same retrieval/answer code path as the batch benchmark.
            Numbers are directly comparable.
          • Serialized via the same lock as batch runs so we don't
            interleave with a running benchmark.
        """
        if not (question or "").strip():
            raise ValueError("question is required")
        approaches = _normalize_approaches(approaches)

        # Build a no-ground-truth BenchmarkQuery wrapper. The scorer
        # tolerates empty ground_truth_entities (precision=1.0, recall=1.0
        # when nothing is expected).
        synth = BenchmarkQuery(
            id=f"ADHOC-{int(time.time() * 1000)}",
            question=question.strip(),
            query_type="ad_hoc",
            required_hops=2,
            tier=0,
            ground_truth_entities=[],
            ground_truth_paths=[],
            complexity_score=0.0,
        )

        with self._guard():
            runner = self._ensure_runner()
            scorer = self._ensure_scorer() if with_scoring else None
            run = runner.run(
                queries=[synth],
                approaches=approaches,
                limit=1,
                scorer=scorer,
                on_event=None,
                parallel=False,
            )
            return run.to_dict()

    # ── Streaming run ────────────────────────────────────────────────────

    def run_stream(
        self,
        approaches: list[str],
        limit: int,
        tier: Optional[int] = None,
        with_scoring: bool = True,
    ) -> Iterator[dict]:
        """Generator yielding event dicts as the benchmark runs. Final event
        is always {"kind": "run.completed", ...} or {"kind": "run.error", ...}."""
        approaches = _normalize_approaches(approaches)
        limit = _normalize_limit(limit)

        if not self._lock.acquire(blocking=False):
            yield {
                "kind": "run.busy",
                "message": "Another benchmark run is in progress.",
                "last_run_id": self._last_run_id,
            }
            return

        try:
            self._busy = True
            ev_queue: "queue.Queue[dict]" = queue.Queue()
            SENTINEL = {"__sentinel__": True}

            def _on_event(ev: dict) -> None:
                ev_queue.put(ev)

            def _worker() -> None:
                try:
                    runner = self._ensure_runner()
                    scorer = self._ensure_scorer() if with_scoring else None
                    ql = QueryLoader(runner.data_loader)
                    queries = ql.load_queries(tier=tier)
                    runner.run(
                        queries=queries,
                        approaches=approaches,
                        limit=limit,
                        scorer=scorer,
                        on_event=_on_event,
                        parallel=False,
                    )
                except Exception as e:
                    logger.exception("benchmark worker failed")
                    ev_queue.put({"kind": "run.error", "error": str(e), "type": type(e).__name__})
                finally:
                    ev_queue.put(SENTINEL)

            t = threading.Thread(target=_worker, daemon=True, name="benchmark-runner")
            t.start()

            while True:
                try:
                    ev = ev_queue.get(timeout=300)  # 5min worker watchdog
                except queue.Empty:
                    yield {"kind": "run.error", "error": "worker_timeout"}
                    return
                if ev is SENTINEL:
                    return
                if ev.get("kind") == "run.completed":
                    self._last_run_id = ev.get("run_id")
                    self._last_run_at = time.time()
                yield ev
        finally:
            self._busy = False
            self._lock.release()

    # ── Helpers ──────────────────────────────────────────────────────────

    class _Guard:
        def __init__(self, parent: "BenchmarkService") -> None:
            self.parent = parent

        def __enter__(self) -> None:
            acquired = self.parent._lock.acquire(blocking=False)
            if not acquired:
                raise RuntimeError("benchmark_busy")
            self.parent._busy = True

        def __exit__(self, exc_type, exc, tb) -> None:
            self.parent._busy = False
            self.parent._lock.release()

    def _guard(self) -> "BenchmarkService._Guard":
        return BenchmarkService._Guard(self)


def _normalize_approaches(approaches: Optional[list[str]]) -> list[str]:
    if not approaches:
        return ["pure_llm", "vector_rag", "graph_rag"]
    out: list[str] = []
    for a in approaches:
        a = (a or "").strip()
        if a in _VALID_APPROACHES and a not in out:
            out.append(a)
    if not out:
        raise ValueError(f"approaches must be a subset of {_VALID_APPROACHES}")
    return out


def _normalize_limit(limit: int) -> int:
    try:
        n = int(limit)
    except Exception:
        n = 3
    if n <= 0:
        n = 3
    return min(n, _MAX_LIMIT)
