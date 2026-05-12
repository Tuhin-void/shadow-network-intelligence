"""
Circular Ownership Injector - Shell companies with circular ownership
"""
import random
from typing import List

from .base_topology import BaseTopologyInjector, TopologyResult
from ..schemas.entity_registry import EntityRegistry
from ..schemas.edge import RelationshipType
from ..schemas.fraud_ring import FraudRingSchema, FraudRingBuilder, Severity


class CircularOwnershipInjector(BaseTopologyInjector):
    """
    Creates circular ownership rings where shell companies own each other.

    Example: C1 owns C2, C2 owns C3, C3 owns C1
    """

    def inject(self, registry: EntityRegistry) -> TopologyResult:
        """Inject circular ownership topology"""
        company_ids = list(registry.companies.keys())
        if len(company_ids) < 4:
            return TopologyResult(
                success=False,
                edges_created=[],
                entities_involved=[],
                error_message="Not enough companies for circular ownership",
            )

        r = random.Random(self.seed)
        num_rings = r.randint(2, 3)

        all_edges = []
        all_companies = []

        for ring_num in range(num_rings):
            ring_size = r.randint(3, 5)
            ring_seed = self.seed + ring_num * 1000
            ring_r = random.Random(ring_seed)

            selected_companies = ring_r.sample(company_ids, ring_size)
            all_companies.extend(selected_companies)

            for i in range(ring_size):
                from_company = selected_companies[i]
                to_company = selected_companies[(i + 1) % ring_size]

                edge = self._create_edge(
                    from_id=from_company,
                    from_type="COMPANY",
                    to_id=to_company,
                    to_type="COMPANY",
                    relationship=RelationshipType.OWNS,
                    fraud_ring_id=f"FR-CIRC-{ring_num:02d}",
                )
                all_edges.append(edge)
                registry.add_edge(edge)

            traversal_path = selected_companies + [selected_companies[0]]

            ring = FraudRingBuilder.build_circular_ownership(
                ring_id=f"FR-CIRC-{ring_num:02d}",
                companies=selected_companies,
                traversal_paths=[traversal_path],
                seed=ring_seed,
            )
            registry.add_fraud_ring(ring)

        return TopologyResult(
            success=True,
            edges_created=all_edges,
            entities_involved=all_companies,
            fraud_ring=None,
        )