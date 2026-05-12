"""
Transaction Entity - Financial transaction schema
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum


class TransactionType(Enum):
    WIRE = "wire"
    ACH = "ach"
    CASH = "cash"
    CHECK = "check"
    CRYPTO = "crypto"
    INTERNATIONAL = "international"
    INTERNAL = "internal"


class TransactionStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FLAGGED = "flagged"
    BLOCKED = "blocked"
    RETURNED = "returned"


@dataclass
class TransactionEntity:
    """Transaction entity for AML intelligence generation"""

    id: str
    from_account: str
    to_account: str
    amount: float
    currency: str = "USD"
    transaction_type: TransactionType = TransactionType.WIRE
    timestamp: datetime = field(default_factory=datetime.now)

    # Status
    status: TransactionStatus = TransactionStatus.COMPLETED

    # Description
    description: Optional[str] = None
    reference: Optional[str] = None

    # Risk flags
    is_suspicious: bool = False
    is_structuring: bool = False
    is_smurfing: bool = False
    is_layering: bool = False
    is_placement: bool = False
    is_integration: bool = False

    # Fraud ring
    fraud_ring_id: Optional[str] = None
    risk_score: float = 0.0

    # Source
    device_id: Optional[str] = None
    location: Optional[str] = None

    # Related
    related_transactions: List[str] = field(default_factory=list)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def entity_type(self) -> str:
        return "Transaction"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "entity_type": "Transaction",
            "from_account": self.from_account,
            "to_account": self.to_account,
            "amount": self.amount,
            "currency": self.currency,
            "transaction_type": self.transaction_type.value,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "is_suspicious": self.is_suspicious,
            "is_structuring": self.is_structuring,
            "is_smurfing": self.is_smurfing,
            "is_layering": self.is_layering,
            "risk_score": self.risk_score,
            "fraud_ring_id": self.fraud_ring_id,
        }

    def to_tigergraph(self) -> dict:
        return {
            "transaction_id": self.id,
            "from_account": self.from_account,
            "to_account": self.to_account,
            "amount": self.amount,
            "transaction_type": self.transaction_type.value,
            "timestamp": self.timestamp.isoformat(),
            "is_suspicious": int(self.is_suspicious),
            "risk_score": self.risk_score,
        }