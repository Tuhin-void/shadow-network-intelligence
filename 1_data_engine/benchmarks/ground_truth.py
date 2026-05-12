"""
Ground Truth Builder - Creates benchmark ground truth
"""
from typing import List, Dict
from ..schemas.entity_registry import EntityRegistry
from ..utils.logger import get_logger

logger = get_logger(__name__)


class GroundTruthBuilder:
    """Builds ground truth for benchmark evaluation"""

    def build(self, registry: EntityRegistry) -> Dict:
        """Build ground truth from fraud rings"""
        ground_truth = {
            "fraud_rings": {},
            "traversal_paths": [],
            "key_entities": [],
            "metadata": {
                "total_rings": registry.get_fraud_ring_count(),
                "total_entities": registry.get_entity_count(),
            },
        }

        for ring in registry.fraud_rings.values():
            ground_truth["fraud_rings"][ring.id] = {
                "type": ring.ring_type.value,
                "entities": ring.entities,
                "paths": ring.traversal_paths,
                "key_entities": ring.key_entities,
            }
            ground_truth["traversal_paths"].extend(ring.traversal_paths)
            ground_truth["key_entities"].extend(ring.key_entities)

        logger.info(f"Built ground truth: {len(ground_truth['fraud_rings'])} rings")
        return ground_truth