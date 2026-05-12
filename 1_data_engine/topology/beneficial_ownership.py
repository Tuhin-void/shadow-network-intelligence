"""
Beneficial Ownership Injector - Hidden indirect control chains
"""
import random

from .base_topology import BaseTopologyInjector, TopologyResult
from ..schemas.entity_registry import EntityRegistry
from ..schemas.edge import RelationshipType
from ..schemas.fraud_ring import FraudRingSchema, FraudRingBuilder, Severity, FraudRingType


class BeneficialOwnershipInjector(BaseTopologyInjector):
    """
    Creates hidden control chains: deep beneficial ownership obfuscation.

    Example: P1 -> C1 -> C2 -> C3 (P1 ultimately controls C3)
    """

    def inject(self, registry: EntityRegistry) -> TopologyResult:
        """Inject beneficial ownership topology"""
        person_ids = list(registry.persons.keys())
        company_ids = list(registry.companies.keys())

        if len(person_ids) < 3 or len(company_ids) < 6:
            return TopologyResult(
                success=False,
                edges_created=[],
                entities_involved=[],
                error_message="Not enough entities for beneficial ownership",
            )

        r = random.Random(self.seed)
        num_chains = r.randint(2, 3)

        all_edges = []
        all_entities = []

        for chain_num in range(num_chains):
            chain_seed = self.seed + chain_num * 1000
            chain_r = random.Random(chain_seed)

            chain_length = chain_r.randint(3, 5)
            beneficial_owner = chain_r.choice(person_ids)

            available_companies = [c for c in company_ids if c not in all_entities]
            if len(available_companies) < chain_length:
                continue

            company_chain = chain_r.sample(available_companies, chain_length)
            all_entities.append(beneficial_owner)
            all_entities.extend(company_chain)

            edge = self._create_edge(
                from_id=beneficial_owner,
                from_type="PERSON",
                to_id=company_chain[0],
                to_type="COMPANY",
                relationship=RelationshipType.BENEFICIAL_OWNER_OF,
                fraud_ring_id=f"FR-BENEF-{chain_num:02d}",
            )
            all_edges.append(edge)
            registry.add_edge(edge)

            for i in range(len(company_chain) - 1):
                edge = self._create_edge(
                    from_id=company_chain[i],
                    from_type="COMPANY",
                    to_id=company_chain[i + 1],
                    to_type="COMPANY",
                    relationship=RelationshipType.OWNS,
                    fraud_ring_id=f"FR-BENEF-{chain_num:02d}",
                )
                all_edges.append(edge)
                registry.add_edge(edge)

            traversal_path = [beneficial_owner] + company_chain

            ring = FraudRingSchema(
                id=f"FR-BENEF-{chain_num:02d}",
                ring_type=FraudRingType.BENEFICIAL_OWNERSHIP,
                severity=Severity.HIGH,
                name=f"Beneficial Ownership Chain {chain_num}",
                description=f"Hidden control chain with {chain_length} intermediate companies",
                entities=traversal_path,
                traversal_paths=[traversal_path],
                key_entities=[beneficial_owner],
                expected_questions=[
                    f"Find ultimate beneficial owners of {company_chain[-1]}",
                    f"Trace control chain from {beneficial_owner}",
                ],
                creation_seed=chain_seed,
            )
            registry.add_fraud_ring(ring)

        return TopologyResult(
            success=True,
            edges_created=all_edges,
            entities_involved=all_entities,
            fraud_ring=None,
        )