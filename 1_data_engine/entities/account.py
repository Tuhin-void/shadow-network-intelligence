"""
Account Entity - Bank and crypto account schema
"""
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum


class AccountType(Enum):
    CHECKING = "checking"
    SAVINGS = "savings"
    BUSINESS = "business"
    TRUST = "trust"
    CRYPTO_WALLET = "crypto_wallet"
    OFFSHORE = "offshore"
    CORRESPONDENT = "correspondent"


class AccountStatus(Enum):
    ACTIVE = "active"
    DORMANT = "dormant"
    SUSPENDED = "suspended"
    CLOSED = "closed"


@dataclass
class AccountEntity:
    """Account entity for AML intelligence generation"""

    id: str
    account_number: str
    account_type: AccountType = AccountType.CHECKING
    owner_id: str = ""
    owner_type: str = "Person"

    # Banking
    routing_number: Optional[str] = None
    swift_code: Optional[str] = None
    iban: Optional[str] = None
    wallet_address: Optional[str] = None

    # Financial
    balance: float = 0.0
    currency: str = "USD"
    opened_date: date = field(default_factory=date.today)

    # Status
    status: AccountStatus = AccountStatus.ACTIVE
    last_activity_date: Optional[date] = None

    # Risk
    risk_score: float = 0.0
    velocity_score: float = 0.0
    avg_transaction_size: float = 0.0
    transaction_count: int = 0
    is_correspondent: bool = False
    is_mule: bool = False

    # Transactions
    sent_transactions: List[str] = field(default_factory=list)
    received_transactions: List[str] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def entity_type(self) -> str:
        return "Account"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "entity_type": "Account",
            "account_number": self.account_number[-4:] if self.account_number else "",
            "account_type": self.account_type.value,
            "owner_id": self.owner_id,
            "owner_type": self.owner_type,
            "balance": self.balance,
            "currency": self.currency,
            "status": self.status.value,
            "risk_score": self.risk_score,
            "velocity_score": self.velocity_score,
            "is_correspondent": self.is_correspondent,
            "created_at": self.created_at.isoformat(),
        }

    def to_tigergraph(self) -> dict:
        return {
            "account_id": self.id,
            "account_number": self.account_number[-4:] if self.account_number else "",
            "account_type": self.account_type.value,
            "owner_id": self.owner_id,
            "balance": self.balance,
            "currency": self.currency,
            "status": self.status.value,
            "risk_score": self.risk_score,
            "velocity_score": self.velocity_score,
        }