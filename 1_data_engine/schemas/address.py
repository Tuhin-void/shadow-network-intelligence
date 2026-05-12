"""
Address Schema - Address entities with collision tracking
"""
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class AddressType(Enum):
    RESIDENTIAL = "residential"
    BUSINESS = "business"
    MAILING = "mailing"
    REGISTERED = "registered"
    SHELL_ADDRESS = "shell_address"
    MAILBOX = "mailbox"


class CountryCode(Enum):
    US = "US"
    GB = "GB"
    CA = "CA"
    KY = "KY"
    VG = "VG"
    BS = "VG"
    PA = "PA"
    CH = "CH"
    DE = "DE"
    LU = "LU"


STREET_NAMES = [
    "Main", "Oak", "Pine", "Maple", "Cedar", "Elm", "Washington", "Lincoln",
    "Park", "Lake", "Hill", "Forest", "River", "Valley", "Sunset", "Sunrise",
    "Industrial", "Commerce", "Business", "Corporate", "Executive", "Financial"
]

STREET_TYPES = ["St", "Ave", "Blvd", "Dr", "Way", "Ln", "Rd", "Pl", "Ct"]

CITIES = {
    "US": ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Miami", "Seattle", "Denver", "Atlanta", "Boston", "San Francisco", "Wilmington", "Carson City"],
    "GB": ["London", "Manchester", "Birmingham", "Edinburgh"],
    "KY": ["George Town"],
    "VG": ["Road Town"],
    "PA": ["Panama City"],
    "CH": ["Zurich", "Geneva"],
    "DE": ["Frankfurt", "Berlin"],
    "LU": ["Luxembourg City"],
}

STATES = ["NY", "CA", "TX", "FL", "IL", "WA", "CO", "GA", "MA", "DE", "NV"]


@dataclass
class AddressSchema:
    """Address entity schema with collision support"""

    id: str
    street_address: str
    city: str
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: str = "US"
    address_type: AddressType = AddressType.RESIDENTIAL
    is_shell_location: bool = False
    is_known_fraud_hub: bool = False
    entity_count: int = 0
    risk_score: float = 0.0
    description: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
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
            "description": self.description,
            "created_at": self.created_at.isoformat(),
        }

    def to_tigergraph_row(self) -> dict:
        return {
            "address_id": self.id,
            "street_address": self.street_address,
            "city": self.city,
            "state": self.state or "",
            "postal_code": self.postal_code or "",
            "country": self.country,
            "address_type": self.address_type.value,
            "is_shell_location": int(self.is_shell_location),
            "entity_count": self.entity_count,
            "risk_score": self.risk_score,
        }

    def to_chromadb_doc(self) -> str:
        doc = f"Address: {self.street_address}, {self.city}, {self.state or ''} {self.postal_code or ''}. "
        doc += f"Type: {self.address_type.value}. "
        if self.is_shell_location:
            doc += "Known shell company location. "
        if self.is_known_fraud_hub:
            doc += "Known fraud hub. "
        if self.entity_count > 2:
            doc += f"{self.entity_count} entities registered at this address. "
        return doc

    def get_full_address(self) -> str:
        parts = [self.street_address, self.city]
        if self.state:
            parts.append(self.state)
        if self.postal_code:
            parts.append(self.postal_code)
        parts.append(self.country)
        return ", ".join(parts)


class AddressGenerator:
    """Generator for address entities with collision capability"""

    def __init__(self, seed: Optional[int] = None):
        import random
        self._random = random.Random(seed)
        self._counter = 0

    def generate(
        self,
        seed_override: Optional[int] = None,
        force_shell: bool = False,
        country: str = "US",
    ) -> AddressSchema:
        """Generate a single address entity"""
        if seed_override is not None:
            r = random.Random(seed_override)
        else:
            r = self._random

        self._counter += 1

        is_shell = force_shell or (r.random() < 0.08)
        is_known_fraud_hub = r.random() < 0.03

        if is_shell:
            address_type = AddressType.SHELL_ADDRESS
            street_number = r.randint(1, 99)
            street_name = r.choice(["Suite", "Unit", "Floor", "Mailbox"])
            street_address = f"{street_number} {street_name} {r.randint(1, 500)}"
        else:
            address_type = r.choice([AddressType.RESIDENTIAL, AddressType.BUSINESS, AddressType.REGISTERED])
            street_number = r.randint(100, 9999)
            street_address = f"{street_number} {r.choice(STREET_NAMES)} {r.choice(STREET_TYPES)}"

        available_cities = CITIES.get(country, CITIES["US"])
        city = r.choice(available_cities)

        state = None
        postal_code = None
        if country == "US":
            state = r.choice(STATES)
            postal_code = f"{r.randint(10000, 99999)}"

        risk_score = round(r.uniform(0, 1), 4)
        if is_shell:
            risk_score = min(1.0, risk_score + 0.3)
        if is_known_fraud_hub:
            risk_score = min(1.0, risk_score + 0.4)

        return AddressSchema(
            id=f"ADDR-{self._counter:06d}",
            street_address=street_address,
            city=city,
            state=state,
            postal_code=postal_code,
            country=country,
            address_type=address_type,
            is_shell_location=is_shell,
            is_known_fraud_hub=is_known_fraud_hub,
            risk_score=risk_score,
        )

    def generate_collision_cluster(
        self,
        num_entities: int,
        base_seed: int,
    ) -> List[AddressSchema]:
        """Generate a cluster of addresses that will have entity collisions"""
        addresses = []
        r = random.Random(base_seed)

        base_address = self.generate(seed_override=base_seed, force_shell=True)

        for i in range(num_entities):
            self._counter += 1
            clone = AddressSchema(
                id=f"ADDR-{self._counter:06d}",
                street_address=base_address.street_address,
                city=base_address.city,
                state=base_address.state,
                postal_code=base_address.postal_code,
                country=base_address.country,
                address_type=AddressType.SHELL_ADDRESS,
                is_shell_location=True,
                is_known_fraud_hub=True,
                entity_count=num_entities,
                risk_score=min(1.0, base_address.risk_score + 0.2),
            )
            addresses.append(clone)

        return addresses