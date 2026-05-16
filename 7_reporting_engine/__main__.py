"""
CLI for the reporting engine.

  python3 -m 7_reporting_engine brief    --preset ring-identification
  python3 -m 7_reporting_engine ring     --ring FR-002
  python3 -m 7_reporting_engine sanc     --preset ring-identification
  python3 -m 7_reporting_engine bench
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_HERE = Path(__file__).resolve().parent
# Slice-insert preserves listed order at front of sys.path.
# 4_orchestrator_api comes first so its `orchestration.presets` wins over
# 5_agent_swarm's namesake package.
_paths = [str(p) for p in (
    PROJECT_ROOT / "4_orchestrator_api",
    _HERE,
    PROJECT_ROOT,
    PROJECT_ROOT / "3_graph_intelligence_core",
    PROJECT_ROOT / "5_agent_swarm",
    PROJECT_ROOT / "6_reasoning_engine",
) if str(p) not in sys.path]
sys.path[:0] = _paths


def _resolve_query(preset: str | None, query: str | None,
                   top_k: int = 5, depth: int = 2) -> tuple[str, int, int]:
    if preset:
        from orchestration.presets import get_preset
        p = get_preset(preset)
        if not p:
            raise SystemExit(f"preset '{preset}' not found")
        return p["query"], p["top_k"], p["depth"]
    if not query:
        raise SystemExit("either --preset or a positional query is required")
    return query, top_k, depth


def _run_swarm(query: str, top_k: int, depth: int) -> tuple:
    from swarm import SynthesisCoordinator
    from synthesis import synthesize
    coord = SynthesisCoordinator()
    swarm_report = coord.run(query, top_k=top_k, depth=depth)
    engine_result = coord._engine.query(
        query=query, config={"top_k": top_k, "depth": depth, "strategy": "auto"},
    )
    syn = synthesize(swarm_report, engine_result, query=query)
    return engine_result, swarm_report, syn


def _cmd_brief(args) -> int:
    from generators import InvestigationBriefGenerator
    query, top_k, depth = _resolve_query(args.preset, args.query, args.top_k, args.depth)
    engine_result, swarm_report, syn = _run_swarm(query, top_k, depth)
    rep = InvestigationBriefGenerator().generate(
        query=query, engine_result=engine_result,
        swarm_report=swarm_report, synthesis=syn,
    )
    print(f"Brief → {rep.markdown_path}")
    print(f"JSON  → {rep.json_path}")
    return 0


def _cmd_ring(args) -> int:
    from generators import FraudRingSummaryGenerator
    query = (f"Reconstruct fraud ring {args.ring}: list every person, company, "
             f"account, transaction structurally tied to the ring.")
    engine_result, swarm_report, syn = _run_swarm(query, top_k=5, depth=2)
    rep = FraudRingSummaryGenerator().generate(
        ring_id=args.ring, engine_result=engine_result,
        swarm_report=swarm_report, synthesis=syn,
    )
    print(f"Ring summary → {rep.markdown_path}")
    print(f"JSON         → {rep.json_path}")
    return 0


def _cmd_sanc(args) -> int:
    from generators import SanctionsExposureReportGenerator
    query, top_k, depth = _resolve_query(args.preset, args.query, args.top_k, args.depth)
    _, swarm_report, syn = _run_swarm(query, top_k, depth)
    rep = SanctionsExposureReportGenerator().generate(
        query=query, swarm_report=swarm_report, synthesis=syn,
    )
    print(f"Sanctions report → {rep.markdown_path}")
    print(f"JSON             → {rep.json_path}")
    return 0


def _cmd_bench(args) -> int:
    from generators import BenchmarkSummaryGenerator
    rep = BenchmarkSummaryGenerator().generate(project_root=PROJECT_ROOT)
    print(f"Benchmark summary → {rep.markdown_path}")
    print(f"JSON              → {rep.json_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_brief = sub.add_parser("brief", help="general investigation brief")
    p_brief.add_argument("query", nargs="?")
    p_brief.add_argument("--preset")
    p_brief.add_argument("--top-k", type=int, default=5)
    p_brief.add_argument("--depth", type=int, default=2)
    p_brief.set_defaults(func=_cmd_brief)

    p_ring = sub.add_parser("ring", help="fraud ring summary")
    p_ring.add_argument("--ring", required=True, help="ring id, e.g. FR-002")
    p_ring.set_defaults(func=_cmd_ring)

    p_sanc = sub.add_parser("sanc", help="sanctions exposure report")
    p_sanc.add_argument("query", nargs="?")
    p_sanc.add_argument("--preset")
    p_sanc.add_argument("--top-k", type=int, default=5)
    p_sanc.add_argument("--depth", type=int, default=2)
    p_sanc.set_defaults(func=_cmd_sanc)

    p_bench = sub.add_parser("bench", help="consolidated benchmark summary")
    p_bench.set_defaults(func=_cmd_bench)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
