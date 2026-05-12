"""
Person Generator - Person entity generation with PEP/sanctions
"""
from typing import Optional, List
import random
from datetime import date

from ..schemas.person import PersonSchema, RiskLevel


class PersonGenerator:
    """Generator for person entities with realistic AML attributes"""

    FIRST_NAMES = [
        "James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph",
        "Thomas", "Charles", "Mary", "Patricia", "Jennifer", "Linda", "Barbara", "Susan",
        "Jessica", "Sarah", "Karen", "Nancy", "Lisa", "Margaret", "Betty", "Sandra",
        "Elena", "Viktor", "Dmitri", "Alexei", "Ivan", "Chen", "Wei", "Yuki", "Hiroshi",
        "Raj", "Priya", "Amit", "Fatima", "Mohammed", "Ali", "Oleg", "Katarina", "Wei",
        "Hiroshi", "Kenji", "Yuri", "Natalia", "Olga", "Hans", "Franz", "Pierre", "Jean",
    ]

    LAST_NAMES = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
        "Rodriguez", "Martinez", "Anderson", "Taylor", "Thomas", "Moore", "Jackson", "Martin",
        "Petrov", "Ivanov", "Smirnov", "Kuznetsov", "Wang", "Li", "Zhang", "Singh",
        "Kumar", "Patel", "Al-Hassan", "Abbas", "Novak", "Mueller", "Schmidt", "Weber",
        "Dubois", "Martin", "Bernard", "Thompson", "White", "Harris", "Clark", "Lewis",
    ]

    NATIONALITIES = [
        "US", "GB", "CA", "DE", "FR", "IT", "ES", "RU", "CN", "IN", "JP", "BR", "MX",
        "AU", "NL", "CH", "SE", "NO", "DK", "FI", "KY", "VG", "PA", "BS", "CY", "KR",
    ]

    def __init__(self, seed: Optional[int] = None):
        self._random = random.Random(seed)
        self._counter = 0

    def generate(self, seed_override: Optional[int] = None) -> PersonSchema:
        """Generate a single person entity"""
        r = random.Random(seed_override) if seed_override else self._random
        self._counter += 1

        first_name = r.choice(self.FIRST_NAMES)
        last_name = r.choice(self.LAST_NAMES)
        name = f"{first_name} {last_name}"

        dob = date(r.randint(1940, 2000), r.randint(1, 12), r.randint(1, 28))

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

    def generate_batch(self, count: int) -> List[PersonSchema]:
        """Generate multiple person entities"""
        persons = []
        for i in range(count):
            person = self.generate(seed_override=self._random.getstate()[1][0] + i if self._random else None)
            persons.append(person)
        return persons