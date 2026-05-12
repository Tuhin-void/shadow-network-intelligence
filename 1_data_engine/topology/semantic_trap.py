"""
Semantic Trap Injector - Similar entity names for Vector RAG confusion
"""
import random
from typing import List

from .base_topology import BaseTopologyInjector, TopologyResult
from ..schemas.entity_registry import EntityRegistry
from ..schemas.company import CompanySchema, CompanyGenerator, CompanyType
from ..schemas.fraud_ring import FraudRingSchema, FraudRingBuilder, Severity, FraudRingType


class SemanticTrapInjector(BaseTopologyInjector):
    """
    Creates semantic traps: similar company names to confuse vector similarity search.

    Example: 100 companies with "ShadowCorp" in name, only 1 is actual fraud member
    """

    VARIANT_PREFIXES = [
        "Shadow", "Midnight", "Sterling", "Phoenix", "Crimson", "Onyx", "Silver",
        "Golden", "Diamond", "Platinum", "Titanium", "Carbon", "Neon", "Cyber",
    ]

    SUFFIXES = [
        "Corp", "LLC", "Inc", "Holdings", "Group", "International", "Ventures",
    ]

    def inject(self, registry: EntityRegistry) -> TopologyResult:
        """Inject semantic trap topology"""
        r = random.Random(self.seed)

        num_traps = r.randint(1, 2)
        all_noise_companies = []
        all_edges = []

        for trap_num in range(num_traps):
            trap_seed = self.seed + trap_num * 1000
            trap_r = random.Random(trap_seed)

            base_name = trap_r.choice(self.VARIANT_PREFIXES)
            noise_count = 100

            trap_companies = []
            for i in range(noise_count):
                self._edge_counter += 1
                suffix = trap_r.choice(self.SUFFIXES)
                name = f"{base_name} {suffix}"

                company = CompanySchema(
                    id=f"C-TRAP-{trap_num}-{i:04d}",
                    name=name,
                    legal_name=name,
                    ein=f"{trap_r.randint(10, 99)}-{trap_r.randint(1000000, 9999999)}",
                    industry="Consulting",
                    company_type=CompanyType.DOMESTIC,
                    incorporation_date=__import__('datetime').date(2020, 1, 1),
                    risk_score=round(trap_r.uniform(0.1, 0.3), 4),
                )
                trap_companies.append(company)
                all_noise_companies.append(company)

            real_company_id = trap_r.choice(list(registry.companies.keys())[:100])

            ring = FraudRingBuilder.build_semantic_trap(
                ring_id=f"FR-TRAP-{trap_num:02d}",
                real_company_id=real_company_id,
                noise_company_ids=[c.id for c in trap_companies],
                seed=trap_seed,
            )
            registry.add_fraud_ring(ring)

        return TopologyResult(
            success=True,
            edges_created=all_edges,
            entities_involved=[c.id for c in all_noise_companies],
            fraud_ring=None,
        )