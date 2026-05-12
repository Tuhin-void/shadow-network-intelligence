"""
Graph Integrity Validator - Validates vertex/edge consistency
"""
from typing import Dict, List, Tuple
from dataclasses import dataclass

from ..schemas.entity_registry import EntityRegistry
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class IntegrityReport:
    """Report of graph integrity validation"""

    valid: bool
    total_entities: int
    total_edges: int
    orphaned_edges: int
    missing_references: List[str]
    duplicate_edges: List[str]


class GraphIntegrityValidator:
    """Validates graph integrity - vertex/edge consistency"""

    def validate(self, registry: EntityRegistry) -> IntegrityReport:
        """Validate graph integrity"""
        logger.info("Validating graph integrity...")

        orphaned_edges = []
        missing_refs = []
        seen_edges = set()

        for edge in registry.edges.values():
            edge_key = f"{edge.from_id}|{edge.relationship.value}|{edge.to_id}"

            if edge_key in seen_edges:
                orphaned_edges.append(edge.id)
            seen_edges.add(edge_key)

            from_entity = registry.get_entity(edge.from_id)
            to_entity = registry.get_entity(edge.to_id)

            if not from_entity:
                missing_refs.append(f"Edge {edge.id} references missing {edge.from_id}")
            if not to_entity:
                missing_refs.append(f"Edge {edge.id} references missing {edge.to_id}")

        report = IntegrityReport(
            valid=len(missing_refs) == 0,
            total_entities=registry.get_entity_count(),
            total_edges=len(registry.edges),
            orphaned_edges=len(orphaned_edges),
            missing_references=missing_refs[:10],
            duplicate_edges=orphaned_edges[:10],
        )

        logger.info(f"  Entities: {report.total_entities}, Edges: {report.total_edges}")
        logger.info(f"  Valid: {report.valid}")

        return report