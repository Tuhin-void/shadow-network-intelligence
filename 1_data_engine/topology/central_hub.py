"""
Central Hub Injector - High-centrality node connecting multiple rings
"""
import random

from .base_topology import BaseTopologyInjector, TopologyResult
from ..schemas.entity_registry import EntityRegistry
from ..schemas.transaction import TransactionGenerator
from ..schemas.fraud_ring import FraudRingSchema, FraudRingBuilder, Severity, FraudRingType


class CentralHubInjector(BaseTopologyInjector):
    """
    Creates a central hub: high-centrality account connecting multiple fraud rings.

    Example: Hub A connects to Ring1, Ring2, Ring3
    """

    def inject(self, registry: EntityRegistry) -> TopologyResult:
        """Inject central hub topology"""
        account_ids = list(registry.accounts.keys())
        if len(account_ids) < 15:
            return TopologyResult(
                success=False,
                edges_created=[],
                entities_involved=[],
                error_message="Not enough accounts for central hub",
            )

        r = random.Random(self.seed)
        hub_seed = self.seed
        hub_r = random.Random(hub_seed)

        hub_account = hub_r.choice(account_ids)
        connected_accounts = hub_r.sample([a for a in account_ids if a != hub_account], 12)

        tx_gen = TransactionGenerator(seed=self.seed)
        all_edges = []
        all_accounts = [hub_account] + connected_accounts

        for i, source in enumerate(connected_accounts):
            amount = hub_r.randint(50000, 500000)

            tx = tx_gen.generate(
                from_account=source,
                to_account=hub_account,
                inject_fraud={"type": "hub"},
            )
            registry.add_transaction(tx)

            edge = self._create_transfer_edge(
                from_account=source,
                to_account=hub_account,
                amount=amount,
                fraud_ring_id="FR-HUB-001",
            )
            all_edges.append(edge)
            registry.add_edge(edge)

        ring = FraudRingSchema(
            id="FR-HUB-001",
            ring_type=FraudRingType.CENTRAL_HUB,
            severity=Severity.CRITICAL,
            name="Central Laundering Hub",
            description="High-centrality account connecting multiple fraud rings",
            entities=all_accounts,
            traversal_paths=[connected_accounts + [hub_account]],
            key_entities=[hub_account],
            expected_questions=[
                f"Find the central hub connecting fraud rings",
                f"Identify accounts with highest betweenness centrality",
            ],
            creation_seed=hub_seed,
            metadata={"connections": len(connected_accounts), "hub_id": hub_account},
        )
        registry.add_fraud_ring(ring)

        return TopologyResult(
            success=True,
            edges_created=all_edges,
            entities_involved=all_accounts,
            fraud_ring=ring,
        )