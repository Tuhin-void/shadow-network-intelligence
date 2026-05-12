"""
Shadow Network Intelligence - Benchmark Runner

Runs Pure LLM and Vector RAG baselines against the benchmark questions and
writes a results JSON to outputs/benchmark_results/.

Usage:
    python -m 2_baseline_systems.benchmark_runner [--approaches pure_llm,vector_rag]
                                                   [--questions PATH]
                                                   [--skip-index]
                                                   [--limit N]
                                                   [--output PATH]

Note: dashes are not valid in module names, so to invoke as a script use:
    cd 2_baseline_systems && python benchmark_runner.py
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "2_baseline_systems"  # type: ignore[assignment]

from .benchmark_data_loader import BenchmarkDataLoader
from .config import RESULTS_DIR, ensure_dirs, summary as config_summary
from .data_loader import load_dataset
from .document_builder import build_documents
from .pure_llm import OllamaClient, PureLLMBaseline
from .vector_rag import ChromaStore, VectorRAGBaseline

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("benchmark_runner")


SUPPORTED_APPROACHES = ("pure_llm", "vector_rag")


def _build_index_if_needed(store: ChromaStore, force: bool = False) -> int:
    if not force and store.count() > 0:
        logger.info("Reusing existing Chroma collection with %d documents", store.count())
        return store.count()

    logger.info("Loading sample dataset and building documents...")
    ds = load_dataset()
    docs = build_documents(ds)
    logger.info("Indexing %d documents into ChromaDB...", len(docs))
    n = store.index_documents(docs)
    logger.info("Indexed %d documents.", n)
    return n


def _summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    by_approach: dict[str, dict[str, Any]] = {}
    for r in results:
        agg = by_approach.setdefault(r["approach"], {
            "count": 0,
            "errors": 0,
            "total_latency_ms": 0.0,
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "ground_truth_scores": [],
        })
        agg["count"] += 1
        agg["total_latency_ms"] += r.get("latency_ms", 0.0)
        agg["total_prompt_tokens"] += r.get("prompt_tokens", 0)
        agg["total_completion_tokens"] += r.get("completion_tokens", 0)
        if r.get("error"):
            agg["errors"] += 1
        gt = r.get("ground_truth_eval", {})
        if gt.get("score") is not None:
            agg["ground_truth_scores"].append(gt["score"])

    for agg in by_approach.values():
        n = max(agg["count"], 1)
        agg["avg_latency_ms"] = round(agg["total_latency_ms"] / n, 2)
        scores = agg.pop("ground_truth_scores")
        agg["avg_ground_truth_score"] = round(sum(scores) / len(scores), 3) if scores else None

    return by_approach


def run(
    approaches: list[str],
    questions_path: Path | None = None,
    skip_index: bool = False,
    limit: int | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    ensure_dirs()

    loader = BenchmarkDataLoader()
    questions = (
        loader.load_custom_questions(questions_path) if questions_path else loader.get_questions()
    )
    if limit:
        questions = questions[:limit]
    logger.info("Loaded %d benchmark questions", len(questions))

    baselines: dict[str, Any] = {}
    llm = OllamaClient()

    if "pure_llm" in approaches:
        baselines["pure_llm"] = PureLLMBaseline(client=llm)

    if "vector_rag" in approaches:
        store = ChromaStore()
        if not skip_index:
            _build_index_if_needed(store)
        else:
            logger.info("Skipping index build (--skip-index). Existing count: %d", store.count())
        baselines["vector_rag"] = VectorRAGBaseline(store=store, llm=llm)

    if not llm.available():
        logger.warning(
            "Ollama is NOT reachable at %s. Each question will record an error. "
            "Start it with `ollama serve` and `ollama pull %s`.",
            llm.base_url, llm.model,
        )

    results: list[dict[str, Any]] = []
    for q in questions:
        qid = q["id"]
        qtext = q["question"]
        logger.info("Running Q=%s :: %s", qid, qtext[:80])
        for baseline in baselines.values():
            response = baseline.answer(qtext)
            response["question_id"] = qid
            response["question_meta"] = {
                k: v for k, v in q.items() if k not in {"id", "question"}
            }
            if response.get("answer"):
                response["ground_truth_eval"] = loader.evaluate_against_ground_truth(response["answer"])
            else:
                response["ground_truth_eval"] = {"score": None}
            results.append(response)

    summary_block = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config": config_summary(),
        "approaches": approaches,
        "question_count": len(questions),
        "by_approach": _summarize(results),
        "results": results,
    }

    if output_path is None:
        output_path = RESULTS_DIR / f"benchmark_{int(time.time())}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as f:
        json.dump(summary_block, f, indent=2, default=str)
    logger.info("Results written to %s", output_path)

    return summary_block


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run baseline benchmark.")
    p.add_argument(
        "--approaches",
        default="pure_llm,vector_rag",
        help="Comma-separated subset of: " + ",".join(SUPPORTED_APPROACHES),
    )
    p.add_argument("--questions", type=Path, default=None, help="Custom questions JSON path.")
    p.add_argument("--skip-index", action="store_true", help="Reuse existing Chroma collection.")
    p.add_argument("--limit", type=int, default=None, help="Run only the first N questions.")
    p.add_argument("--output", type=Path, default=None, help="Override output JSON path.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    requested = [a.strip() for a in args.approaches.split(",") if a.strip()]
    unknown = [a for a in requested if a not in SUPPORTED_APPROACHES]
    if unknown:
        logger.error("Unknown approaches: %s. Supported: %s", unknown, SUPPORTED_APPROACHES)
        return 2

    summary_block = run(
        approaches=requested,
        questions_path=args.questions,
        skip_index=args.skip_index,
        limit=args.limit,
        output_path=args.output,
    )

    print(json.dumps(summary_block["by_approach"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
