"""
Address Collision Injector - Multiple entities sharing same address
"""
import random

from .base_topology import BaseTopologyInjector, TopologyResult
from ..schemas.entity_registry import EntityRegistry
from ..schemas.edge import RelationshipType
from ..schemas.fraud_ring import FraudRingSchema, FraudRingBuilder, Severity, FraudRingType


class AddressCollisionInjector(BaseTopologyInjector):
    """
    Creates address collision clusters: multiple entities at same address.

    Example: P1, P2, C1 all at Address X
    """

    def inject(self, registry: EntityRegistry) -> TopologyResult:
        """Inject address collision topology"""
        if len(registry.addresses) < 3:
            return TopologyResult(
                success=False,
                edges_created=[],
                entities_involved=[],
                error_message="Not enough addresses for collision",
            )

        r = random.Random(self.seed)
        num_collisions = r.randint(8, 12)

        all_edges = []
        address_ids = list(registry.addresses.keys())
        person_ids = list(registry.persons.keys())
        company_ids = list(registry.companies.keys())

        for coll_num in range(num_collisions):
            coll_seed = self.seed + coll_num * 1000
            coll_r = random.Random(coll_seed)

            address = coll_r.choice(address_ids)
            entity_count = coll_r.randint(3, 8)

            entities = []
            for _ in range(entity_count):
                if person_ids and coll_r.random() < 0.6:
                    entity = coll_r.choice(person_ids)
                    entity_type = "PERSON"
                elif company_ids:
                    entity = coll_r.choice(company_ids)
                    entity_type = "COMPANY"
                else:
                    continue

                edge = self._create_edge(
                    from_id=entity,
                    from_type=entity_type,
                    to_id=address,
                    to_type="ADDRESS",
                    relationship=RelationshipType.LOCATED_AT,
                    fraud_ring_id=f"FR-ADDR-{coll_num:02d}",
                )
                all_edges.append(edge)
                registry.add_edge(edge)
                entities.append(entity)

            if entities:
                ring = FraudRingBuilder.build_address_collision(
                    ring_id=f"FR-ADDR-{coll_num:02d}",
                    address_id=address,
                    entities=entities,
                    seed=coll_seed,
                )
                registry.add_fraud_ring(ring)

        return TopologyResult(
            success=True,
            edges_created=all_edges,
            entities_involved=[],
            fraud_ring=None,
        )