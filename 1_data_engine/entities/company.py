"""
Company Entity - Company schema with shell/offshore structures
"""
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum


class CompanyType(Enum):
    DOMESTIC = "domestic"
    OFFSHORE = "offshore"
    SHELL = "shell"
    HOLDING = "holding"
    SUBSIDIARY = "subsidiary"
    TRUST = "trust"


@dataclass
class CompanyEntity:
    """Company entity for AML intelligence generation"""

    id: str
    name: str
    legal_name: str
    ein: str
    industry: str
    company_type: CompanyType = CompanyType.DOMESTIC

    # Geography
    address_id: Optional[str] = None
    registration_country: str = "US"
    incorporation_jurisdiction: str = "US"

    # Status
    incorporation_date: date = field(default_factory=date.today)
    dissolution_date: Optional[date] = None
    is_offshore: bool = False
    is_shell: bool = False
    is_dormant: bool = False

    # Financial
    annual_revenue: Optional[int] = None
    employee_count: int = 1

    # Risk
    risk_score: float = 0.0

    # Ownership
    beneficial_owners: List[str] = field(default_factory=list)
    directors: List[str] = field(default_factory=list)
    parent_company: Optional[str] = None
    subsidiaries: List[str] = field(default_factory=list)

    # Accounts
    accounts: List[str] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def entity_type(self) -> str:
        return "Company"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "entity_type": "Company",
            "name": self.name,
            "legal_name": self.legal_name,
            "ein": self.ein,
            "industry": self.industry,
            "company_type": self.company_type.value,
            "incorporation_date": self.incorporation_date.isoformat(),
            "registration_country": self.registration_country,
            "incorporation_jurisdiction": self.incorporation_jurisdiction,
            "is_offshore": self.is_offshore,
            "is_shell": self.is_shell,
            "is_dormant": self.is_dormant,
            "annual_revenue": self.annual_revenue,
            "employee_count": self.employee_count,
            "risk_score": self.risk_score,
            "beneficial_owners": self.beneficial_owners,
            "created_at": self.created_at.isoformat(),
        }

    def to_tigergraph(self) -> dict:
        return {
            "company_id": self.id,
            "name": self.name,
            "ein": self.ein,
            "industry": self.industry,
            "company_type": self.company_type.value,
            "incorporation_date": self.incorporation_date.isoformat(),
            "is_offshore": int(self.is_offshore),
            "is_shell": int(self.is_shell),
            "risk_score": self.risk_score,
        }

    def to_chroma_doc(self) -> str:
        doc = f"Company: {self.name}. Industry: {self.industry}. "
        if self.is_offshore:
            doc += f"Offshore entity in {self.incorporation_jurisdiction}. "
        if self.is_shell:
            doc += "Shell company. "
        if self.beneficial_owners:
            doc += f"Beneficial owners: {', '.join(self.beneficial_owners)}. "
        doc += f"Risk score: {self.risk_score}. "
        return doc