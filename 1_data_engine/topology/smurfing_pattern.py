"""
Smurfing Pattern Injector - Structuring/smurfing below CTR threshold
"""
import random

from .base_topology import BaseTopologyInjector, TopologyResult
from ..schemas.entity_registry import EntityRegistry
from ..schemas.transaction import TransactionSchema, TransactionGenerator
from ..schemas.fraud_ring import FraudRingSchema, FraudRingBuilder, Severity, FraudRingType


class SmurfingInjector(BaseTopologyInjector):
    """
    Creates smurfing patterns: multiple sub-10K transactions to avoid CTR.

    Example: Multiple $9,500 transfers from different accounts to one destination
    """

    def inject(self, registry: EntityRegistry) -> TopologyResult:
        """Inject smurfing pattern topology"""
        account_ids = list(registry.accounts.keys())
        if len(account_ids) < 6:
            return TopologyResult(
                success=False,
                edges_created=[],
                entities_involved=[],
                error_message="Not enough accounts for smurfing",
            )

        r = random.Random(self.seed)
        num_smurfing = r.randint(2, 3)

        all_edges = []
        all_accounts = []
        tx_gen = TransactionGenerator(seed=self.seed)

        for smurf_num in range(num_smurfing):
            sources = r.randint(5, 10)
            smurf_seed = self.seed + smurf_num * 1000
            smurf_r = random.Random(smurf_seed)

            available = [a for a in account_ids if a not in all_accounts]
            if len(available) < sources + 1:
                continue

            selected = smurf_r.sample(available, sources + 1)
            destination = selected[-1]
            source_accounts = selected[:-1]

            all_accounts.extend(source_accounts)
            all_accounts.append(destination)

            for source_acc in source_accounts:
                amount = smurf_r.randint(8000, 9800)

                tx = tx_gen.generate(
                    from_account=source_acc,
                    to_account=destination,
                    inject_fraud={"type": "smurfing", "amount": float(amount)},
                )
                registry.add_transaction(tx)

                edge = self._create_transfer_edge(
                    from_account=source_acc,
                    to_account=destination,
                    amount=amount,
                    fraud_ring_id=f"FR-SMURF-{smurf_num:02d}",
                )
                all_edges.append(edge)
                registry.add_edge(edge)

            ring = FraudRingSchema(
                id=f"FR-SMURF-{smurf_num:02d}",
                ring_type=FraudRingType.SMURFING_RING,
                severity=Severity.HIGH,
                name=f"Smurfing Ring {smurf_num}",
                description="Multiple sub-10K transactions to avoid CTR reporting",
                entities=source_accounts + [destination],
                traversal_paths=[source_accounts + [destination]],
                key_entities=[destination],
                creation_seed=smurf_seed,
            )
            registry.add_fraud_ring(ring)

        return TopologyResult(
            success=True,
            edges_created=all_edges,
            entities_involved=all_accounts,
            fraud_ring=None,
        )