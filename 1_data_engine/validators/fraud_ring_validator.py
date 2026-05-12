"""
Fraud Ring Validator - Validates fraud ring existence and traversability
"""
from typing import Dict, List
from dataclasses import dataclass

from ..schemas.entity_registry import EntityRegistry
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FraudRingReport:
    """Report of fraud ring validation"""

    valid: bool
    total_rings: int
    valid_rings: int
    invalid_rings: List[str]
    ring_details: Dict


class FraudRingValidator:
    """Validates fraud rings exist and are traversable"""

    def validate(self, registry: EntityRegistry) -> FraudRingReport:
        """Validate all fraud rings"""
        logger.info("Validating fraud rings...")

        valid_rings = []
        invalid_rings = []
        ring_details = {}

        for ring in registry.fraud_rings.values():
            ring_valid = True

            for entity_id in ring.entities:
                if not registry.get_entity(entity_id):
                    ring_valid = False
                    invalid_rings.append(f"{ring.id}: missing entity {entity_id}")
                    break

            for path in ring.traversal_paths:
                for i, entity_id in enumerate(path):
                    if not registry.get_entity(entity_id):
                        ring_valid = False

            if ring_valid:
                valid_rings.append(ring.id)

            ring_details[ring.id] = {
                "type": ring.ring_type.value,
                "entities": len(ring.entities),
                "traversal_paths": len(ring.traversal_paths),
                "valid": ring_valid,
            }

        report = FraudRingReport(
            valid=len(invalid_rings) == 0,
            total_rings=len(registry.fraud_rings),
            valid_rings=len(valid_rings),
            invalid_rings=invalid_rings,
            ring_details=ring_details,
        )

        logger.info(f"  Total rings: {report.total_rings}, Valid: {report.valid_rings}")

        return report