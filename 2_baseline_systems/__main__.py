"""
CLI entry point for 2_baseline_systems.

Usage:
    python -m 2_baseline_systems benchmark --profile hackathon_default --tier 3
    python -m 2_baseline_systems benchmark --profile hackathon_default --limit 5 --approaches pure_llm vector_rag
    python -m 2_baseline_systems data --profile hackathon_default
    python -m 2_baseline_systems report --run-id RUN_xxx
    python -m 2_baseline_systems list
    python -m 2_baseline_systems graph-stats --profile hackathon_default
"""
import sys
import json
import argparse
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-30s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger(__name__)


def cmd_benchmark(args):
    from .benchmarking import BenchmarkRunner
    from .analytics import TokenEfficiencyAnalyzer, GraphAnalytics
    from .reports import BenchmarkReportGenerator

    logger.info(f"Starting benchmark: profile={args.profile}, tier={args.tier}, "
                f"approaches={args.approaches}, limit={args.limit}")

    runner = BenchmarkRunner(
        profile=args.profile,
        config={
            "embedder_provider": args.embedder,
            "embedder_model": args.embedder_model or "nomic-embed-text",
            "llm_provider": "mock",
            "llm_model": args.llm_model or "llama3.2",
            "top_k": args.top_k,
            "chunk_size": args.chunk_size,
            "vector_provider": args.vector_provider,
            "graph_provider": args.graph_provider,
            # Optional separate judge LLM for scientific fairness.
            "judge_llm_provider": args.judge_llm,
            "judge_llm_model":    args.judge_model,
        },
    )

    from .shared.data_loader import AdaptiveDataLoader
    data_loader = AdaptiveDataLoader(profile=args.profile)

    graph_analytics = GraphAnalytics(data_loader)
    graph_stats = graph_analytics.compute()
    logger.info(f"Graph stats: {graph_stats['total_entities']} entities, "
                f"{graph_stats['total_edges']} edges, {graph_stats['fraud_ring_count']} fraud rings, "
                f"{graph_stats['total_transactions']} transactions")

    benchmark_run = runner.run_cli(
        profile=args.profile,
        tier=args.tier,
        approaches=args.approaches,
        limit=args.limit,
        output_dir=args.output,
    )

    token_analyzer = TokenEfficiencyAnalyzer()
    token_report = token_analyzer.analyze(benchmark_run)
    logger.info(f"Token efficiency: {token_report.get('comparisons', {})}")

    if args.generate_report:
        report_gen = BenchmarkReportGenerator()
        report_gen.generate(benchmark_run)

    logger.info(f"Benchmark complete: run_id={benchmark_run.run_id}")
    return benchmark_run


def cmd_data(args):
    from .shared.data_loader import AdaptiveDataLoader
    from .shared.document_builder import DocumentBuilder

    logger.info(f"Loading data: profile={args.profile}")
    loader = AdaptiveDataLoader(profile=args.profile)
    dataset = loader.load(force_regenerate=args.regenerate)

    summary = dataset.to_graph_summary()
    logger.info(f"Dataset summary: {summary}")

    if args.build_docs:
        builder = DocumentBuilder(dataset)
        docs = builder.build_all()
        logger.info(f"Built {len(docs)} documents")

    return dataset


def cmd_graph_stats(args):
    from .shared.data_loader import AdaptiveDataLoader
    from .analytics import GraphAnalytics

    loader = AdaptiveDataLoader(profile=args.profile)
    analytics = GraphAnalytics(loader)
    stats = analytics.compute()

    print("\n" + "=" * 60)
    print("GRAPH STATISTICS")
    print("=" * 60)
    print(f"Total Entities:    {stats['total_entities']:,}")
    print(f"Total Edges:       {stats['total_edges']:,}")
    print(f"Total Transactions:{stats['by_type']['transactions']:,}")
    print(f"Graph Density:     {stats['graph_density']:.6f}")
    print(f"Avg Degree:        {stats['avg_degree']:.4f}")
    print(f"Max Degree:        {stats['max_degree']}")
    print(f"Fraud Rings:       {stats['fraud_ring_count']}")
    print(f"Fraud Edges:       {stats['fraud_edges']}")
    print(f"Offshore Co's:     {stats['offshore_companies']}")
    print(f"Shell Co's:        {stats['shell_companies']}")
    print(f"Mule Accounts:     {stats['mule_accounts']}")
    print(f"  Persons:         {stats['by_type']['persons']:,}")
    print(f"  Companies:       {stats['by_type']['companies']:,}")
    print(f"  Accounts:        {stats['by_type']['accounts']:,}")
    print(f"  Addresses:       {stats['by_type']['addresses']:,}")
    print(f"  Transactions:    {stats['by_type']['transactions']:,}")
    print("=" * 60)

    return stats


def cmd_list(args):
    output_dir = Path(args.output_dir or "2_baseline_systems/outputs/benchmark_results")
    runs = sorted(output_dir.glob("benchmark_*.json"), reverse=True)
    print(f"\nAvailable benchmark runs in {output_dir}:")
    if not runs:
        print("  No benchmark runs found.")
        return
    for r in runs[:10]:
        with open(r) as f:
            d = json.load(f)
        ts = d.get("timestamp", "unknown")
        ts_str = ts[:19] if isinstance(ts, str) else str(ts)
        profile = d.get("profile", "?")
        queries = d.get("queries_run", "?")
        approaches = list(d.get("results", {}).keys())
        print(f"  {d.get('run_id', r.stem)}  {ts_str}  profile={profile}  queries={queries}  [{', '.join(approaches)}]")
    print(f"\n  Total: {len(runs)} runs")
    print(f"\n  Usage: python -m 2_baseline_systems report --run-id <RUN_ID>")
    print(f"  Usage: python -m 2_baseline_systems benchmark --profile small --limit 5")


def cmd_report(args):
    from .reports import BenchmarkReportGenerator
    from .shared.schemas import BenchmarkRun

    output_dir = Path(args.output_dir or "2_baseline_systems/outputs/benchmark_results")

    if args.run_id:
        run_file = output_dir / f"benchmark_{args.run_id}.json"
        if not run_file.exists():
            logger.error(f"Run file not found: {run_file}")
            print(f"\nAvailable runs:")
            for r in sorted(output_dir.glob("benchmark_*.json"), reverse=True)[:10]:
                print(f"  {r.stem.replace('benchmark_', '')}")
            return

        with open(run_file) as f:
            run_data = json.load(f)
        run = BenchmarkRun(**run_data)
        report_gen = BenchmarkReportGenerator(output_dir)
        report = report_gen.generate(run)
        print(f"\nReport generated: {output_dir}/report_{run.run_id}.json")
        return report

    print(f"\nAvailable runs in {output_dir}:")
    runs = sorted(output_dir.glob("benchmark_*.json"), reverse=True)
    if not runs:
        print("  No benchmark runs found.")
        return
    for r in runs[:10]:
        with open(r) as f:
            d = json.load(f)
        ts = d.get("timestamp", "unknown")
        profile = d.get("profile", "?")
        queries = d.get("queries_run", "?")
        print(f"  {d.get('run_id', r.stem)}  [{ts[:19] if isinstance(ts, str) else ts}] "
              f"profile={profile}, queries={queries}")
    print(f"\n  Total: {len(runs)} runs")
    print(f"\n  Usage: python -m 2_baseline_systems report --run-id RUN_xxxxxx")


def main():
    parser = argparse.ArgumentParser(description="2_baseline_systems - Retrieval Benchmarking Framework")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    subparsers = parser.add_subparsers(dest="command", required=True)

    bench_parser = subparsers.add_parser("benchmark", help="Run benchmark across all pipelines")
    bench_parser.add_argument("--profile", default="hackathon_default", help="Data profile (small/medium/large/hackathon_default)")
    bench_parser.add_argument("--tier", type=int, default=None, help="Filter queries by difficulty tier (1-5)")
    bench_parser.add_argument("--approaches", nargs="+", default=["pure_llm", "vector_rag", "graph_rag"],
                              help="Pipelines to run")
    bench_parser.add_argument("--limit", type=int, default=0, help="Limit number of queries")
    bench_parser.add_argument("--output", type=str, default=None, help="Output directory")
    bench_parser.add_argument("--embedder", default="nim", choices=["ollama", "openai", "mock", "nim"])
    bench_parser.add_argument("--embedder-model", default=None)
    bench_parser.add_argument("--llm", default="ollama", choices=["ollama", "openai", "anthropic", "mock"])
    bench_parser.add_argument("--llm-model", default=None)
    bench_parser.add_argument("--judge-llm", default=None, choices=["ollama", "openai", "anthropic", "mock", None],
                              help="LLM provider for the judge (defaults to pipeline LLM — NOT recommended for fair scoring)")
    bench_parser.add_argument("--judge-model", default=None,
                              help="Model name for the judge LLM (use this together with --judge-llm)")
    bench_parser.add_argument("--top-k", type=int, default=10)
    bench_parser.add_argument("--chunk-size", type=int, default=500)
    bench_parser.add_argument("--graph-provider", default="mock", choices=["mock", "tigergraph"],
                              help="Graph retriever provider for graph_rag pipeline")
    bench_parser.add_argument("--vector-provider", default="chroma", choices=["chroma", "mock"],
                              help="Vector store provider for vector_rag pipeline")
    bench_parser.add_argument("--generate-report", action="store_true", help="Generate benchmark report")

    data_parser = subparsers.add_parser("data", help="Load and inspect data from 1_data_engine")
    data_parser.add_argument("--profile", default="hackathon_default")
    data_parser.add_argument("--regenerate", action="store_true", help="Force regenerate data")
    data_parser.add_argument("--build-docs", action="store_true", help="Build RAG documents")

    stats_parser = subparsers.add_parser("graph-stats", help="Print graph statistics")
    stats_parser.add_argument("--profile", default="hackathon_default")

    report_parser = subparsers.add_parser("report", help="Generate or view benchmark reports")
    report_parser.add_argument("--run-id", type=str, default=None, help="Run ID to generate report for")
    report_parser.add_argument("--output-dir", type=str, default=None, help="Output directory")

    list_parser = subparsers.add_parser("list", help="List available benchmark runs")
    list_parser.add_argument("--output-dir", type=str, default=None, help="Output directory")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        if args.command == "benchmark":
            cmd_benchmark(args)
        elif args.command == "data":
            cmd_data(args)
        elif args.command == "graph-stats":
            cmd_graph_stats(args)
        elif args.command == "report":
            cmd_report(args)
        elif args.command == "list":
            cmd_list(args)
        else:
            parser.print_help()
    except Exception as e:
        logger.error(f"Command failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()