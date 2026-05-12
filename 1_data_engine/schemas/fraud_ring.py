"""
Fraud Ring Schema - Fraud ring metadata and definitions
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class FraudRingType(Enum):
    CIRCULAR_OWNERSHIP = "circular_ownership"
    FUNNEL_ACCOUNT = "funnel_account"
    SMURFING_RING = "smurfing_ring"
    LAYERING_CHAIN = "layering_chain"
    SHARED_ADDRESS = "shared_address"
    OFFSHORE_ROUTING = "offshore_routing"
    CENTRAL_HUB = "central_hub"
    DORMANT_BURST = "dormant_burst"
    BENEFICIAL_OWNERSHIP = "beneficial_ownership"
    SEMANTIC_TRAP = "semantic_trap"
    HYBRID_NETWORK = "hybrid_network"
    TEMPORAL_SPIKE = "temporal_spike"


class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class FraudRingSchema:
    """Fraud ring metadata with ground truth"""

    id: str
    ring_type: FraudRingType
    severity: Severity
    name: str
    description: str
    entities: List[str] = field(default_factory=list)
    edges: List[str] = field(default_factory=list)
    traversal_paths: List[List[str]] = field(default_factory=list)
    key_entities: List[str] = field(default_factory=list)
    expected_questions: List[str] = field(default_factory=list)
    expected_graph_paths: List[str] = field(default_factory=list)
    creation_seed: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "ring_type": self.ring_type.value,
            "severity": self.severity.value,
            "name": self.name,
            "description": self.description,
            "entities": self.entities,
            "edges": self.edges,
            "traversal_paths": self.traversal_paths,
            "key_entities": self.key_entities,
            "expected_questions": self.expected_questions,
            "expected_graph_paths": self.expected_graph_paths,
            "creation_seed": self.creation_seed,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    def get_entity_count(self) -> int:
        return len(self.entities)

    def get_edge_count(self) -> int:
        return len(self.edges)

    def get_max_hop(self) -> int:
        if not self.traversal_paths:
            return 0
        return max(len(path) - 1 for path in self.traversal_paths)


@dataclass
class FraudRingBuilder:
    """Builder for creating fraud ring metadata"""

    @staticmethod
    def build_circular_ownership(
        ring_id: str,
        companies: List[str],
        traversal_paths: List[List[str]],
        seed: int,
    ) -> FraudRingSchema:
        return FraudRingSchema(
            id=ring_id,
            ring_type=FraudRingType.CIRCULAR_OWNERSHIP,
            severity=Severity.CRITICAL,
            name=f"Circular Ownership Ring {ring_id}",
            description="Shell companies with circular ownership structure for fund obscuration",
            entities=companies,
            traversal_paths=traversal_paths,
            key_entities=companies[:3] if len(companies) >= 3 else companies,
            expected_questions=[
                "Find all companies in circular ownership with this entity",
                "Identify the ownership loop starting from company X",
            ],
            expected_graph_paths=[f"{c1}->OWNS->{c2}" for c1, c2 in zip(companies, companies[1:] + [companies[0]])],
            creation_seed=seed,
        )

    @staticmethod
    def build_funnel_account(
        ring_id: str,
        source_accounts: List[str],
        funnel_account: str,
        traversal_path: List[str],
        seed: int,
    ) -> FraudRingSchema:
        return FraudRingSchema(
            id=ring_id,
            ring_type=FraudRingType.FUNNEL_ACCOUNT,
            severity=Severity.HIGH,
            name=f"Funnel Account Network {ring_id}",
            description="Multiple source accounts funneling funds to single laundering account",
            entities=source_accounts + [funnel_account],
            traversal_paths=[traversal_path],
            key_entities=[funnel_account],
            expected_questions=[
                f"Find accounts that funnel funds to {funnel_account}",
                "Identify transaction funnels with high concentration",
            ],
            expected_graph_paths=[f"{acc}->TRANSFERRED_TO->{funnel_account}" for acc in source_accounts],
            creation_seed=seed,
        )

    @staticmethod
    def build_laundering_chain(
        ring_id: str,
        chain: List[str],
        seed: int,
    ) -> FraudRingSchema:
        return FraudRingSchema(
            id=ring_id,
            ring_type=FraudRingType.LAYERING_CHAIN,
            severity=Severity.CRITICAL,
            name=f"Laundering Chain {ring_id}",
            description="Multi-hop transaction chain for money laundering",
            entities=chain,
            traversal_paths=[chain],
            key_entities=chain[0],  # Entry point
            expected_questions=[
                f"Trace the laundering path from {chain[0]}",
                "Find all downstream accounts from this entry point",
            ],
            expected_graph_paths=[f"{chain[i]}->TRANSFERRED_TO->{chain[i+1]}" for i in range(len(chain)-1)],
            creation_seed=seed,
        )

    @staticmethod
    def build_address_collision(
        ring_id: str,
        address_id: str,
        entities: List[str],
        seed: int,
    ) -> FraudRingSchema:
        return FraudRingSchema(
            id=ring_id,
            ring_type=FraudRingType.SHARED_ADDRESS,
            severity=Severity.HIGH,
            name=f"Address Collision Cluster {ring_id}",
            description="Multiple entities sharing same address for fraud concealment",
            entities=entities,
            key_entities=[address_id],
            expected_questions=[
                f"Find all entities located at {address_id}",
                "Identify address collision clusters",
            ],
            expected_graph_paths=[f"{e}->LOCATED_AT->{address_id}" for e in entities],
            creation_seed=seed,
        )

    @staticmethod
    def build_semantic_trap(
        ring_id: str,
        real_company_id: str,
        noise_company_ids: List[str],
        seed: int,
    ) -> FraudRingSchema:
        all_entities = [real_company_id] + noise_company_ids
        return FraudRingSchema(
            id=ring_id,
            ring_type=FraudRingType.SEMANTIC_TRAP,
            severity=Severity.MEDIUM,
            name=f"Semantic Ambiguity Trap {ring_id}",
            description="Similar company names designed to confuse vector retrieval",
            entities=all_entities,
            key_entities=[real_company_id],
            expected_questions=[
                "Which company is the actual member of this fraud ring?",
                "Distinguish the real entity from similarly named noise",
            ],
            expected_graph_paths=[],
            creation_seed=seed,
            metadata={
                "real_entity": real_company_id,
                "noise_entities": noise_company_ids,
                "trap_type": "name_ambiguity",
            },
        )