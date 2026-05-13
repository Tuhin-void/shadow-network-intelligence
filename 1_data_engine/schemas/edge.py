"""
Edge Schema - Graph edge definitions for relationships
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class RelationshipType(Enum):
    # Infrastructure
    OWNS = "owns"
    HAS_ACCOUNT = "has_account"
    TRANSFERRED_TO = "transferred_to"
    LOCATED_AT = "located_at"
    ASSOCIATED_WITH = "associated_with"
    USES_DEVICE = "uses_device"
    ACCESSED_FROM = "accessed_from"
    SENT_TRANSACTION = "sent_transaction"
    RECEIVED_TRANSACTION = "received_transaction"
    REGISTERED_AT = "registered_at"
    BENEFITS_FROM = "benefits_from"
    SHARES_DEVICE_WITH = "shares_device_with"
    SHARES_ADDRESS_WITH = "shares_address_with"
    CONTROLS = "controls"
    DIRECTOR_OF = "director_of"
    # Explicit ring membership (live schema)
    PERSON_MEMBER_OF_RING = "person_member_of_ring"
    COMPANY_MEMBER_OF_RING = "company_member_of_ring"
    ACCOUNT_MEMBER_OF_RING = "account_member_of_ring"
    TRANSACTION_MEMBER_OF_RING = "transaction_member_of_ring"
    DEVICE_CONNECTED_TO_RING = "device_connected_to_ring"
    ADDRESS_CONNECTED_TO_RING = "address_connected_to_ring"


ENTITY_TYPES = ["PERSON", "COMPANY", "ACCOUNT", "ADDRESS", "DEVICE"]


@dataclass
class EdgeSchema:
    """Graph edge schema representing relationships between entities"""

    id: str
    from_id: str
    from_type: str
    to_id: str
    to_type: str
    relationship: RelationshipType
    weight: float = 1.0
    confidence: float = 1.0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_fraud_related: bool = False
    fraud_ring_id: Optional[str] = None
    description: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "from_id": self.from_id,
            "from_type": self.from_type,
            "to_id": self.to_id,
            "to_type": self.to_type,
            "relationship": self.relationship.value,
            "weight": self.weight,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "is_fraud_related": self.is_fraud_related,
            "fraud_ring_id": self.fraud_ring_id,
            "description": self.description,
        }

    def to_tigergraph_row(self) -> dict:
        return {
            "from_id": self.from_id,
            "from_type": self.from_type,
            "to_id": self.to_id,
            "to_type": self.to_type,
            "relationship": self.relationship.value,
            "weight": self.weight,
            "timestamp": self.timestamp.isoformat(),
            "is_fraud_related": int(self.is_fraud_related),
        }

    def get_edge_key(self) -> str:
        """Unique edge identifier for deduplication"""
        return f"{self.from_id}|{self.relationship.value}|{self.to_id}"


class EdgeBuilder:
    """Builder for creating graph edges with validation"""

    COUNTER = 0

    @staticmethod
    def create(
        from_id: str,
        from_type: str,
        to_id: str,
        to_type: str,
        relationship: RelationshipType,
        is_fraud_related: bool = False,
        fraud_ring_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
        weight: float = 1.0,
    ) -> EdgeSchema:
        """Create a validated edge"""
        if from_type not in ENTITY_TYPES:
            raise ValueError(f"Invalid from_type: {from_type}")
        if to_type not in ENTITY_TYPES:
            raise ValueError(f"Invalid to_type: {to_type}")

        EdgeBuilder.COUNTER += 1

        edge = EdgeSchema(
            id=f"E-{EdgeBuilder.COUNTER:08d}",
            from_id=from_id,
            from_type=from_type,
            to_id=to_id,
            to_type=to_type,
            relationship=relationship,
            weight=weight,
            is_fraud_related=is_fraud_related,
            fraud_ring_id=fraud_ring_id,
            metadata=metadata or {},
        )

        return edge

    @staticmethod
    def person_owns_company(person_id: str, company_id: str, fraud_ring_id: Optional[str] = None) -> EdgeSchema:
        return EdgeBuilder.create(
            from_id=person_id,
            from_type="PERSON",
            to_id=company_id,
            to_type="COMPANY",
            relationship=RelationshipType.OWNS,
            is_fraud_related=fraud_ring_id is not None,
            fraud_ring_id=fraud_ring_id,
        )

    @staticmethod
    def company_owns_company(parent_id: str, child_id: str, fraud_ring_id: Optional[str] = None) -> EdgeSchema:
        return EdgeBuilder.create(
            from_id=parent_id,
            from_type="COMPANY",
            to_id=child_id,
            to_type="COMPANY",
            relationship=RelationshipType.OWNS,
            is_fraud_related=fraud_ring_id is not None,
            fraud_ring_id=fraud_ring_id,
        )

    @staticmethod
    def account_transfer(
        from_account: str,
        to_account: str,
        amount: float = 0,
        fraud_ring_id: Optional[str] = None,
    ) -> EdgeSchema:
        return EdgeBuilder.create(
            from_id=from_account,
            from_type="ACCOUNT",
            to_id=to_account,
            to_type="ACCOUNT",
            relationship=RelationshipType.TRANSFERRED_TO,
            metadata={"amount": amount},
            weight=1.0,
            is_fraud_related=fraud_ring_id is not None,
            fraud_ring_id=fraud_ring_id,
        )

    @staticmethod
    def entity_located_at(entity_id: str, entity_type: str, address_id: str) -> EdgeSchema:
        return EdgeBuilder.create(
            from_id=entity_id,
            from_type=entity_type,
            to_id=address_id,
            to_type="ADDRESS",
            relationship=RelationshipType.LOCATED_AT,
        )

    @staticmethod
    def owner_has_account(owner_id: str, owner_type: str, account_id: str) -> EdgeSchema:
        return EdgeBuilder.create(
            from_id=owner_id,
            from_type=owner_type,
            to_id=account_id,
            to_type="ACCOUNT",
            relationship=RelationshipType.HAS_ACCOUNT,
        )

    @staticmethod
    def person_controls_company(person_id: str, company_id: str, fraud_ring_id: Optional[str] = None) -> EdgeSchema:
        return EdgeBuilder.create(
            from_id=person_id,
            from_type="PERSON",
            to_id=company_id,
            to_type="COMPANY",
            relationship=RelationshipType.CONTROLS,
            is_fraud_related=fraud_ring_id is not None,
            fraud_ring_id=fraud_ring_id,
        )

    @staticmethod
    def company_benefits_from_company(source_id: str, target_id: str, fraud_ring_id: Optional[str] = None) -> EdgeSchema:
        return EdgeBuilder.create(
            from_id=source_id,
            from_type="COMPANY",
            to_id=target_id,
            to_type="COMPANY",
            relationship=RelationshipType.BENEFITS_FROM,
            is_fraud_related=fraud_ring_id is not None,
            fraud_ring_id=fraud_ring_id,
        )