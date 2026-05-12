"""
Laundering Chain Injector - Multi-hop transaction layering
"""
import random

from .base_topology import BaseTopologyInjector, TopologyResult
from ..schemas.entity_registry import EntityRegistry
from ..schemas.transaction import TransactionGenerator
from ..schemas.fraud_ring import FraudRingSchema, FraudRingBuilder, Severity, FraudRingType


class LaunderingChainInjector(BaseTopologyInjector):
    """
    Creates multi-hop laundering chains: funds routed through multiple accounts.

    Example: A1 -> A2 -> A3 -> A4 -> A5
    """

    def inject(self, registry: EntityRegistry) -> TopologyResult:
        """Inject laundering chain topology"""
        account_ids = list(registry.accounts.keys())
        if len(account_ids) < 10:
            return TopologyResult(
                success=False,
                edges_created=[],
                entities_involved=[],
                error_message="Not enough accounts for laundering chain",
            )

        r = random.Random(self.seed)
        num_chains = r.randint(3, 4)

        all_edges = []
        all_accounts = []
        tx_gen = TransactionGenerator(seed=self.seed)

        for chain_num in range(num_chains):
            chain_length = r.randint(5, 7)
            chain_seed = self.seed + chain_num * 1000
            chain_r = random.Random(chain_seed)

            available = [a for a in account_ids if a not in all_accounts]
            if len(available) < chain_length:
                continue

            chain = chain_r.sample(available, chain_length)
            all_accounts.extend(chain)

            for i in range(len(chain) - 1):
                tx = tx_gen.generate(
                    from_account=chain[i],
                    to_account=chain[i + 1],
                    inject_fraud={"type": "layering"},
                )
                registry.add_transaction(tx)

                edge = self._create_transfer_edge(
                    from_account=chain[i],
                    to_account=chain[i + 1],
                    amount=tx.amount,
                    fraud_ring_id=f"FR-LAYER-{chain_num:02d}",
                )
                all_edges.append(edge)
                registry.add_edge(edge)

            ring = FraudRingSchema(
                id=f"FR-LAYER-{chain_num:02d}",
                ring_type=FraudRingType.LAYERING_CHAIN,
                severity=Severity.CRITICAL,
                name=f"Laundering Chain {chain_num}",
                description=f"Multi-hop chain with {chain_length} accounts",
                entities=chain,
                traversal_paths=[chain],
                key_entities=[chain[0]],
                expected_graph_paths=[
                    f"{chain[i]}->TRANSFERRED_TO->{chain[i+1]}" for i in range(len(chain)-1)
                ],
                creation_seed=chain_seed,
            )
            registry.add_fraud_ring(ring)

        return TopologyResult(
            success=True,
            edges_created=all_edges,
            entities_involved=all_accounts,
            fraud_ring=None,
        )