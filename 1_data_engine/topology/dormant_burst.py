"""
Dormant Burst Injector - Inactive accounts suddenly activated together
"""
import random

from .base_topology import BaseTopologyInjector, TopologyResult
from ..schemas.entity_registry import EntityRegistry
from ..schemas.transaction import TransactionGenerator
from ..schemas.fraud_ring import FraudRingSchema, FraudRingBuilder, Severity, FraudRingType
from datetime import date


class DormantBurstInjector(BaseTopologyInjector):
    """
    Creates dormant burst: previously inactive accounts activated together.

    Example: A1, A2, A3 dormant for 6 months, then all activate same day
    """

    def inject(self, registry: EntityRegistry) -> TopologyResult:
        """Inject dormant burst topology"""
        account_ids = list(registry.accounts.keys())
        if len(account_ids) < 10:
            return TopologyResult(
                success=False,
                edges_created=[],
                entities_involved=[],
                error_message="Not enough accounts for dormant burst",
            )

        r = random.Random(self.seed)
        num_bursts = r.randint(2, 3)

        all_edges = []
        all_accounts = []
        tx_gen = TransactionGenerator(seed=self.seed)

        for burst_num in range(num_bursts):
            burst_seed = self.seed + burst_num * 1000
            burst_r = random.Random(burst_seed)

            account_count = burst_r.randint(5, 8)
            burst_accounts = burst_r.sample(account_ids, account_count)
            all_accounts.extend(burst_accounts)

            for i, from_acc in enumerate(burst_accounts):
                to_acc = burst_accounts[(i + 1) % len(burst_accounts)]
                amount = burst_r.randint(20000, 100000)

                tx = tx_gen.generate(
                    from_account=from_acc,
                    to_account=to_acc,
                    inject_fraud={"type": "burst"},
                )
                registry.add_transaction(tx)

                edge = self._create_transfer_edge(
                    from_account=from_acc,
                    to_account=to_acc,
                    amount=amount,
                    fraud_ring_id=f"FR-DORMANT-{burst_num:02d}",
                )
                all_edges.append(edge)
                registry.add_edge(edge)

            ring = FraudRingSchema(
                id=f"FR-DORMANT-{burst_num:02d}",
                ring_type=FraudRingType.DORMANT_BURST,
                severity=Severity.HIGH,
                name=f"Dormant Account Burst {burst_num}",
                description="Previously dormant accounts suddenly activated together",
                entities=burst_accounts,
                traversal_paths=[burst_accounts],
                key_entities=burst_accounts[:2],
                creation_seed=burst_seed,
                metadata={"dormant_days": 180, "burst_window_hours": 48},
            )
            registry.add_fraud_ring(ring)

        return TopologyResult(
            success=True,
            edges_created=all_edges,
            entities_involved=all_accounts,
            fraud_ring=None,
        )