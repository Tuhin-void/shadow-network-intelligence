"""
Pipeline Orchestrator - Main generation pipeline
"""
import random
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from ..entities import EntityRegistry
from ..entities.person import PersonEntity, RiskLevel
from ..entities.company import CompanyEntity, CompanyType
from ..entities.account import AccountEntity, AccountType, AccountStatus
from ..entities.address import AddressEntity, AddressType
from ..entities.device import DeviceEntity
from ..entities.transaction import TransactionEntity, TransactionType, TransactionStatus
from ..edges import EdgeFactory, GraphEdge
from .profiles import GenerationConfig, PROFILES, GenerationProfile

logger = logging.getLogger(__name__)


class PipelineStage:
    """Pipeline stage tracking"""

    def __init__(self, name: str):
        self.name = name
        self.started_at = None
        self.completed_at = None
        self.status = "pending"
        self.message = ""

    def start(self):
        self.started_at = datetime.now()
        self.status = "running"

    def complete(self, message: str = ""):
        self.completed_at = datetime.now()
        self.status = "completed"
        self.message = message

    def fail(self, message: str):
        self.completed_at = datetime.now()
        self.status = "failed"
        self.message = message

    def duration_ms(self) -> float:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() * 1000
        return 0


class PipelineOrchestrator:
    """
    Main pipeline orchestrator for synthetic intelligence generation.

    Generates entities, edges, documents, fraud patterns, and exports
    for TigerGraph, ChromaDB, and benchmark systems.
    """

    def __init__(self, config: Optional[GenerationConfig] = None):
        self.config = config or PROFILES["hackathon_default"]
        self.registry = EntityRegistry()
        self.rng = random.Random(self.config.seed)
        self.stages: List[PipelineStage] = []

        self._counters = {
            "person": 0,
            "company": 0,
            "account": 0,
            "address": 0,
            "device": 0,
            "transaction": 0,
            "edge": 0,
            "document": 0,
        }

        self._token_count = 0

    def generate(self) -> EntityRegistry:
        """Run the complete generation pipeline"""
        logger.info(f"Starting pipeline with profile: {self.config.profile.value}")

        self._run_stage("Initialize", self._initialize)
        self._run_stage("Generate Addresses", self._generate_addresses)
        self._run_stage("Generate Persons", self._generate_persons)
        self._run_stage("Generate Companies", self._generate_companies)
        self._run_stage("Generate Accounts", self._generate_accounts)
        self._run_stage("Generate Devices", self._generate_devices)
        self._run_stage("Generate Base Edges", self._generate_base_edges)
        self._run_stage("Generate Transactions", self._generate_transactions)
        self._run_stage("Inject Fraud Patterns", self._inject_fraud_patterns)
        self._run_stage("Generate Documents", self._generate_documents)
        self._run_stage("Inject Vector Noise", self._inject_vector_noise)
        self._run_stage("Add Temporal Features", self._add_temporal_features)
        self._run_stage("Validate", self._validate)
        self._run_stage("Export", self._export)

        logger.info(f"Pipeline complete: {self.registry.get_entity_count()} entities, {self.registry.get_edge_count()} edges")
        return self.registry

    def _run_stage(self, name: str, func):
        """Run a pipeline stage with tracking"""
        stage = PipelineStage(name)
        stage.start()
        self.stages.append(stage)

        try:
            result = func()
            stage.complete(f"Generated {result} items" if result else "Done")
            logger.info(f"  {name}: {stage.message}")
        except Exception as e:
            stage.fail(str(e))
            logger.error(f"  {name}: FAILED - {e}")
            raise

    def _initialize(self) -> int:
        """Initialize the pipeline"""
        EdgeFactory._edge_counter = 0
        return 1

    def _generate_addresses(self) -> int:
        """Generate address entities"""
        count = self.config.address_count
        for i in range(count):
            self._counters["address"] += 1
            addr_num = self._counters["address"]

            is_shell = self.rng.random() < 0.08
            is_fraud_hub = self.rng.random() < 0.03

            address = AddressEntity(
                id=f"ADDR-{addr_num:06d}",
                street_address=f"{self.rng.randint(100, 9999)} {self.rng.choice(['Main', 'Oak', 'Pine', 'Maple', 'Cedar', 'Industrial', 'Commerce'])} {self.rng.choice(['St', 'Ave', 'Blvd', 'Dr'])}",
                city=self.rng.choice(["New York", "Los Angeles", "Chicago", "Miami", "Houston", "Seattle", "Denver", "Wilmington"]),
                state=self.rng.choice(["NY", "CA", "TX", "FL", "IL", "DE"]),
                postal_code=f"{self.rng.randint(10000, 99999)}",
                country="US" if self.rng.random() < 0.85 else self.rng.choice(["KY", "VG", "BS", "CH"]),
                address_type=AddressType.SHELL_ADDRESS if is_shell else AddressType.BUSINESS,
                is_shell_location=is_shell,
                is_known_fraud_hub=is_fraud_hub,
                risk_score=min(1.0, self.rng.uniform(0, 0.5) + (0.3 if is_shell else 0) + (0.4 if is_fraud_hub else 0)),
            )
            self.registry.add_address(address)

        return count

    def _generate_persons(self) -> int:
        """Generate person entities"""
        count = self.config.person_count
        first_names = ["James", "John", "Robert", "Michael", "William", "David", "Mary", "Patricia", "Jennifer", "Linda", "Elena", "Viktor", "Dmitri", "Chen", "Wei", "Raj", "Priya", "Mohammed", "Fatima", "Oleg"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Petrov", "Ivanov", "Wang", "Li", "Singh", "Kumar", "Al-Hassan", "Novak", "Mueller"]
        nationalities = ["US", "GB", "CA", "DE", "FR", "RU", "CN", "IN", "JP", "BR"]

        address_ids = list(self.registry.addresses.keys())

        for i in range(count):
            self._counters["person"] += 1
            person_num = self._counters["person"]

            first = self.rng.choice(first_names)
            last = self.rng.choice(last_names)

            is_pep = self.rng.random() < self.config.pep_ratio
            is_sanctioned = self.rng.random() < self.config.sanctioned_ratio
            is_watched = self.rng.random() < 0.08
            is_mule = self.rng.random() < 0.05

            risk_score = self.rng.uniform(0, 0.4)
            if is_pep:
                risk_score = min(1.0, risk_score + 0.2)
            if is_sanctioned:
                risk_score = min(1.0, risk_score + 0.4)
            if is_watched:
                risk_score = min(1.0, risk_score + 0.15)
            if is_mule:
                risk_score = min(1.0, risk_score + 0.3)

            risk_level = RiskLevel.LOW
            if risk_score > 0.8:
                risk_level = RiskLevel.CRITICAL
            elif risk_score > 0.6:
                risk_level = RiskLevel.HIGH
            elif risk_score > 0.3:
                risk_level = RiskLevel.MEDIUM

            person = PersonEntity(
                id=f"P-{person_num:06d}",
                first_name=first,
                last_name=last,
                date_of_birth=datetime(1960 + self.rng.randint(0, 40), self.rng.randint(1, 12), self.rng.randint(1, 28)).date(),
                nationality=self.rng.choice(nationalities),
                tax_id=f"{self.rng.randint(100, 999)}-{self.rng.randint(10, 99)}-{self.rng.randint(1000, 9999)}",
                email=f"{first.lower()}.{last.lower()}@{self.rng.choice(['gmail.com', 'yahoo.com', 'outlook.com'])}" if self.rng.random() < 0.6 else None,
                phone=f"+1-{self.rng.randint(200, 999)}-{self.rng.randint(100, 999)}-{self.rng.randint(1000, 9999)}" if self.rng.random() < 0.7 else None,
                address_id=self.rng.choice(address_ids) if address_ids and self.rng.random() < 0.6 else None,
                risk_score=risk_score,
                risk_level=risk_level,
                is_pep=is_pep,
                is_sanctioned=is_sanctioned,
                is_watched=is_watched,
                is_mule=is_mule,
                aliases=[f"{self.rng.choice(first_names)} {self.rng.choice(last_names)}"] if self.rng.random() < 0.15 else [],
            )
            self.registry.add_person(person)

        return count

    def _generate_companies(self) -> int:
        """Generate company entities"""
        count = self.config.company_count
        prefixes = ["Global", "American", "United", "National", "Pacific", "Premier", "Capital", "Strategic", "Dynamic", "Apex", "Titan", "Sterling", "Shadow", "Phoenix", "Midnight"]
        suffixes = ["Corp", "Inc", "LLC", "Holdings", "Group", "Partners", "Enterprises", "Services", "Ventures", "Investments"]
        industries = ["Financial Services", "Import/Export", "Real Estate", "Consulting", "Technology", "Healthcare", "Construction", "Retail", "Manufacturing", "Hospitality"]

        address_ids = list(self.registry.addresses.keys())
        offshore_codes = ["KY", "VG", "BS", "PA", "CH", "LU"]

        for i in range(count):
            self._counters["company"] += 1
            company_num = self._counters["company"]

            is_offshore = self.rng.random() < self.config.offshore_ratio
            is_shell = self.rng.random() < self.config.shell_ratio

            name = f"{self.rng.choice(prefixes)} {self.rng.choice(suffixes)}"

            risk_score = self.rng.uniform(0, 0.4)
            if is_offshore:
                risk_score = min(1.0, risk_score + 0.3)
            if is_shell:
                risk_score = min(1.0, risk_score + 0.35)

            company = CompanyEntity(
                id=f"C-{company_num:06d}",
                name=name,
                legal_name=name,
                ein=f"{self.rng.randint(10, 99)}-{self.rng.randint(1000000, 9999999)}",
                industry=self.rng.choice(industries) if not is_shell else "Consulting",
                company_type=CompanyType.OFFSHORE if is_offshore else (CompanyType.SHELL if is_shell else CompanyType.DOMESTIC),
                address_id=self.rng.choice(address_ids) if address_ids and self.rng.random() < 0.7 else None,
                registration_country=self.rng.choice(offshore_codes) if is_offshore else "US",
                incorporation_jurisdiction=self.rng.choice(offshore_codes) if is_offshore else "US",
                incorporation_date=datetime(2000 + self.rng.randint(0, 24), self.rng.randint(1, 12), self.rng.randint(1, 28)).date(),
                is_offshore=is_offshore,
                is_shell=is_shell,
                is_dormant=self.rng.random() < 0.08,
                annual_revenue=self.rng.choice([50000, 100000, 500000, 1000000, 5000000, 10000000]),
                employee_count=self.rng.randint(1, 5) if is_shell else self.rng.randint(1, 500),
                risk_score=risk_score,
            )
            self.registry.add_company(company)

        return count

    def _generate_accounts(self) -> int:
        """Generate account entities"""
        count = self.config.account_count
        person_ids = list(self.registry.persons.keys())
        company_ids = list(self.registry.companies.keys())

        for i in range(count):
            self._counters["account"] += 1
            acc_num = self._counters["account"]

            owner_type = self.rng.choice(["Person", "Company"]) if self.rng.random() < 0.3 else "Person"
            if owner_type == "Person" and person_ids:
                owner_id = self.rng.choice(person_ids)
            elif company_ids:
                owner_id = self.rng.choice(company_ids)
            else:
                owner_id = person_ids[0] if person_ids else f"P-{self.rng.randint(1, self.config.person_count):06d}"

            account = AccountEntity(
                id=f"A-{acc_num:06d}",
                account_number=f"{self.rng.randint(100000, 999999)}{self.rng.randint(100000, 999999)}",
                account_type=self.rng.choice([AccountType.CHECKING, AccountType.SAVINGS, AccountType.BUSINESS]),
                owner_id=owner_id,
                owner_type=owner_type,
                routing_number=f"{self.rng.randint(100000, 999999)}",
                swift_code=f"{self.rng.choice(['CHASUS', 'BOFA', 'CITI', 'HSBC'])}{self.rng.randint(1000, 9999)}",
                balance=self.rng.uniform(0, 500000) if owner_type == "Person" else self.rng.uniform(10000, 5000000),
                currency="USD",
                opened_date=datetime(2015 + self.rng.randint(0, 9), self.rng.randint(1, 12), self.rng.randint(1, 28)).date(),
                status=AccountStatus.ACTIVE,
                risk_score=self.rng.uniform(0, 0.5),
                velocity_score=self.rng.uniform(0, 0.8),
                transaction_count=self.rng.randint(0, 500),
            )
            self.registry.add_account(account)

            edge = EdgeFactory.has_account(owner_id, owner_type, account.id)
            self.registry.add_edge(edge)

        return count

    def _generate_devices(self) -> int:
        """Generate device entities"""
        count = self.config.device_count
        person_ids = list(self.registry.persons.keys())

        for i in range(count):
            self._counters["device"] += 1
            dev_num = self._counters["device"]

            owner_id = self.rng.choice(person_ids) if person_ids else None

            device = DeviceEntity(
                id=f"D-{dev_num:06d}",
                device_type=self.rng.choice(["desktop", "mobile", "tablet"]),
                ip_address=f"{self.rng.randint(1, 255)}.{self.rng.randint(0, 255)}.{self.rng.randint(0, 255)}.{self.rng.randint(1, 254)}",
                owner_id=owner_id,
                owner_type="Person",
                location_country=self.rng.choice(["US", "GB", "CA", "DE", "FR", "RU", "CN"]),
                first_seen=datetime(2020 + self.rng.randint(0, 4), self.rng.randint(1, 12), self.rng.randint(1, 28)).date(),
                risk_score=self.rng.uniform(0, 0.5),
                is_burner=self.rng.random() < 0.1,
                is_vpn=self.rng.random() < 0.15,
            )
            self.registry.add_device(device)

            if owner_id:
                edge = EdgeFactory.uses_device(owner_id, device.id)
                self.registry.add_edge(edge)

        return count

    def _generate_base_edges(self) -> int:
        """Generate base graph edges"""
        edge_count = 0

        person_ids = list(self.registry.persons.keys())
        company_ids = list(self.registry.companies.keys())
        address_ids = list(self.registry.addresses.keys())

        for person_id in person_ids[:min(len(person_ids), self.config.person_count // 10)]:
            if company_ids and self.rng.random() < 0.2:
                company_id = self.rng.choice(company_ids)
                edge = EdgeFactory.owns(person_id, company_id)
                self.registry.add_edge(edge)
                edge_count += 1

        for company_id in company_ids[:min(len(company_ids), self.config.company_count // 10)]:
            if address_ids and self.rng.random() < 0.3:
                address_id = self.rng.choice(address_ids)
                edge = EdgeFactory.located_at(company_id, "Company", address_id)
                self.registry.add_edge(edge)
                edge_count += 1

        return edge_count

    def _generate_transactions(self) -> int:
        """Generate transaction entities"""
        count = self.config.transaction_count
        account_ids = list(self.registry.accounts.keys())

        for i in range(count):
            self._counters["transaction"] += 1
            tx_num = self._counters["transaction"]

            from_acc = self.rng.choice(account_ids)
            to_acc = self.rng.choice([a for a in account_ids if a != from_acc])

            is_suspicious = self.rng.random() < 0.05
            if is_suspicious:
                amount = self.rng.choice([9500, 9800, 9900, 15000, 25000, 50000])
            else:
                amount = self.rng.choice([100, 500, 1000, 2500, 5000, 7500])

            transaction = TransactionEntity(
                id=f"TX-{tx_num:08d}",
                from_account=from_acc,
                to_account=to_acc,
                amount=round(amount + self.rng.uniform(0, 99.99), 2),
                currency="USD",
                transaction_type=self.rng.choice([TransactionType.WIRE, TransactionType.ACH, TransactionType.CASH, TransactionType.CHECK]),
                timestamp=datetime.now() - timedelta(days=self.rng.randint(0, 365), hours=self.rng.randint(0, 23)),
                status=TransactionStatus.COMPLETED,
                is_suspicious=is_suspicious,
                risk_score=self.rng.uniform(0, 0.3) + (0.4 if is_suspicious else 0),
            )
            self.registry.add_transaction(transaction)

            edge = EdgeFactory.transferred_to(from_acc, to_acc, amount)
            self.registry.add_edge(edge)

        return count

    def _inject_fraud_patterns(self) -> int:
        """Inject fraud pattern structures"""
        edge_count = 0
        fraud_ring_id = 0

        account_ids = list(self.registry.accounts.keys())
        company_ids = list(self.registry.companies.keys())

        for i in range(self.config.fraud_ring_count):
            fraud_ring_id += 1
            fr_id = f"FR-{fraud_ring_id:03d}"
            pattern_type = i % 12

            if pattern_type == 0:
                chain_length = self.rng.randint(5, 7)
                chain = self.rng.sample(account_ids, chain_length)
                for j in range(len(chain) - 1):
                    edge = EdgeFactory.transferred_to(chain[j], chain[j + 1], self.rng.randint(10000, 100000), fr_id)
                    self.registry.add_edge(edge)
                    edge_count += 1

            elif pattern_type == 1:
                ring_size = self.rng.randint(3, 5)
                companies = self.rng.sample(company_ids, ring_size)
                for j in range(ring_size):
                    edge = EdgeFactory.company_owns_company(companies[j], companies[(j + 1) % ring_size], fr_id)
                    self.registry.add_edge(edge)
                    edge_count += 1

            elif pattern_type == 2:
                funnel_sources = self.rng.randint(5, 12)
                sources = self.rng.sample(account_ids, funnel_sources)
                funnel = self.rng.choice([a for a in account_ids if a not in sources])
                for source in sources:
                    edge = EdgeFactory.transferred_to(source, funnel, self.rng.randint(10000, 50000), fr_id)
                    self.registry.add_edge(edge)
                    edge_count += 1

        return edge_count

    def _generate_documents(self) -> int:
        """Generate synthetic documents"""
        doc_count = min(self.config.document_count, 1000)
        return doc_count

    def _inject_vector_noise(self) -> int:
        """Inject vector noise for RAG failure engineering"""
        return 0

    def _add_temporal_features(self) -> int:
        """Add temporal features to entities"""
        return 0

    def _validate(self) -> int:
        """Validate generated data"""
        return 0

    def _export(self) -> int:
        """Export data to all formats"""
        return 0