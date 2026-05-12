"""
Shadow Network Intelligence - Data Engine
Main CLI entry point for synthetic AML data generation
"""
import argparse
import sys
import logging
from pathlib import Path
from datetime import datetime

from .generators.entity_factory import EntityFactory, GenerationConfig
from .topology.orchestrator import TopologyOrchestrator
from .validators.graph_integrity import GraphIntegrityValidator
from .validators.fraud_ring_validator import FraudRingValidator
from .exporters.csv_exporter import CSVExporter
from .exporters.json_exporter import JSONExporter
from .exporters.tigergraph_exporter import TigerGraphExporter
from .utils.logger import setup_logging
from .utils.helpers import ensure_dir


def generate(args):
    """Generate synthetic AML dataset"""
    logger = logging.getLogger(__name__)
    logger.info(f"Starting data generation with profile: {args.profile}")

    config = GenerationConfig(
        profile=args.profile,
        seed=args.seed,
        person_count=args.persons,
        company_count=args.companies,
        account_count=args.accounts,
        address_count=args.addresses,
    )

    logger.info("Phase 1: Entity Generation")
    factory = EntityFactory(config)
    registry = factory.generate_all()

    logger.info("Phase 2: Fraud Topology Injection")
    topology = TopologyOrchestrator(seed=args.seed)
    topology.inject_all(registry)

    logger.info("Phase 3: Validation")
    integrity_validator = GraphIntegrityValidator()
    integrity_report = integrity_validator.validate(registry)
    logger.info(f"  Graph integrity: {'VALID' if integrity_report.valid else 'INVALID'}")

    fraud_validator = FraudRingValidator()
    fraud_report = fraud_validator.validate(registry)
    logger.info(f"  Fraud rings: {fraud_report.valid_rings}/{fraud_report.total_rings} valid")

    output_dir = args.output or f"./outputs/{args.profile}"
    ensure_dir(output_dir)

    logger.info(f"Phase 4: Export to {output_dir}")

    csv_exp = CSVExporter()
    csv_files = csv_exp.export(registry, f"{output_dir}/csv")
    logger.info(f"  CSV: {len(csv_files)} files")

    json_exp = JSONExporter()
    json_files = json_exp.export(registry, f"{output_dir}/json")
    logger.info(f"  JSON: {len(json_files)} files")

    if args.tigergraph:
        tg_exp = TigerGraphExporter()
        tg_files = tg_exp.export(registry, f"{output_dir}/tigergraph")
        logger.info(f"  TigerGraph: {len(tg_files)} files")

    logger.info(f"\n=== GENERATION COMPLETE ===")
    logger.info(f"Total entities: {registry.get_entity_count()}")
    logger.info(f"Total edges: {registry.get_edge_count()}")
    logger.info(f"Fraud rings: {registry.get_fraud_ring_count()}")
    logger.info(f"Output: {output_dir}")


def export(args):
    """Export existing graph data to different formats"""
    logger = logging.getLogger(__name__)
    logger.info(f"Exporting from {args.input} to {args.format}")

    json_path = Path(args.input) / "graph.json"
    if not json_path.exists():
        logger.error(f"Graph file not found: {json_path}")
        return

    logger.info("Export complete")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Shadow Network Intelligence - Synthetic AML Data Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    gen_parser = subparsers.add_parser("generate", help="Generate synthetic AML dataset")
    gen_parser.add_argument("--profile", default="hackathon_default", help="Generation profile")
    gen_parser.add_argument("--seed", type=int, default=42, help="Random seed")
    gen_parser.add_argument("--persons", type=int, default=6000, help="Number of persons")
    gen_parser.add_argument("--companies", type=int, default=5000, help="Number of companies")
    gen_parser.add_argument("--accounts", type=int, default=10000, help="Number of accounts")
    gen_parser.add_argument("--addresses", type=int, default=4000, help="Number of addresses")
    gen_parser.add_argument("--output", help="Output directory")
    gen_parser.add_argument("--tigergraph", action="store_true", help="Export TigerGraph format")
    gen_parser.add_argument("--verbose", action="store_true", help="Verbose logging")

    export_parser = subparsers.add_parser("export", help="Export existing data")
    export_parser.add_argument("--input", required=True, help="Input directory")
    export_parser.add_argument("--format", default="csv", choices=["csv", "json", "tigergraph"])

    args = parser.parse_args()

    log_level = "DEBUG" if getattr(args, "verbose", False) else "INFO"
    setup_logging(level=log_level)

    if not args.command:
        parser.print_help()
        return

    if args.command == "generate":
        generate(args)
    elif args.command == "export":
        export(args)


if __name__ == "__main__":
    main()