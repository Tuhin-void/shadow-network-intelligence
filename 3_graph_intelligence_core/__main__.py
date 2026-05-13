"""
3_graph_intelligence_core CLI entry point.

Usage:
    python -m 3_graph_intelligence_core <command> [options]

Commands:
    health          Check TigerGraph connectivity
    validate        Validate ShadowGraph schema
    setup           Create schema and install queries
    load <profile>  Load CSV data into TigerGraph
    stats           Show graph statistics
    benchmark       Run retrieval benchmark
    query <text>    Run a graph query
"""
import sys
import argparse
from pathlib import Path

_MOD_DIR = Path(__file__).parent
sys.path.insert(0, str(_MOD_DIR))


def cmd_health(args) -> int:
    from clients.graph_client import GraphClient
    from configs.config import load_config

    config = load_config(args.config)
    dataset = None
    if args.profile:
        try:
            import sys as _sys
            _sys.path.insert(0, str(Path(__file__).parent.parent / "2_baseline_systems"))
            from shared.data_loader import AdaptiveDataLoader
            loader = AdaptiveDataLoader(args.profile)
            dataset = loader.load()
            print(f"  Loaded dataset: {len(dataset.persons)} persons", file=sys.stderr)
        except Exception as e:
            print(f"  Failed to load dataset: {e}", file=sys.stderr)

    client = GraphClient(config, dataset=dataset)
    health = client.health_check()

    print(f"TigerGraph Health Check:")
    print(f"  Mode: {'OFFLINE (fallback)' if health.get('offline_mode') else 'LIVE'}")
    print(f"  Latency: {health.get('latency_ms', 0):.1f}ms")
    if health.get("offline_mode"):
        print(f"  Reason: TigerGraph Cloud requires token auth — using local dataset fallback")
        print(f"  Local entities: {len(client._offline_fallback._entity_index)}")
    for k, v in health.items():
        if k in ("details", "vertex_counts"):
            continue
        status = "✓" if isinstance(v, bool) and v else "?"
        print(f"  {status} {k}: {v}")
    return 0 if health.get("healthy") else 1


def cmd_validate(args) -> int:
    from clients.graph_client import GraphClient
    from validation.schema_validator import SchemaValidator
    from configs.config import load_config

    config = load_config(args.config)
    client = GraphClient(config)
    validator = SchemaValidator(client)
    report = validator.validate()
    print(report)
    return 0 if report.is_valid else 1


def cmd_setup(args) -> int:
    from clients.graph_client import GraphClient
    from ingestion.schema_manager import SchemaManager
    from configs.config import load_config

    config = load_config(args.config)
    client = GraphClient(config)
    manager = SchemaManager(client, dry_run=args.dry_run)
    result = manager.full_setup(gsql_dir=args.gsql_dir)
    print(f"Setup complete: {result}")
    return 0


def cmd_load(args) -> int:
    from clients.graph_client import GraphClient
    from ingestion.loader import GraphLoader
    from configs.config import load_config

    # Live progress: force unbuffered stdout/stderr.
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except Exception:
        pass

    config = load_config(args.config)
    batch_size = args.batch_size or config.ingestion.batch_size
    client = GraphClient(config)
    loader = GraphLoader(client, batch_size=batch_size)
    result = loader.load_profile(
        profile=args.profile,
        source_dir=config.data.source_dir,
        sample_limit=args.sample,
    )
    print(f"Load complete: success={result.get('success')} "
          f"vertices={sum(result.get('vertices', {}).values())} "
          f"edges={sum(result.get('edges', {}).values())}")
    return 0 if result.get("success") else 1


def cmd_stats(args) -> int:
    from clients.graph_client import GraphClient
    from configs.config import load_config

    config = load_config(args.config)
    client = GraphClient(config)

    print("Graph Statistics:")
    for vtype in ["Person", "Company", "Account", "Address", "Device", "Transaction"]:
        count = len(client.get_vertices(vtype, limit=1))
        print(f"  {vtype}: {count} vertices")
    return 0


def cmd_benchmark(args) -> int:
    from clients.graph_client import GraphClient
    from graph_rag.graphrag_engine import GraphRAGEngine
    from metrics.collector import MetricsCollector
    from configs.config import load_config

    config = load_config(args.config)
    client = GraphClient(config)
    engine = GraphRAGEngine(client, config, compression=args.compression)
    collector = MetricsCollector()

    queries = [
        "What accounts have high risk scores?",
        "Find the relationship between P-1 and C-1",
        "Show transaction patterns for account A-1",
    ]

    print("GraphRAG Benchmark:")
    for i, query in enumerate(queries):
        collector.start_retrieval("benchmark")
        result = engine.query(query)
        collector.end_retrieval()
        m = collector.record_result(result.get("metadata", {}), result.get("answer", ""))
        print(f"  [{i+1}] {query[:50]}... -> {len(result.get('entities', []))} entities, {result.get('metadata', {}).get('total_time_ms', 0):.1f}ms")

    agg = collector.aggregate()
    print(f"\nAggregate: {agg}")
    return 0


def cmd_query(args) -> int:
    from clients.graph_client import GraphClient
    from graph_rag.graphrag_engine import GraphRAGEngine
    from configs.config import load_config

    config = load_config(args.config)
    client = GraphClient(config)
    engine = GraphRAGEngine(client, config, compression=args.compression)

    result = engine.query(args.query)
    print(f"Answer: {result.get('answer', 'No answer')}")
    print(f"Entities: {len(result.get('entities', []))}")
    print(f"Neighbors: {len(result.get('context', []))}")
    print(f"Evidence: {len(result.get('sources', []))} items")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="3_graph_intelligence_core",
        description="Shadow Network Intelligence GraphRAG Engine CLI",
    )
    parser.add_argument("--config", default=None, help="Path to config.yaml")

    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("health", help="Check TigerGraph connectivity")
    p.add_argument("--profile", default=None, help="Data profile for offline fallback (small, medium, hackathon_default)")
    p = sub.add_parser("validate", help="Validate ShadowGraph schema")
    p = sub.add_parser("setup", help="Create schema and install queries")
    p.add_argument("--dry-run", action="store_true", help="Dry run mode")
    p.add_argument("--gsql-dir", default=None, help="Directory with GSQL files")

    p = sub.add_parser("load", help="Load CSV data into TigerGraph")
    p.add_argument("profile", help="Data profile (small, medium, hackathon_default)")
    p.add_argument("--sample", type=int, default=None,
                   help="Truncate every CSV to this many rows (smoke-test mode)")
    p.add_argument("--batch-size", type=int, default=None,
                   help="Override config batch_size for upsert calls")

    p = sub.add_parser("stats", help="Show graph statistics")

    p = sub.add_parser("benchmark", help="Run retrieval benchmark")
    p.add_argument("--compression", default="rule_based", choices=["rule_based", "llm"])

    p = sub.add_parser("query", help="Run a graph query")
    p.add_argument("query", help="Query text")
    p.add_argument("--compression", default="rule_based", choices=["rule_based", "llm"])

    args = parser.parse_args()

    commands = {
        "health": cmd_health,
        "validate": cmd_validate,
        "setup": cmd_setup,
        "load": cmd_load,
        "stats": cmd_stats,
        "benchmark": cmd_benchmark,
        "query": cmd_query,
    }

    cmd_fn = commands.get(args.command)
    if cmd_fn:
        try:
            return cmd_fn(args)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())