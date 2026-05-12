"""
Offshore Routing Injector - Cross-border laundering chains
"""
import random

from .base_topology import BaseTopologyInjector, TopologyResult
from ..schemas.entity_registry import EntityRegistry
from ..schemas.transaction import TransactionGenerator
from ..schemas.fraud_ring import FraudRingSchema, FraudRingBuilder, Severity, FraudRingType


class OffshoreRoutingInjector(BaseTopologyInjector):
    """
    Creates offshore routing: funds transferred to offshore jurisdictions.

    Example: Domestic A -> Offshore A -> Offshore B -> Return
    """

    OFFSHORE_CODES = ["KY", "VG", "BS", "PA", "CH", "LU"]

    def inject(self, registry: EntityRegistry) -> TopologyResult:
        """Inject offshore routing topology"""
        account_ids = list(registry.accounts.keys())
        company_ids = list(registry.companies.keys())

        if len(account_ids) < 6 or len(company_ids) < 2:
            return TopologyResult(
                success=False,
                edges_created=[],
                entities_involved=[],
                error_message="Not enough entities for offshore routing",
            )

        r = random.Random(self.seed)
        num_routes = r.randint(1, 2)

        all_edges = []
        all_entities = []
        tx_gen = TransactionGenerator(seed=self.seed)

        for route_num in range(num_routes):
            route_seed = self.seed + route_num * 1000
            route_r = random.Random(route_seed)

            chain = route_r.sample(account_ids, 4)
            offshore_entity = route_r.choice([c for c in company_ids if "offshore" in c.lower() or route_r.random() < 0.3])

            all_entities.extend(chain)
            all_entities.append(offshore_entity)

            for i in range(len(chain) - 1):
                tx = tx_gen.generate(
                    from_account=chain[i],
                    to_account=chain[i + 1],
                    inject_fraud={"type": "offshore"},
                )
                registry.add_transaction(tx)

                edge = self._create_transfer_edge(
                    from_account=chain[i],
                    to_account=chain[i + 1],
                    amount=tx.amount,
                    fraud_ring_id=f"FR-OFFSHORE-{route_num:02d}",
                )
                all_edges.append(edge)
                registry.add_edge(edge)

            ring = FraudRingSchema(
                id=f"FR-OFFSHORE-{route_num:02d}",
                ring_type=FraudRingType.OFFSHORE_ROUTING,
                severity=Severity.CRITICAL,
                name=f"Offshore Routing {route_num}",
                description="Cross-border fund transfers to offshore jurisdictions",
                entities=chain + [offshore_entity],
                traversal_paths=[chain],
                key_entities=[chain[0], offshore_entity],
                creation_seed=route_seed,
                metadata={"offshore_jurisdictions": self.OFFSHORE_CODES[:2]},
            )
            registry.add_fraud_ring(ring)

        return TopologyResult(
            success=True,
            edges_created=all_edges,
            entities_involved=all_entities,
            fraud_ring=None,
        )