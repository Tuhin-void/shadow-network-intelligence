"""
Question Generator - Creates benchmark investigation questions
"""
from typing import List
from ..schemas.entity_registry import EntityRegistry
from ..schemas.benchmark import BenchmarkQuestion, QuestionType
from ..utils.logger import get_logger
import random

logger = get_logger(__name__)


class BenchmarkQuestionGenerator:
    """Generates benchmark questions from fraud rings"""

    TEMPLATES = {
        QuestionType.TRAVERSAL: [
            "Find all entities connected to {entity} within {hops} hops",
            "List all accounts reachable from {entity} through ownership chains",
        ],
        QuestionType.PATH_FINDING: [
            "Trace the laundering path from {source} to {target}",
            "Find the transaction chain from {source} through intermediate to {dest}",
        ],
        QuestionType.FRAUD_RING_IDENTIFICATION: [
            "Identify all entities in the {ring_type} ring starting from {entity}",
            "Find the fraud ring containing {entity}",
        ],
    }

    def generate(self, registry: EntityRegistry, count: int = 50) -> List[BenchmarkQuestion]:
        """Generate benchmark questions from fraud rings"""
        questions = []
        r = random.Random(42)

        for ring in registry.fraud_rings.values():
            if ring.key_entities:
                entity = r.choice(ring.key_entities)
                hops = ring.get_max_hop() or 3

                q = BenchmarkQuestion(
                    id=f"BQ-{ring.id}-001",
                    question=f"Find all entities connected to {entity} within {hops} hops",
                    question_type=QuestionType.TRAVERSAL,
                    required_hops=hops,
                    relevant_entities=ring.entities,
                    relevant_paths=ring.traversal_paths,
                    fraud_ring_id=ring.id,
                    ground_truth_entities=ring.entities,
                    complexity_score=0.5 + (hops * 0.1),
                )
                questions.append(q)

                if len(questions) >= count:
                    break

        logger.info(f"Generated {len(questions)} benchmark questions")
        return questions