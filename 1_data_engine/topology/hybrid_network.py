"""
Hybrid Network Injector - Interconnected multiple fraud rings
"""
import random

from .base_topology import BaseTopologyInjector, TopologyResult
from ..schemas.entity_registry import EntityRegistry
from ..schemas.fraud_ring import FraudRingSchema, FraudRingBuilder, Severity, FraudRingType


class HybridNetworkInjector(BaseTopologyInjector):
    """
    Creates hybrid network: multiple fraud rings interconnected.

    Example: Ring1 <-> Ring2 <-> Ring3 forming mega-network
    """

    def inject(self, registry: EntityRegistry) -> TopologyResult:
        """Inject hybrid network topology"""
        existing_rings = list(registry.fraud_rings.keys())
        if len(existing_rings) < 3:
            return TopologyResult(
                success=False,
                edges_created=[],
                entities_involved=[],
                error_message="Not enough existing rings for hybrid network",
            )

        r = random.Random(self.seed)
        num_networks = r.randint(1, 2)

        all_edges = []
        all_entities = []

        for net_num in range(num_networks):
            net_seed = self.seed + net_num * 1000
            net_r = random.Random(net_seed)

            ring_count = net_r.randint(3, 4)
            selected_rings = net_r.sample(existing_rings, ring_count)

            ring_entities = []
            for ring_id in selected_rings:
                ring = registry.get_fraud_ring(ring_id)
                if ring:
                    ring_entities.extend(ring.entities[:2])

            bridge_seed = net_seed + 5000
            bridge_r = random.Random(bridge_seed)

            company_ids = list(registry.companies.keys())
            if len(company_ids) >= 3:
                bridge_companies = bridge_r.sample(company_ids, 3)
                all_entities.extend(bridge_companies)

                for i in range(len(bridge_companies) - 1):
                    from ..schemas.edge import EdgeBuilder, RelationshipType
                    edge = EdgeBuilder.create(
                        from_id=bridge_companies[i],
                        from_type="COMPANY",
                        to_id=bridge_companies[i + 1],
                        to_type="COMPANY",
                        relationship=RelationshipType.ASSOCIATED_WITH,
                        is_fraud_related=True,
                        fraud_ring_id=f"FR-HYBRID-{net_num:02d}",
                    )
                    all_edges.append(edge)
                    registry.add_edge(edge)

            ring = FraudRingSchema(
                id=f"FR-HYBRID-{net_num:02d}",
                ring_type=FraudRingType.HYBRID_NETWORK,
                severity=Severity.CRITICAL,
                name=f"Hybrid Multi-Ring Network {net_num}",
                description=f"Interconnected {ring_count} fraud rings",
                entities=bridge_companies,
                traversal_paths=[bridge_companies],
                key_entities=bridge_companies,
                creation_seed=net_seed,
                metadata={"connected_rings": selected_rings},
            )
            registry.add_fraud_ring(ring)

        return TopologyResult(
            success=True,
            edges_created=all_edges,
            entities_involved=all_entities,
            fraud_ring=None,
        )