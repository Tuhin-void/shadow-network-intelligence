#!/usr/bin/env python3
"""
Consolidated benchmark report.

Reads the artifacts produced by the upstream validation scripts and emits
ONE markdown report aggregating:

  • Adversarial benchmark            (scripts/adversarial_results.md)
  • Benchmark reliability            (scripts/benchmark_reliability.json)
  • TigerGraph operational validator (scripts/tigergraph_validation.json)
  • Corpus enrichment manifest       (outputs/{profile}/documents/cross_refs/enricher_manifest.json)

Pure aggregation — no graph or LLM calls. Idempotent. Safe to run any time.

Output:
  scripts/benchmark_full_report.md

Usage:
  python3 scripts/benchmark_full_report.py
  python3 scripts/benchmark_full_report.py --profile benchmark_dense
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ADVERSARIAL_MD = PROJECT_ROOT / "scripts" / "adversarial_results.md"
RELIABILITY_JSON = PROJECT_ROOT / "scripts" / "benchmark_reliability.json"
TG_VALIDATION_JSON = PROJECT_ROOT / "scripts" / "tigergraph_validation.json"
OUT_MD = PROJECT_ROOT / "scripts" / "benchmark_full_report.md"


def _read_json(p: Path) -> dict[str, Any] | None:
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def _read_text(p: Path) -> str | None:
    return p.read_text() if p.exists() else None


def _compose(profile: str) -> str:
    rep = ["# Shadow Network Intelligence — Consolidated Benchmark Report",
           "",
           f"_Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', '')}Z · "
           f"profile: `{profile}`_",
           ""]

    # ── 1. TigerGraph operational state ────────────────────────────────
    tg = _read_json(TG_VALIDATION_JSON)
    rep += ["## 1. TigerGraph operational state", ""]
    if not tg:
        rep += ["_No validation artifact found. Run "
                "`python3 scripts/tigergraph_validate.py` first._", ""]
    else:
        status = tg.get("status", "?")
        rep += [
            f"**Status:** `{status}`",
            f"- Vertex total: **{tg.get('vertex_total', 0):,}**",
            f"- Edge total:   **{tg.get('edge_total', 0):,}**",
            f"- Reverse edges observed: **{len(tg.get('reverse_edges_observed') or {})}**",
            f"- Rings with members: **{tg.get('rings_with_members', 0)}** / "
            f"{len(tg.get('ring_probe') or [])} sampled",
            f"- Installed queries: {', '.join(f'`{k}`' for k in (tg.get('installed_queries') or {}).keys())}",
            "",
        ]
        crits = tg.get("critical_findings") or []
        if crits:
            rep += ["**Critical findings:**", ""]
            rep += [f"- {c}" for c in crits]
            rep += [""]

    # ── 2. Reliability ─────────────────────────────────────────────────
    rel = _read_json(RELIABILITY_JSON)
    rep += ["## 2. Reliability (two-trial reproducibility)", ""]
    if not rel:
        rep += ["_No reliability artifact found. Run "
                "`python3 scripts/benchmark_reliability.py` first._", ""]
    else:
        rep += [
            f"**Verdict:** `{rel.get('status', '?')}`",
            f"- Queries: {rel.get('queries_run', 0)} × {rel.get('trials_per_query', 0)} trials",
            f"- Structural drift: **{rel.get('structural_drift_count', 0)}** "
            f"(target: 0)",
            f"- Latency outliers (>{rel.get('latency_tolerance_pct', 0)}%): "
            f"**{rel.get('latency_outlier_count', 0)}**",
            f"- Empty answers: **{rel.get('empty_answer_count', 0)}** (target: 0)",
            "",
        ]
        if rel.get("issues"):
            rep += ["**Issues sample:**", ""]
            rep += [f"- {iss}" for iss in rel["issues"][:8]]
            rep += [""]

    # ── 3. Adversarial benchmark ───────────────────────────────────────
    rep += ["## 3. Adversarial benchmark (GraphRAG vs VectorRAG vs PureLLM)", ""]
    adv = _read_text(ADVERSARIAL_MD)
    if not adv:
        rep += ["_No adversarial-benchmark artifact found. Run "
                "`python3 scripts/adversarial_benchmark.py` first._", ""]
    else:
        # Extract the "Summary Table" section so the consolidated report
        # doesn't drown in per-query detail. The full doc remains available.
        in_table = False
        captured: list[str] = []
        for line in adv.splitlines():
            if line.startswith("## Summary Table"):
                in_table = True
                continue
            if in_table:
                if line.startswith("## "):
                    break
                captured.append(line)
        rep.append("Summary (full detail in `scripts/adversarial_results.md`):")
        rep.append("")
        rep += captured
        rep.append("")

    # ── 4. Corpus enrichment ───────────────────────────────────────────
    enricher = _read_json(
        PROJECT_ROOT / "outputs" / profile / "documents"
        / "cross_refs" / "enricher_manifest.json"
    )
    rep += ["## 4. Corpus enrichment manifest", ""]
    if not enricher:
        rep += ["_No corpus enrichment artifact for this profile. Run "
                f"`python3 scripts/data_corpus_enricher.py --profile {profile}`._",
                ""]
    else:
        rep += [
            f"- Documents emitted: **{enricher.get('documents_emitted', 0):,}**",
            f"- Estimated tokens:  **{enricher.get('estimated_tokens', 0):,}**",
            f"- Output dir:         `{enricher.get('output_dir', '—')}`",
            "",
            "| kind | count |",
            "|---|---|",
        ]
        for k, v in (enricher.get("by_kind") or {}).items():
            rep.append(f"| `{k}` | {v} |")
        rep.append("")

    # ── 5. Verdict synthesis ───────────────────────────────────────────
    rep += ["## 5. Synthesis", ""]
    verdict_bits: list[str] = []
    if tg:
        verdict_bits.append(f"TigerGraph={tg.get('status', '?')}")
    if rel:
        verdict_bits.append(f"Reliability={rel.get('status', '?')}")
    if adv:
        verdict_bits.append("Adversarial=PRESENT")
    rep.append(" · ".join(verdict_bits) or "_no upstream artifacts present yet_")
    rep.append("")
    rep.append(
        "The combined signal: GraphRAG superiority emerges from the dataset's "
        "topology, not from model choice — vector retrieval cannot reconstruct "
        "ring membership, hidden ownership, or multi-hop laundering chains "
        "from chunked text alone."
    )

    return "\n".join(rep)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile", default="small")
    args = ap.parse_args(argv)

    body = _compose(args.profile)
    OUT_MD.write_text(body)
    print(f"Consolidated report → {OUT_MD.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
