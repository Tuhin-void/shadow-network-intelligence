"""
Company Generator - Company entity generation with shell/offshore injection
"""
from typing import Optional, List
import random

from ..schemas.company import CompanySchema, CompanyType


OFFSHORE_JURISDICTIONS = ["KY", "VG", "BS", "PA", "CY", "LU", "CH", "LI", "MC", "AN"]
HIGH_RISK_INDUSTRIES = ["Financial Services", "Import/Export", "Consulting", "Holding"]


class CompanyGenerator:
    """Generator for company entities with shell/offshore injection"""

    PREFIXES = [
        "Global", "American", "United", "National", "Pacific", "Atlantic",
        "Premier", "Capital", "Financial", "Investment", "Strategic", "Dynamic",
        "Advanced", "Quantum", "Nexus", "Apex", "Vertex", "Horizon", "Summit",
        "Imperial", "Royal", "Crown", "Phoenix", "Titan", "Omega", "Alpha",
        "Delta", "Sigma", "Omega", "Epsilon", "Zeta", "Prime", "Elite",
        "Shadow", "Midnight", "Sterling", "Crimson", "Onyx", "Silver", "Golden",
    ]

    SUFFIXES = [
        "Corp", "Inc", "LLC", "Holdings", "Group", "Partners", "Enterprises",
        "Services", "Solutions", "Associates", "Consulting", "Management",
        "Ventures", "Capital", "Investments", "Trading", "Logistics", "Systems",
        "Technologies", "Dynamics", "Industries", "Limited", "Co", "Foundation",
    ]

    VARIANT_PREFIXES = [
        "Shadow", "Midnight", "Sterling", "Phoenix", "Crimson", "Onyx", "Silver",
        "Golden", "Diamond", "Platinum", "Titanium", "Carbon", "Neon", "Cyber",
    ]

    INDUSTRIES = [
        "Financial Services", "Import/Export", "Real Estate", "Consulting",
        "Technology", "Healthcare", "Construction", "Retail", "Manufacturing",
        "Hospitality", "Transportation", "Energy", "Media", "Education",
    ]

    def __init__(self, seed: Optional[int] = None):
        self._random = random.Random(seed)
        self._counter = 0

    def generate(
        self,
        seed_override: Optional[int] = None,
        force_offshore: bool = False,
        force_shell: bool = False,
    ) -> CompanySchema:
        """Generate a single company entity"""
        r = random.Random(seed_override) if seed_override else self._random
        self._counter += 1

        is_offshore = force_offshore or (r.random() < 0.12)
        is_shell = force_shell or (r.random() < 0.10)

        if is_offshore:
            jurisdiction = r.choice(OFFSHORE_JURISDICTIONS)
            country = jurisdiction
            company_type = CompanyType.OFFSHORE
            name = f"{r.choice(self.PREFIXES)} {r.choice(self.VARIANT_PREFIXES)} {r.choice(self.SUFFIXES)}"
        else:
            jurisdiction = "US"
            country = "US"
            if is_shell:
                company_type = CompanyType.SHELL
                name = f"{r.choice(self.PREFIXES)} {r.choice(self.SUFFIXES)}"
            else:
                company_type = CompanyType.DOMESTIC
                name = f"{r.choice(self.PREFIXES)} {r.choice(self.SUFFIXES)}"

        industry = r.choice(self.INDUSTRIES)
        if is_shell:
            industry = "Consulting"

        ein = f"{r.randint(10, 99)}-{r.randint(1000000, 9999999)}"

        years_active = r.randint(1, 40)
        from datetime import date
        incorporation_date = date(1984 + r.randint(0, years_active), r.randint(1, 12), r.randint(1, 28))

        revenue_options = [50000, 100000, 250000, 500000, 1000000, 2500000, 5000000, 10000000, 50000000]
        annual_revenue = r.choice(revenue_options)

        risk_score = round(r.uniform(0, 1), 4)
        if is_offshore or is_shell:
            risk_score = min(1.0, risk_score + 0.3)
        if industry in HIGH_RISK_INDUSTRIES:
            risk_score = min(1.0, risk_score + 0.15)

        is_dormant = r.random() < 0.08

        return CompanySchema(
            id=f"C-{self._counter:06d}",
            name=name,
            legal_name=name,
            ein=ein,
            industry=industry,
            company_type=company_type,
            incorporation_date=incorporation_date,
            is_offshore=is_offshore,
            is_shell=is_shell,
            is_dormant=is_dormant,
            annual_revenue=annual_revenue,
            employee_count=r.randint(1, 500) if not is_shell else r.randint(1, 5),
            risk_score=risk_score,
            registration_country=country,
            incorporation_jurisdiction=jurisdiction,
        )

    def generate_ambiguous(self, count: int = 100) -> List[CompanySchema]:
        """Generate semantically ambiguous company names for Vector RAG failure"""
        companies = []
        for i in range(count):
            r = random.Random(1000 + i)
            self._counter += 1
            name = f"{r.choice(self.VARIANT_PREFIXES)}Corp {r.choice(self.SUFFIXES)}"
            companies.append(CompanySchema(
                id=f"C-AMB-{self._counter:06d}",
                name=name,
                legal_name=name,
                ein=f"{r.randint(10, 99)}-{r.randint(1000000, 9999999)}",
                industry="Consulting",
                company_type=CompanyType.DOMESTIC,
                incorporation_date=date(2020, 1, 1),
                risk_score=r.uniform(0.1, 0.3),
            ))
        return companies