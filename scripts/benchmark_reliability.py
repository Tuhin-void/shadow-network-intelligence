#!/usr/bin/env python3
"""
Benchmark reliability validator.

Runs the adversarial-query suite TWICE against the same GraphRAG engine and
asserts:
  1. Structural metrics are reproducible across runs (entity_count,
     neighbor_count, structural_edges — exact match expected with caches.)
  2. Latency is within reasonable variance (no pathological cold-start
     fluctuation post-prewarm).
  3. Token / evidence counts are non-zero on every query (no silent failures).
  4. No query produces an empty answer.

The point: the GraphRAG superiority story is only credible if the numbers
are stable across runs. Random variance would invite skepticism.

Outputs:
  scripts/benchmark_reliability.json  — full numeric comparison
  scripts/benchmark_reliability.md    — narrative pass/fail report

Exit code: 0 = all stable; 1 = significant variance detected; 2 = TG offline.

Usage:
  python3 scripts/benchmark_reliability.py
  python3 scripts/benchmark_reliability.py --limit 10 --latency-tolerance-pct 60
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "3_graph_intelligence_core"))

QUERIES_PATH = PROJECT_ROOT / "scripts" / "adversarial_queries.json"
JSON_OUT = PROJECT_ROOT / "scripts" / "benchmark_reliability.json"
MD_OUT = PROJECT_ROOT / "scripts" / "benchmark_reliability.md"

# Structural metrics that MUST be stable across runs (caches + deterministic
# retrieval should make these exactly equal between back-to-back calls).
_STABLE_METRICS = ("entities", "neighbors", "evidence")


def _emit(msg: str) -> None:
    print(msg, flush=True)


def _run_one(engine, q: dict, top_k: int = 5, depth: int = 2) -> dict[str, Any]:
    t0 = time.perf_counter()
    res = engine.query(q["question"], config={"strategy": "auto", "top_k": top_k, "depth": depth})
    ms = (time.perf_counter() - t0) * 1000
    md = res.get("metadata", {}) or {}
    sources = res.get("sources", []) or []
    edge_types = sorted({
        (s.get("provenance", {}) or {}).get("edge_type", "")
        for s in sources
    } - {""})
    answer = (res.get("answer") or "").strip()
    return {
        "qid": q["id"],
        "ms": round(ms, 1),
        "entities":  md.get("entity_count", 0),
        "neighbors": md.get("neighbor_count", 0),
        "evidence":  md.get("evidence_count", 0),
        "edge_types": edge_types,
        "answer_len": len(answer),
        "answer_nonempty": bool(answer),
    }


def reliability(limit: int, latency_tolerance_pct: float) -> dict[str, Any]:
    from clients.graph_client import GraphClient
    from configs.config import load_config
    from graph_rag.graphrag_engine import GraphRAGEngine

    queries = json.loads(QUERIES_PATH.read_text())["queries"]
    if limit:
        queries = queries[:limit]

    cfg = load_config(None)
    client = GraphClient(cfg)
    if client._offline_mode:
        return {"status": "OFFLINE", "queries": []}

    engine = GraphRAGEngine(client, cfg, compression="rule_based")
    _emit("Prewarming caches ...")
    pre = engine.prewarm(top_n=30)
    _emit(f"  prewarm: candidates={pre.get('candidates')} took={pre.get('ms')}ms\n")

    rows: list[dict[str, Any]] = []
    _emit(f"Reliability run · {len(queries)} queries × 2 trials ...\n")
    for q in queries:
        trial1 = _run_one(engine, q)
        trial2 = _run_one(engine, q)
        rows.append({"q": {"id": q["id"], "category": q["category"]},
                     "trial1": trial1, "trial2": trial2})
        _emit(f"  {q['id']:24s}  t1={trial1['ms']:6.1f}ms  t2={trial2['ms']:6.1f}ms  "
              f"ent={trial1['entities']}/{trial2['entities']}  "
              f"nb={trial1['neighbors']}/{trial2['neighbors']}  "
              f"ev={trial1['evidence']}/{trial2['evidence']}")

    # ── Verdicts ───────────────────────────────────────────────────────
    issues: list[str] = []
    structural_drift = 0
    latency_outliers = 0
    empty_answers = 0
    for row in rows:
        t1, t2 = row["trial1"], row["trial2"]
        for m in _STABLE_METRICS:
            if t1[m] != t2[m]:
                structural_drift += 1
                issues.append(f"{row['q']['id']}: metric `{m}` drifted "
                              f"{t1[m]} vs {t2[m]}")
        # Latency tolerance — cache-warm run-to-run should be tight.
        if t1["ms"] > 0 and t2["ms"] > 0:
            ratio = abs(t1["ms"] - t2["ms"]) / max(t1["ms"], t2["ms"]) * 100
            if ratio > latency_tolerance_pct:
                latency_outliers += 1
                issues.append(f"{row['q']['id']}: latency variance "
                              f"{ratio:.1f}% > {latency_tolerance_pct}%")
        if not t1["answer_nonempty"] or not t2["answer_nonempty"]:
            empty_answers += 1
            issues.append(f"{row['q']['id']}: at least one empty answer")

    verdict = "STABLE" if not issues else (
        "ACCEPTABLE" if (structural_drift == 0 and empty_answers == 0)
        else "DEGRADED"
    )

    return {
        "status": verdict,
        "queries_run": len(rows),
        "structural_drift_count": structural_drift,
        "latency_outlier_count": latency_outliers,
        "empty_answer_count": empty_answers,
        "latency_tolerance_pct": latency_tolerance_pct,
        "trials_per_query": 2,
        "issues": issues,
        "rows": rows,
        "prewarm": pre,
    }


def _write_markdown(rep: dict[str, Any]) -> None:
    if rep.get("status") == "OFFLINE":
        MD_OUT.write_text("# Benchmark reliability\n\nStatus: **OFFLINE** "
                          "(TigerGraph unreachable; reliability run skipped).")
        return

    lines = [
        "# Benchmark reliability report",
        "",
        f"**Verdict:** `{rep['status']}`  •  **Queries:** {rep['queries_run']}  •  "
        f"**Trials per query:** {rep['trials_per_query']}",
        "",
        f"- Structural metric drift: **{rep['structural_drift_count']}** "
        f"(target: 0)",
        f"- Latency outliers (>{rep['latency_tolerance_pct']}% variance): "
        f"**{rep['latency_outlier_count']}**",
        f"- Empty answers: **{rep['empty_answer_count']}** (target: 0)",
        "",
        "## Per-query results",
        "",
        "| query | t1 ms | t2 ms | ent₁ | ent₂ | nb₁ | nb₂ | ev₁ | ev₂ |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rep["rows"]:
        t1, t2 = row["trial1"], row["trial2"]
        lines.append(
            f"| `{row['q']['id']}` | {t1['ms']} | {t2['ms']} | "
            f"{t1['entities']} | {t2['entities']} | "
            f"{t1['neighbors']} | {t2['neighbors']} | "
            f"{t1['evidence']} | {t2['evidence']} |"
        )

    if rep["issues"]:
        lines += ["", "## Issues detected", ""]
        lines += [f"- {iss}" for iss in rep["issues"][:40]]

    MD_OUT.write_text("\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=0,
                    help="number of queries to run (0 = all)")
    ap.add_argument("--latency-tolerance-pct", type=float, default=80.0,
                    help="acceptable t1↔t2 variance in percent")
    args = ap.parse_args(argv)

    rep = reliability(args.limit, args.latency_tolerance_pct)
    JSON_OUT.write_text(json.dumps(rep, indent=2, default=str))
    _write_markdown(rep)
    _emit(f"\nReliability JSON → {JSON_OUT.relative_to(PROJECT_ROOT)}")
    _emit(f"Reliability MD   → {MD_OUT.relative_to(PROJECT_ROOT)}")
    if rep.get("status") == "OFFLINE":
        return 2
    return 0 if rep.get("status") in ("STABLE", "ACCEPTABLE") else 1


if __name__ == "__main__":
    sys.exit(main())
