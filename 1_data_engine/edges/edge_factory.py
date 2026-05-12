"""
Edge Factory - Factory for creating graph edges
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum


class EdgeType(Enum):
    OWNS = "OWNS"
    HAS_ACCOUNT = "HAS_ACCOUNT"
    TRANSFERRED_TO = "TRANSFERRED_TO"
    LOCATED_AT = "LOCATED_AT"
    ASSOCIATED_WITH = "ASSOCIATED_WITH"
    USES_DEVICE = "USES_DEVICE"
    ACCESSED_FROM = "ACCESSED_FROM"
    SENT_TRANSACTION = "SENT_TRANSACTION"
    RECEIVED_TRANSACTION = "RECEIVED_TRANSACTION"
    REGISTERED_AT = "REGISTERED_AT"
    BENEFITS_FROM = "BENEFITS_FROM"
    SHARES_DEVICE_WITH = "SHARES_DEVICE_WITH"
    SHARES_ADDRESS_WITH = "SHARES_ADDRESS_WITH"
    CONTROLS = "CONTROLS"
    DIRECTOR_OF = "DIRECTOR_OF"


RELATIONSHIP_WEIGHTS = {
    EdgeType.OWNS: 1.0,
    EdgeType.HAS_ACCOUNT: 0.7,
    EdgeType.TRANSFERRED_TO: 0.8,
    EdgeType.LOCATED_AT: 0.4,
    EdgeType.ASSOCIATED_WITH: 0.5,
    EdgeType.USES_DEVICE: 0.6,
    EdgeType.ACCESSED_FROM: 0.5,
    EdgeType.SENT_TRANSACTION: 0.9,
    EdgeType.RECEIVED_TRANSACTION: 0.9,
    EdgeType.REGISTERED_AT: 0.5,
    EdgeType.BENEFITS_FROM: 0.8,
    EdgeType.SHARES_DEVICE_WITH: 0.6,
    EdgeType.SHARES_ADDRESS_WITH: 0.7,
    EdgeType.CONTROLS: 0.9,
    EdgeType.DIRECTOR_OF: 0.8,
}


@dataclass
class GraphEdge:
    """Graph edge representation"""

    id: str
    from_id: str
    from_type: str
    to_id: str
    to_type: str
    relationship: str

    weight: float = 1.0
    timestamp: datetime = field(default_factory=datetime.now)

    is_fraud_related: bool = False
    fraud_ring_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "from_id": self.from_id,
            "from_type": self.from_type,
            "to_id": self.to_id,
            "to_type": self.to_type,
            "relationship": self.relationship,
            "weight": self.weight,
            "timestamp": self.timestamp.isoformat(),
            "is_fraud_related": self.is_fraud_related,
            "fraud_ring_id": self.fraud_ring_id,
        }

    def to_tigergraph(self) -> dict:
        return {
            "from_id": self.from_id,
            "from_type": self.from_type,
            "to_id": self.to_id,
            "to_type": self.to_type,
            "relationship": self.relationship,
            "weight": self.weight,
            "timestamp": self.timestamp.isoformat(),
            "is_fraud_related": int(self.is_fraud_related),
        }


class EdgeFactory:
    """Factory for creating graph edges"""

    _edge_counter = 0

    @classmethod
    def create(
        cls,
        from_id: str,
        from_type: str,
        to_id: str,
        to_type: str,
        relationship: str,
        weight: float = 1.0,
        is_fraud: bool = False,
        fraud_ring_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> GraphEdge:
        """Create a new edge"""
        cls._edge_counter += 1
        return GraphEdge(
            id=f"E-{cls._edge_counter:08d}",
            from_id=from_id,
            from_type=from_type,
            to_id=to_id,
            to_type=to_type,
            relationship=relationship,
            weight=weight,
            is_fraud_related=is_fraud,
            fraud_ring_id=fraud_ring_id,
            metadata=metadata or {},
        )

    @classmethod
    def owns(cls, person_id: str, company_id: str, fraud_ring_id: Optional[str] = None) -> GraphEdge:
        return cls.create(
            from_id=person_id,
            from_type="Person",
            to_id=company_id,
            to_type="Company",
            relationship="OWNS",
            weight=RELATIONSHIP_WEIGHTS[EdgeType.OWNS],
            is_fraud=fraud_ring_id is not None,
            fraud_ring_id=fraud_ring_id,
        )

    @classmethod
    def company_owns_company(cls, parent_id: str, child_id: str, fraud_ring_id: Optional[str] = None) -> GraphEdge:
        return cls.create(
            from_id=parent_id,
            from_type="Company",
            to_id=child_id,
            to_type="Company",
            relationship="OWNS",
            weight=RELATIONSHIP_WEIGHTS[EdgeType.OWNS],
            is_fraud=fraud_ring_id is not None,
            fraud_ring_id=fraud_ring_id,
        )

    @classmethod
    def has_account(cls, owner_id: str, owner_type: str, account_id: str) -> GraphEdge:
        return cls.create(
            from_id=owner_id,
            from_type=owner_type,
            to_id=account_id,
            to_type="Account",
            relationship="HAS_ACCOUNT",
            weight=RELATIONSHIP_WEIGHTS[EdgeType.HAS_ACCOUNT],
        )

    @classmethod
    def transferred_to(
        cls,
        from_account: str,
        to_account: str,
        amount: float = 0,
        fraud_ring_id: Optional[str] = None,
    ) -> GraphEdge:
        return cls.create(
            from_id=from_account,
            from_type="Account",
            to_id=to_account,
            to_type="Account",
            relationship="TRANSFERRED_TO",
            weight=RELATIONSHIP_WEIGHTS[EdgeType.TRANSFERRED_TO],
            is_fraud=fraud_ring_id is not None,
            fraud_ring_id=fraud_ring_id,
            metadata={"amount": amount} if amount else {},
        )

    @classmethod
    def located_at(cls, entity_id: str, entity_type: str, address_id: str) -> GraphEdge:
        return cls.create(
            from_id=entity_id,
            from_type=entity_type,
            to_id=address_id,
            to_type="Address",
            relationship="LOCATED_AT",
            weight=RELATIONSHIP_WEIGHTS[EdgeType.LOCATED_AT],
        )

    @classmethod
    def uses_device(cls, person_id: str, device_id: str) -> GraphEdge:
        return cls.create(
            from_id=person_id,
            from_type="Person",
            to_id=device_id,
            to_type="Device",
            relationship="USES_DEVICE",
            weight=RELATIONSHIP_WEIGHTS[EdgeType.USES_DEVICE],
        )

    @classmethod
    def accessed_from(cls, account_id: str, device_id: str) -> GraphEdge:
        return cls.create(
            from_id=account_id,
            from_type="Account",
            to_id=device_id,
            to_type="Device",
            relationship="ACCESSED_FROM",
            weight=RELATIONSHIP_WEIGHTS[EdgeType.ACCESSED_FROM],
        )

    @classmethod
    def associated_with(cls, entity1_id: str, entity1_type: str, entity2_id: str, entity2_type: str) -> GraphEdge:
        return cls.create(
            from_id=entity1_id,
            from_type=entity1_type,
            to_id=entity2_id,
            to_type=entity2_type,
            relationship="ASSOCIATED_WITH",
            weight=RELATIONSHIP_WEIGHTS[EdgeType.ASSOCIATED_WITH],
        )

    @classmethod
    def shares_device_with(cls, person1_id: str, person2_id: str) -> GraphEdge:
        return cls.create(
            from_id=person1_id,
            from_type="Person",
            to_id=person2_id,
            to_type="Person",
            relationship="SHARES_DEVICE_WITH",
            weight=RELATIONSHIP_WEIGHTS[EdgeType.SHARES_DEVICE_WITH],
        )

    @classmethod
    def shares_address_with(cls, entity1_id: str, entity1_type: str, entity2_id: str) -> GraphEdge:
        return cls.create(
            from_id=entity1_id,
            from_type=entity1_type,
            to_id=entity2_id,
            to_type="Address",
            relationship="SHARES_ADDRESS_WITH",
            weight=RELATIONSHIP_WEIGHTS[EdgeType.SHARES_ADDRESS_WITH],
        )

    @classmethod
    def controls(cls, person_id: str, company_id: str, fraud_ring_id: Optional[str] = None) -> GraphEdge:
        return cls.create(
            from_id=person_id,
            from_type="Person",
            to_id=company_id,
            to_type="Company",
            relationship="CONTROLS",
            weight=RELATIONSHIP_WEIGHTS[EdgeType.CONTROLS],
            is_fraud=fraud_ring_id is not None,
            fraud_ring_id=fraud_ring_id,
        )

    @classmethod
    def director_of(cls, person_id: str, company_id: str) -> GraphEdge:
        return cls.create(
            from_id=person_id,
            from_type="Person",
            to_id=company_id,
            to_type="Company",
            relationship="DIRECTOR_OF",
            weight=RELATIONSHIP_WEIGHTS[EdgeType.DIRECTOR_OF],
        )

    @classmethod
    def benefits_from(cls, source_id: str, target_id: str, fraud_ring_id: Optional[str] = None) -> GraphEdge:
        return cls.create(
            from_id=source_id,
            from_type="Company",
            to_id=target_id,
            to_type="Company",
            relationship="BENEFITS_FROM",
            weight=RELATIONSHIP_WEIGHTS[EdgeType.BENEFITS_FROM],
            is_fraud=fraud_ring_id is not None,
            fraud_ring_id=fraud_ring_id,
        )