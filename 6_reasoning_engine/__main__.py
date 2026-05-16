"""
CLI for the reasoning engine.

Runs the swarm coordinator + reasoning synthesis on a query or preset.

Usage:
  python3 -m 6_reasoning_engine "Identify members of fraud ring FR-002"
  python3 -m 6_reasoning_engine --preset funnel-pattern --json
  python3 -m 6_reasoning_engine --preset ring-identification --explain P-005027
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_HERE = Path(__file__).resolve().parent
# Order matters: 4_orchestrator_api MUST be first so its `orchestration`
# package wins over 5_agent_swarm/orchestration/. Use slice-insert to
# preserve the order as given (insert(0, ...) in a loop REVERSES the order).
_paths = [str(p) for p in (
    PROJECT_ROOT / "4_orchestrator_api",
    _HERE,
    PROJECT_ROOT,
    PROJECT_ROOT / "3_graph_intelligence_core",
    PROJECT_ROOT / "5_agent_swarm",
) if str(p) not in sys.path]
sys.path[:0] = _paths


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("query", nargs="?", help="natural-language investigation question")
    g.add_argument("--preset", help="curated preset key")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--depth", type=int, default=2)
    ap.add_argument("--strategy", default="auto")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--explain", help="emit a why-this-entity rationale for this v_id")
    args = ap.parse_args(argv)

    if args.preset:
        from orchestration.presets import get_preset
        p = get_preset(args.preset)
        if not p:
            raise SystemExit(f"preset '{args.preset}' not found")
        query, top_k, depth = p["query"], p["top_k"], p["depth"]
    else:
        query, top_k, depth = args.query, args.top_k, args.depth

    from swarm import SynthesisCoordinator
    from synthesis import synthesize, explain_entity

    coord = SynthesisCoordinator()
    t0 = time.perf_counter()
    swarm_report = coord.run(query, top_k=top_k, depth=depth, strategy=args.strategy)
    engine_result = coord._engine.query(
        query=query,
        config={"strategy": args.strategy, "top_k": top_k, "depth": depth},
    )
    syn = synthesize(swarm_report, engine_result, query=query)
    elapsed = (time.perf_counter() - t0) * 1000

    if args.json:
        out = {
            "swarm": swarm_report.to_dict(),
            "synthesis": syn.to_dict(),
            "elapsed_ms": elapsed,
        }
        if args.explain:
            out["entity_explanation"] = {
                args.explain: explain_entity(engine_result, args.explain),
            }
        print(json.dumps(out, indent=2, default=str))
        return 0

    print(f"\n{'='*72}\nREASONING  query: {query}\n{'='*72}")
    print(f"Elapsed: {elapsed:.0f}ms\n")
    print(f"HEADLINE: {syn.headline}")
    print(f"BODY:     {syn.body}\n")

    print("KEY CLAIMS:")
    for c in syn.key_claims[:12]:
        print(f"  [{c.basis:9s}] {c.statement}   ({c.confidence:.2f})")
    print()

    if syn.contradictions:
        print("CONTRADICTIONS:")
        for x in syn.contradictions[:5]:
            print(f"  ⚠ {x.reason}")
        print()

    print(f"OVERALL STRUCTURAL CONFIDENCE: {syn.overall_confidence:.2f}\n")

    if args.explain:
        print(f"WHY {args.explain} WAS SURFACED:")
        print(f"  {explain_entity(engine_result, args.explain)}\n")
    else:
        print("PER-SUSPECT EXPLANATIONS:")
        for vid, reason in list(syn.explanations.items())[:8]:
            print(f"  {vid:15s} → {reason}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
