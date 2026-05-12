"""
Address Generator - Address entities with collision tracking
"""
from typing import Optional, List
import random
from datetime import date

from ..schemas.address import AddressSchema, AddressType


STREET_NAMES = [
    "Main", "Oak", "Pine", "Maple", "Cedar", "Elm", "Washington", "Lincoln",
    "Park", "Lake", "Hill", "Forest", "River", "Valley", "Sunset", "Sunrise",
    "Industrial", "Commerce", "Business", "Corporate", "Executive", "Financial",
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


class AddressGenerator:
    """Generator for address entities with collision capability"""

    def __init__(self, seed: Optional[int] = None):
        self._random = random.Random(seed)
        self._counter = 0

    def generate(
        self,
        seed_override: Optional[int] = None,
        force_shell: bool = False,
        country: str = "US",
    ) -> AddressSchema:
        """Generate a single address entity"""
        r = random.Random(seed_override) if seed_override else self._random
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
        """Generate a cluster of addresses with shared address for collision"""
        addresses = []
        base_address = self.generate(seed_override=base_seed, force_shell=True)
        base_address.entity_count = num_entities

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