"""
Temporal Spike Injector - Rapid transfer bursts in short time window
"""
import random

from .base_topology import BaseTopologyInjector, TopologyResult
from ..schemas.entity_registry import EntityRegistry
from ..schemas.transaction import TransactionGenerator
from ..schemas.fraud_ring import FraudRingSchema, FraudRingBuilder, Severity, FraudRingType
from datetime import datetime, timedelta


class TemporalSpikeInjector(BaseTopologyInjector):
    """
    Creates temporal spike: rapid transactions within constrained time window.

    Example: 20 transfers within 2-hour window
    """

    def inject(self, registry: EntityRegistry) -> TopologyResult:
        """Inject temporal spike topology"""
        account_ids = list(registry.accounts.keys())
        if len(account_ids) < 6:
            return TopologyResult(
                success=False,
                edges_created=[],
                entities_involved=[],
                error_message="Not enough accounts for temporal spike",
            )

        r = random.Random(self.seed)
        num_spikes = r.randint(2, 3)

        all_edges = []
        all_accounts = []
        tx_gen = TransactionGenerator(seed=self.seed)

        for spike_num in range(num_spikes):
            spike_seed = self.seed + spike_num * 1000
            spike_r = random.Random(spike_seed)

            tx_count = spike_r.randint(10, 20)
            spike_accounts = spike_r.sample(account_ids, min(6, len(account_ids)))
            all_accounts.extend(spike_accounts)

            base_time = datetime.now() - timedelta(hours=spike_r.randint(1, 24))

            for i in range(tx_count):
                from_acc = spike_r.choice(spike_accounts)
                to_acc = spike_r.choice([a for a in spike_accounts if a != from_acc])
                amount = spike_r.randint(15000, 50000)

                tx_timestamp = base_time + timedelta(
                    hours=spike_r.randint(0, 2),
                    minutes=spike_r.randint(0, 59),
                )

                tx = tx_gen.generate(
                    from_account=from_acc,
                    to_account=to_acc,
                    inject_fraud={"type": "spike"},
                )
                tx.timestamp = tx_timestamp
                registry.add_transaction(tx)

                edge = self._create_transfer_edge(
                    from_account=from_acc,
                    to_account=to_acc,
                    amount=amount,
                    fraud_ring_id=f"FR-SPIKE-{spike_num:02d}",
                )
                all_edges.append(edge)
                registry.add_edge(edge)

            ring = FraudRingSchema(
                id=f"FR-SPIKE-{spike_num:02d}",
                ring_type=FraudRingType.TEMPORAL_SPIKE,
                severity=Severity.HIGH,
                name=f"Temporal Velocity Spike {spike_num}",
                description=f"{tx_count} transfers within 2-hour window",
                entities=spike_accounts,
                traversal_paths=[spike_accounts],
                key_entities=spike_accounts[:2],
                creation_seed=spike_seed,
                metadata={"transaction_count": tx_count, "time_window_hours": 2},
            )
            registry.add_fraud_ring(ring)

        return TopologyResult(
            success=True,
            edges_created=all_edges,
            entities_involved=all_accounts,
            fraud_ring=None,
        )