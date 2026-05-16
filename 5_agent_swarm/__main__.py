"""
CLI for the professional investigation swarm.

Usage:
  python3 -m 5_agent_swarm "Identify members of fraud ring FR-002"
  python3 -m 5_agent_swarm --preset ring-identification
  python3 -m 5_agent_swarm --preset funnel-pattern --top-k 5 --depth 2 --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_HERE = Path(__file__).resolve().parent
# Slice-insert preserves listed order. 4_orchestrator_api first so its
# orchestration.presets wins over the namesake package under _HERE.
_paths = [str(p) for p in (
    PROJECT_ROOT / "4_orchestrator_api",
    _HERE,
) if str(p) not in sys.path]
sys.path[:0] = _paths


def _load_preset(key: str) -> dict:
    from orchestration.presets import get_preset
    p = get_preset(key)
    if not p:
        raise SystemExit(f"preset '{key}' not found")
    return p


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("query", nargs="?", help="natural-language investigation question")
    g.add_argument("--preset", help="curated preset key (see /demo/presets)")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--depth", type=int, default=2)
    ap.add_argument("--strategy", default="auto")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of human view")
    args = ap.parse_args(argv)

    if args.preset:
        p = _load_preset(args.preset)
        query, top_k, depth = p["query"], p["top_k"], p["depth"]
    else:
        query, top_k, depth = args.query, args.top_k, args.depth

    # Lazy import — booting the engine is heavy.
    from swarm import SynthesisCoordinator

    coord = SynthesisCoordinator()
    report = coord.run(query, top_k=top_k, depth=depth, strategy=args.strategy)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2, default=str))
        return 0

    print(f"\n{'='*72}")
    print(f"INVESTIGATION  {report.investigation_id}")
    print(f"{'='*72}")
    print(f"Query: {report.query}")
    print(f"Elapsed: {report.elapsed_ms:.0f}ms")
    print(f"\nCoordinator: {report.coordinator_summary}\n")
    print(f"Consolidated metrics:")
    for k, v in report.consolidated_metrics.items():
        print(f"  - {k}: {v}")
    print()
    for a in report.agents:
        print(f"── {a.agent.upper()} (confidence {a.confidence:.2f}) ──")
        print(f"   {a.summary}")
        for k, v in a.metrics.items():
            print(f"     • {k}: {v}")
        for n in a.notes:
            print(f"     ⚠ {n}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
