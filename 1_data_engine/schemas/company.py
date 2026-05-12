"""
Company Schema - Company entity with shell/offshore/international structures
"""
import random
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List
from enum import Enum


class CompanyType(Enum):
    DOMESTIC = "domestic"
    OFFSHORE = "offshore"
    SHELL = "shell"
    HOLDING = "holding"
    SUBSIDIARY = "subsidiary"
    TRUST = "trust"


class Industry(Enum):
    FINANCIAL_SERVICES = "Financial Services"
    IMPORT_EXPORT = "Import/Export"
    REAL_ESTATE = "Real Estate"
    CONSULTING = "Consulting"
    TECHNOLOGY = "Technology"
    HEALTHCARE = "Healthcare"
    CONSTRUCTION = "Construction"
    RETAIL = "Retail"
    MANUFACTURING = "Manufacturing"
    HOSPITALITY = "Hospitality"
    TRANSPORTATION = "Transportation"
    ENERGY = "Energy"


OFFSHORE_JURISDICTIONS = ["KY", "VG", "BS", "PA", "CY", "LU", "CH", "LI", "MC", "AN"]
HIGH_RISK_INDUSTRIES = ["Financial Services", "Import/Export", "Consulting", "Holding"]


@dataclass
class CompanySchema:
    """Company entity schema for AML data generation"""

    id: str
    name: str
    legal_name: str
    ein: str
    industry: str
    company_type: CompanyType
    incorporation_date: date
    dissolution_date: Optional[date] = None
    address_id: Optional[str] = None
    registration_country: str = "US"
    incorporation_jurisdiction: str = "US"
    is_offshore: bool = False
    is_shell: bool = False
    is_dormant: bool = False
    annual_revenue: Optional[int] = None
    employee_count: int = 1
    risk_score: float = 0.0
    beneficial_owners: List[str] = field(default_factory=list)
    directors: List[str] = field(default_factory=list)
    parent_company: Optional[str] = None
    subsidiaries: List[str] = field(default_factory=list)
    associated_entities: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "legal_name": self.legal_name,
            "ein": self.ein,
            "industry": self.industry,
            "company_type": self.company_type.value,
            "incorporation_date": self.incorporation_date.isoformat(),
            "dissolution_date": self.dissolution_date.isoformat() if self.dissolution_date else None,
            "address_id": self.address_id,
            "registration_country": self.registration_country,
            "incorporation_jurisdiction": self.incorporation_jurisdiction,
            "is_offshore": self.is_offshore,
            "is_shell": self.is_shell,
            "is_dormant": self.is_dormant,
            "annual_revenue": self.annual_revenue,
            "employee_count": self.employee_count,
            "risk_score": self.risk_score,
            "beneficial_owners": self.beneficial_owners,
            "directors": self.directors,
            "parent_company": self.parent_company,
            "subsidiaries": self.subsidiaries,
            "associated_entities": self.associated_entities,
            "created_at": self.created_at.isoformat(),
        }

    def to_tigergraph_row(self) -> dict:
        return {
            "company_id": self.id,
            "name": self.name,
            "legal_name": self.legal_name,
            "ein": self.ein,
            "industry": self.industry,
            "company_type": self.company_type.value,
            "incorporation_date": self.incorporation_date.isoformat(),
            "registration_country": self.registration_country,
            "incorporation_jurisdiction": self.incorporation_jurisdiction,
            "is_offshore": int(self.is_offshore),
            "is_shell": int(self.is_shell),
            "is_dormant": int(self.is_dormant),
            "annual_revenue": self.annual_revenue or 0,
            "employee_count": self.employee_count,
            "risk_score": self.risk_score,
        }

    def to_chromadb_doc(self) -> str:
        doc = f"Company: {self.name}. "
        doc += f"Industry: {self.industry}. "
        doc += f"Incorporated: {self.incorporation_date.isoformat()}. "
        if self.is_offshore:
            doc += f"Offshore entity in {self.incorporation_jurisdiction}. "
        if self.is_shell:
            doc += "Shell company. "
        if self.beneficial_owners:
            doc += f"Beneficial owners: {', '.join(self.beneficial_owners)}. "
        doc += f"Risk score: {self.risk_score}. "
        return doc


class CompanyGenerator:
    """Generator for company entities with shell/offshore injection"""

    PREFIXES = [
        "Global", "American", "United", "National", "Pacific", "Atlantic",
        "Premier", "Capital", "Financial", "Investment", "Strategic", "Dynamic",
        "Advanced", "Quantum", "Nexus", "Apex", "Vertex", "Horizon", "Summit",
        "Imperial", "Royal", "Crown", "Phoenix", "Titan", "Omega", "Alpha",
        "Delta", "Sigma", "Omega", "Epsilon", "Zeta", "Prime", "Elite",
        "Shadow", "Midnight", "Sterling", "Phoenix", "Crimson", "Onyx"
    ]

    SUFFIXES = [
        "Corp", "Inc", "LLC", "Holdings", "Group", "Partners", "Enterprises",
        "Services", "Solutions", "Associates", "Consulting", "Management",
        "Ventures", "Capital", "Investments", "Trading", "Logistics", "Systems",
        "Technologies", "Dynamics", "Industries", "Limited", "Co", "Foundation"
    ]

    VARIANT_PREFIXES = [
        "Shadow", "Midnight", "Sterling", "Phoenix", "Crimson", "Onyx", "Silver",
        "Golden", "Diamond", "Platinum", "Titanium", "Carbon", "Neon", "Cyber"
    ]

    INDUSTRIES = list(Industry)

    def __init__(self, seed: Optional[int] = None):
        import random
        self._random = random.Random(seed)
        self._counter = 0

    def generate(self, seed_override: Optional[int] = None, force_offshore: bool = False, force_shell: bool = False) -> CompanySchema:
        """Generate a single company entity"""
        if seed_override is not None:
            r = random.Random(seed_override)
        else:
            r = self._random

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

        industry = r.choice(self.INDUSTRIES).value
        if is_shell:
            industry = "Consulting"

        ein = f"{r.randint(10, 99)}-{r.randint(1000000, 9999999)}"

        years_active = r.randint(1, 40)
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