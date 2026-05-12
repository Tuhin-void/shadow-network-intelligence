"""
Noise Generator - Semantic ambiguity injection for Vector RAG failure
"""
from typing import List, Optional
import random

from ..schemas.company import CompanySchema, CompanyType
from ..schemas.person import PersonSchema
from ..schemas.address import AddressSchema, AddressType
from ..utils.seed_manager import SeedManager


class NoiseGenerator:
    """
    Generates semantic noise to intentionally confuse Vector RAG systems.

    Creates:
    - Similar company names (ShadowCorp LLC, ShadowCorp Holdings, etc.)
    - Duplicate addresses
    - Similar descriptions
    - Alias proliferation
    """

    VARIANT_PREFIXES = [
        "Shadow", "Midnight", "Sterling", "Phoenix", "Crimson", "Onyx", "Silver",
        "Golden", "Diamond", "Platinum", "Titanium", "Carbon", "Neon", "Cyber",
    ]

    SUFFIXES = [
        "LLC", "Inc", "Holdings", "Group", "International", "Ventures",
        "Services", "Solutions", "Enterprises", "Partners", "Corp",
    ]

    def __init__(self, seed: Optional[int] = None):
        self._seed_manager = SeedManager(global_seed=seed or 42)
        self._counter = 0

    def generate_company_noise(self, count: int = 100, base_name: str = "ShadowCorp") -> List[CompanySchema]:
        """
        Generate semantically similar company names.

        Only ONE should belong to actual fraud ring - the rest are noise
        designed to confuse vector similarity search.
        """
        companies = []
        r = random.Random(self._seed_manager.get_seed("company_noise"))

        for i in range(count):
            self._counter += 1
            prefix = r.choice(self.VARIANT_PREFIXES)
            suffix = r.choice(self.SUFFIXES)
            name = f"{prefix}{suffix}"

            company = CompanySchema(
                id=f"C-NOISE-{self._counter:06d}",
                name=name,
                legal_name=name,
                ein=f"{r.randint(10, 99)}-{r.randint(1000000, 9999999)}",
                industry=r.choice(["Consulting", "Financial Services", "Technology"]),
                company_type=CompanyType.DOMESTIC,
                incorporation_date=__import__('datetime').date(2020, 1, 1),
                risk_score=round(r.uniform(0.1, 0.3), 4),
            )
            companies.append(company)

        return companies

    def generate_address_noise(self, base_addresses: List[AddressSchema], noise_ratio: int = 10) -> List[AddressSchema]:
        """Generate duplicate/similar addresses to create entity resolution confusion"""
        addresses = []
        r = random.Random(self._seed_manager.get_seed("address_noise"))

        for base_addr in base_addresses:
            for i in range(noise_ratio):
                self._counter += 1
                dup = AddressSchema(
                    id=f"ADDR-NOISE-{self._counter:06d}",
                    street_address=base_addr.street_address,
                    city=base_addr.city,
                    state=base_addr.state,
                    postal_code=base_addr.postal_code,
                    country=base_addr.country,
                    address_type=AddressType.MAILBOX,
                    is_shell_location=True,
                    risk_score=round(r.uniform(0.2, 0.4), 4),
                )
                addresses.append(dup)

        return addresses

    def generate_person_alias_noise(self, persons: List[PersonSchema]) -> List[PersonSchema]:
        """Generate ambiguous aliases that could be confused with separate entities"""
        noise_persons = []
        r = random.Random(self._seed_manager.get_seed("person_noise"))

        for person in persons[:50]:
            for i in range(2):
                self._counter += 1
                alias_person = PersonSchema(
                    id=f"P-NOISE-{self._counter:06d}",
                    name=person.aliases[i] if i < len(person.aliases) else f"{person.first_name} {person.last_name}",
                    first_name=person.first_name,
                    last_name=person.last_name,
                    date_of_birth=person.date_of_birth,
                    nationality=person.nationality,
                    tax_id=f"{r.randint(100, 999)}-{r.randint(10, 99)}-{r.randint(1000, 9999)}",
                    risk_score=round(r.uniform(0.1, 0.3), 4),
                    is_pep=False,
                    is_sanctioned=False,
                    is_watched=False,
                )
                noise_persons.append(alias_person)

        return noise_persons

    def generate_description_noise(self, count: int = 50) -> List[str]:
        """Generate similar business descriptions for semantic ambiguity"""
        templates = [
            "Consulting services for international clients",
            "Investment and financial advisory",
            "Global trade and commerce solutions",
            "Strategic business consulting",
            "Financial services and investment management",
            "International business consulting and advisory",
            "Trade and commerce solutions provider",
            "Business consulting and financial services",
        ]

        descriptions = []
        r = random.Random(self._seed_manager.get_seed("desc_noise"))

        for _ in range(count):
            template = r.choice(templates)
            variations = ["", " LLC", " Inc", " Group", " Services"]
            variation = r.choice(variations)
            descriptions.append(template + variation)

        return descriptions