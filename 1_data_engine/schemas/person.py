"""
Person Schema - Person entity with PEP/sanctions/aliases
"""
import random
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List
from enum import Enum


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PersonSchema:
    """Person entity schema for AML data generation"""

    id: str
    name: str
    first_name: str
    last_name: str
    date_of_birth: date
    nationality: str
    tax_id: str
    passport_number: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address_id: Optional[str] = None
    risk_score: float = 0.0
    risk_level: RiskLevel = RiskLevel.LOW
    is_pep: bool = False
    is_sanctioned: bool = False
    is_watched: bool = False
    aliases: List[str] = field(default_factory=list)
    beneficial_owner_of: List[str] = field(default_factory=list)
    director_of: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "date_of_birth": self.date_of_birth.isoformat(),
            "nationality": self.nationality,
            "tax_id": self.tax_id,
            "passport_number": self.passport_number,
            "phone": self.phone,
            "email": self.email,
            "address_id": self.address_id,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level.value,
            "is_pep": self.is_pep,
            "is_sanctioned": self.is_sanctioned,
            "is_watched": self.is_watched,
            "aliases": self.aliases,
            "beneficial_owner_of": self.beneficial_owner_of,
            "director_of": self.director_of,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def to_tigergraph_row(self) -> dict:
        return {
            "person_id": self.id,
            "name": self.name,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "dob": self.date_of_birth.isoformat(),
            "nationality": self.nationality,
            "tax_id": self.tax_id,
            "risk_score": self.risk_score,
            "is_pep": int(self.is_pep),
            "is_sanctioned": int(self.is_sanctioned),
        }

    def to_chromadb_doc(self) -> str:
        doc = f"Person: {self.name}. "
        doc += f"Nationality: {self.nationality}. "
        if self.is_pep:
            doc += "Politically Exposed Person. "
        if self.is_sanctioned:
            doc += "Sanctioned entity. "
        if self.aliases:
            doc += f"Also known as: {', '.join(self.aliases)}. "
        doc += f"Risk score: {self.risk_score}. "
        if self.beneficial_owner_of:
            doc += f"Beneficial owner of companies: {', '.join(self.beneficial_owner_of)}. "
        return doc


class PersonGenerator:
    """Generator for person entities with realistic AML attributes"""

    FIRST_NAMES = [
        "James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph",
        "Thomas", "Charles", "Mary", "Patricia", "Jennifer", "Linda", "Barbara", "Susan",
        "Jessica", "Sarah", "Karen", "Nancy", "Lisa", "Margaret", "Betty", "Sandra",
        "Elena", "Viktor", "Dmitri", "Alexei", "Ivan", "Chen", "Wei", "Yuki", "Hiroshi",
        "Raj", "Priya", "Amit", "Fatima", "Mohammed", "Ali", "Oleg", "Katarina"
    ]

    LAST_NAMES = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
        "Rodriguez", "Martinez", "Anderson", "Taylor", "Thomas", "Moore", "Jackson", "Martin",
        "Petrov", "Ivanov", "Smirnov", "Kuznetsov", "Wang", "Li", "Zhang", "Singh",
        "Kumar", "Patel", "Al-Hassan", "Abbas", "Novak", " Mueller", "Schmidt", "Weber"
    ]

    NATIONALITIES = [
        "US", "GB", "CA", "DE", "FR", "IT", "ES", "RU", "CN", "IN", "JP", "BR", "MX",
        "AU", "NL", "CH", "SE", "NO", "DK", "FI", "KY", "VG", "PA", "BS", "CY"
    ]

    PEP_TITLES = [
        "Minister", "Deputy Minister", "Senator", "Governor", "Mayor",
        "Board Member", "CEO", "CFO", "Director", "Chairman"
    ]

    def __init__(self, seed: Optional[int] = None):
        import random
        self._random = random.Random(seed)
        self._counter = 0

    def generate(self, seed_override: Optional[int] = None) -> PersonSchema:
        """Generate a single person entity"""
        if seed_override is not None:
            r = random.Random(seed_override)
        else:
            r = self._random

        self._counter += 1
        first_name = r.choice(self.FIRST_NAMES)
        last_name = r.choice(self.LAST_NAMES)
        name = f"{first_name} {last_name}"

        dob = date(1960 + r.randint(0, 40), r.randint(1, 12), r.randint(1, 28))

        tax_id = f"{r.randint(100, 999)}-{r.randint(10, 99)}-{r.randint(1000, 9999)}"

        nationality = r.choice(self.NATIONALITIES)

        risk_score = round(r.uniform(0, 1), 4)
        if risk_score > 0.8:
            risk_level = RiskLevel.CRITICAL
        elif risk_score > 0.6:
            risk_level = RiskLevel.HIGH
        elif risk_score > 0.3:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        is_pep = r.random() < 0.05
        is_sanctioned = r.random() < 0.02
        is_watched = r.random() < 0.08

        aliases = []
        if r.random() < 0.15:
            num_aliases = r.randint(1, 3)
            for _ in range(num_aliases):
                aliases.append(f"{r.choice(self.FIRST_NAMES)} {r.choice(self.LAST_NAMES)}")

        return PersonSchema(
            id=f"P-{self._counter:06d}",
            name=name,
            first_name=first_name,
            last_name=last_name,
            date_of_birth=dob,
            nationality=nationality,
            tax_id=tax_id,
            passport_number=f"{r.randint(100000000, 999999999)}" if r.random() < 0.6 else None,
            phone=f"+1-{r.randint(200, 999)}-{r.randint(100, 999)}-{r.randint(1000, 9999)}" if r.random() < 0.7 else None,
            email=f"{first_name.lower()}.{last_name.lower()}@{r.choice(['gmail.com', 'yahoo.com', 'outlook.com', 'company.com'])}" if r.random() < 0.6 else None,
            risk_score=risk_score,
            risk_level=risk_level,
            is_pep=is_pep,
            is_sanctioned=is_sanctioned,
            is_watched=is_watched,
            aliases=aliases,
        )