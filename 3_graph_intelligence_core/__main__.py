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


def cmd_health(args) -> int:
    from clients.graph_client import GraphClient
    from configs.config import load_config

    config = load_config(args.config)
    client = GraphClient(config)
    health = client.health_check()

    print(f"TigerGraph Health Check:")
    for k, v in health.items():
        status = "✓" if isinstance(v, bool) and v else "✗" if k != "healthy" else "✓"
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

    config = load_config(args.config)
    client = GraphClient(config)
    loader = GraphLoader(client, batch_size=config.ingestion.batch_size)
    result = loader.load_profile(profile=args.profile, source_dir=config.data.source_dir)
    print(f"Load complete: {result}")
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
    p = sub.add_parser("validate", help="Validate ShadowGraph schema")
    p = sub.add_parser("setup", help="Create schema and install queries")
    p.add_argument("--dry-run", action="store_true", help="Dry run mode")
    p.add_argument("--gsql-dir", default=None, help="Directory with GSQL files")

    p = sub.add_parser("load", help="Load CSV data into TigerGraph")
    p.add_argument("profile", help="Data profile (small, medium, hackathon_default)")

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