"""
Address Entity - Address schema with collision tracking
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum


class AddressType(Enum):
    RESIDENTIAL = "residential"
    BUSINESS = "business"
    MAILING = "mailing"
    REGISTERED = "registered"
    SHELL_ADDRESS = "shell_address"
    MAILBOX = "mailbox"


@dataclass
class AddressEntity:
    """Address entity for AML intelligence generation"""

    id: str
    street_address: str
    city: str
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: str = "US"
    address_type: AddressType = AddressType.RESIDENTIAL

    # Risk
    is_shell_location: bool = False
    is_known_fraud_hub: bool = False
    entity_count: int = 0
    risk_score: float = 0.0

    # Entities at this address
    persons: List[str] = field(default_factory=list)
    companies: List[str] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def entity_type(self) -> str:
        return "Address"

    def get_full_address(self) -> str:
        parts = [self.street_address, self.city]
        if self.state:
            parts.append(self.state)
        if self.postal_code:
            parts.append(self.postal_code)
        parts.append(self.country)
        return ", ".join(parts)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "entity_type": "Address",
            "street_address": self.street_address,
            "city": self.city,
            "state": self.state,
            "postal_code": self.postal_code,
            "country": self.country,
            "address_type": self.address_type.value,
            "is_shell_location": self.is_shell_location,
            "is_known_fraud_hub": self.is_known_fraud_hub,
            "entity_count": self.entity_count,
            "risk_score": self.risk_score,
        }

    def to_tigergraph(self) -> dict:
        return {
            "address_id": self.id,
            "street_address": self.street_address,
            "city": self.city,
            "state": self.state or "",
            "country": self.country,
            "is_shell_location": int(self.is_shell_location),
            "entity_count": self.entity_count,
        }