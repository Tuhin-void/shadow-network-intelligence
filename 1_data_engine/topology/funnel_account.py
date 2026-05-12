"""
Funnel Account Injector - Hub-spoke funnel structure
"""
import random

from .base_topology import BaseTopologyInjector, TopologyResult
from ..schemas.entity_registry import EntityRegistry
from ..schemas.edge import RelationshipType
from ..schemas.fraud_ring import FraudRingSchema, FraudRingBuilder, Severity


class FunnelAccountInjector(BaseTopologyInjector):
    """
    Creates funnel accounts: many source accounts funnel to single laundering hub.

    Example: A1, A2, A3 -> Funnel A
    """

    def inject(self, registry: EntityRegistry) -> TopologyResult:
        """Inject funnel account topology"""
        account_ids = list(registry.accounts.keys())
        if len(account_ids) < 6:
            return TopologyResult(
                success=False,
                edges_created=[],
                entities_involved=[],
                error_message="Not enough accounts for funnel",
            )

        r = random.Random(self.seed)
        num_funnels = r.randint(3, 5)

        all_edges = []
        all_accounts = []

        for funnel_num in range(num_funnels):
            sources_per_funnel = r.randint(5, 12)
            funnel_seed = self.seed + funnel_num * 1000
            funnel_r = random.Random(funnel_seed)

            available_accounts = [a for a in account_ids if a not in all_accounts]
            if len(available_accounts) < sources_per_funnel + 1:
                continue

            selected = funnel_r.sample(available_accounts, sources_per_funnel + 1)
            funnel_account = selected[-1]
            source_accounts = selected[:-1]

            all_accounts.extend(source_accounts)
            all_accounts.append(funnel_account)

            total_amount = 0
            for source_acc in source_accounts:
                amount = funnel_r.randint(10000, 100000)
                total_amount += amount

                edge = self._create_transfer_edge(
                    from_account=source_acc,
                    to_account=funnel_account,
                    amount=amount,
                    fraud_ring_id=f"FR-FUNNEL-{funnel_num:02d}",
                )
                all_edges.append(edge)
                registry.add_edge(edge)

            traversal_path = source_accounts + [funnel_account]

            ring = FraudRingBuilder.build_funnel_account(
                ring_id=f"FR-FUNNEL-{funnel_num:02d}",
                source_accounts=source_accounts,
                funnel_account=funnel_account,
                traversal_path=traversal_path,
                seed=funnel_seed,
            )
            registry.add_fraud_ring(ring)

        return TopologyResult(
            success=True,
            edges_created=all_edges,
            entities_involved=all_accounts,
            fraud_ring=None,
        )