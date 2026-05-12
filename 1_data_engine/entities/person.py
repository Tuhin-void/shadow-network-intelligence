"""
Person Entity - Person schema with PEP/sanctions/aliases
"""
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PersonEntity:
    """Person entity for AML intelligence generation"""

    id: str
    first_name: str
    last_name: str
    date_of_birth: date
    nationality: str
    tax_id: str

    # Contact
    email: Optional[str] = None
    phone: Optional[str] = None
    address_id: Optional[str] = None

    # Risk
    risk_score: float = 0.0
    risk_level: RiskLevel = RiskLevel.LOW
    is_pep: bool = False
    is_sanctioned: bool = False
    is_watched: bool = False
    is_mule: bool = False

    # Identity
    aliases: List[str] = field(default_factory=list)
    passport_number: Optional[str] = None
    ssn: Optional[str] = None

    # Relationships
    beneficial_owner_of: List[str] = field(default_factory=list)
    director_of: List[str] = field(default_factory=list)
    accounts: List[str] = field(default_factory=list)
    devices: List[str] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def entity_type(self) -> str:
        return "Person"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "entity_type": "Person",
            "name": self.name,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "date_of_birth": self.date_of_birth.isoformat(),
            "nationality": self.nationality,
            "tax_id": self.tax_id,
            "email": self.email,
            "phone": self.phone,
            "address_id": self.address_id,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level.value,
            "is_pep": self.is_pep,
            "is_sanctioned": self.is_sanctioned,
            "is_watched": self.is_watched,
            "is_mule": self.is_mule,
            "aliases": self.aliases,
            "passport_number": self.passport_number,
            "created_at": self.created_at.isoformat(),
        }

    def to_tigergraph(self) -> dict:
        return {
            "person_id": self.id,
            "name": self.name,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "dob": self.date_of_birth.isoformat(),
            "nationality": self.nationality,
            "risk_score": self.risk_score,
            "is_pep": int(self.is_pep),
            "is_sanctioned": int(self.is_sanctioned),
        }

    def to_chroma_doc(self) -> str:
        doc = f"Person: {self.name}. Nationality: {self.nationality}. "
        if self.is_pep:
            doc += "Politically Exposed Person. "
        if self.is_sanctioned:
            doc += "Sanctioned entity. "
        if self.aliases:
            doc += f"Also known as: {', '.join(self.aliases)}. "
        doc += f"Risk score: {self.risk_score}. "
        return doc