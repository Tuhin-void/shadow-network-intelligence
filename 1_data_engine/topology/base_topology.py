"""
Base Topology Injector - Abstract base class for fraud topology injection
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from ..schemas.entity_registry import EntityRegistry
from ..schemas.edge import EdgeSchema, EdgeBuilder, RelationshipType
from ..schemas.fraud_ring import FraudRingSchema, FraudRingBuilder


@dataclass
class TopologyResult:
    """Result of topology injection operation"""

    success: bool
    edges_created: List[EdgeSchema]
    entities_involved: List[str]
    fraud_ring: Optional[FraudRingSchema] = None
    error_message: Optional[str] = None


class BaseTopologyInjector(ABC):
    """
    Abstract base class for fraud topology injectors.

    Each injector implements a specific fraud pattern:
    - Circular ownership rings
    - Funnel accounts
    - Smurfing patterns
    - Laundering chains
    - etc.
    """

    def __init__(self, seed: int = 42):
        self.seed = seed
        self._edge_counter = 0

    @abstractmethod
    def inject(self, registry: EntityRegistry) -> TopologyResult:
        """
        Inject the fraud topology into the entity registry.

        Args:
            registry: Entity registry containing all generated entities

        Returns:
            TopologyResult with created edges and metadata
        """
        pass

    def _create_edge(
        self,
        from_id: str,
        from_type: str,
        to_id: str,
        to_type: str,
        relationship: RelationshipType,
        is_fraud: bool = True,
        fraud_ring_id: Optional[str] = None,
    ) -> EdgeSchema:
        """Helper to create edges with consistent formatting"""
        edge = EdgeBuilder.create(
            from_id=from_id,
            from_type=from_type,
            to_id=to_id,
            to_type=to_type,
            relationship=relationship,
            is_fraud_related=is_fraud,
            fraud_ring_id=fraud_ring_id,
        )
        self._edge_counter += 1
        return edge

    def _create_transfer_edge(
        self,
        from_account: str,
        to_account: str,
        amount: float = 0,
        fraud_ring_id: Optional[str] = None,
    ) -> EdgeSchema:
        """Helper to create transfer edges between accounts"""
        return EdgeBuilder.account_transfer(
            from_account,
            to_account,
            amount=amount,
            fraud_ring_id=fraud_ring_id,
        )

    def get_random_entities(
        self,
        registry: EntityRegistry,
        entity_type: str,
        count: int,
        exclude: Optional[List[str]] = None,
    ) -> List[str]:
        """Get random entity IDs of specified type"""
        if entity_type == "COMPANY":
            pool = list(registry.companies.keys())
        elif entity_type == "PERSON":
            pool = list(registry.persons.keys())
        elif entity_type == "ACCOUNT":
            pool = list(registry.accounts.keys())
        else:
            pool = []

        if exclude:
            pool = [e for e in pool if e not in exclude]

        import random
        r = random.Random(self.seed)
        return r.sample(pool, min(count, len(pool)))