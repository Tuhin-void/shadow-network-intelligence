"""
Entity Factory - High-level factory orchestrator for all entity generation
"""
import random
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import date, datetime

from ..schemas.entity_registry import EntityRegistry
from ..schemas.person import PersonSchema, PersonGenerator
from ..schemas.company import CompanySchema, CompanyGenerator
from ..schemas.account import AccountSchema, AccountGenerator
from ..schemas.address import AddressSchema, AddressGenerator
from ..schemas.transaction import TransactionSchema, TransactionGenerator
from ..schemas.edge import EdgeBuilder, RelationshipType
from ..utils.seed_manager import SeedManager
from ..utils.logger import get_logger
from ..configs import ConfigLoader

logger = get_logger(__name__)


@dataclass
class GenerationConfig:
    """Configuration for entity generation"""

    profile: str = "hackathon_default"
    seed: int = 42

    person_count: int = 6000
    company_count: int = 5000
    account_count: int = 10000
    address_count: int = 4000

    edge_target: int = 500000
    fraud_ring_count: int = 15

    offshore_ratio: float = 0.12
    shell_ratio: float = 0.10
    pep_ratio: float = 0.05
    sanctioned_ratio: float = 0.02


class EntityFactory:
    """
    High-level factory for generating synthetic AML entities.

    Orchestrates generation of:
    - Persons (with PEP/sanctions flags)
    - Companies (with offshore/shell injection)
    - Accounts (bank/crypto with velocity)
    - Addresses (with collision capability)
    - Transactions (baseline for fraud injection)
    """

    def __init__(self, config: Optional[GenerationConfig] = None):
        self.config = config or GenerationConfig()
        self.seed_manager = SeedManager(global_seed=self.config.seed)

        self.person_gen = PersonGenerator(seed=self.seed_manager.get_seed("person"))
        self.company_gen = CompanyGenerator(seed=self.seed_manager.get_seed("company"))
        self.account_gen = AccountGenerator(seed=self.seed_manager.get_seed("account"))
        self.address_gen = AddressGenerator(seed=self.seed_manager.get_seed("address"))
        self.transaction_gen = TransactionGenerator(seed=self.seed_manager.get_seed("transaction"))

        self.registry = EntityRegistry()

        self._person_counter = 0
        self._company_counter = 0
        self._account_counter = 0
        self._address_counter = 0
        self._transaction_counter = 0

        logger.info(f"EntityFactory initialized with profile: {self.config.profile}")

    def generate_all(self) -> EntityRegistry:
        """Generate all entities according to config"""
        logger.info("Starting entity generation...")

        logger.info(f"Generating {self.config.address_count} addresses...")
        self._generate_addresses()

        logger.info(f"Generating {self.config.person_count} persons...")
        self._generate_persons()

        logger.info(f"Generating {self.config.company_count} companies...")
        self._generate_companies()

        logger.info(f"Generating {self.config.account_count} accounts...")
        self._generate_accounts()

        logger.info("Generating baseline transactions...")
        self._generate_baseline_transactions()

        logger.info(f"Entity generation complete. Total: {self.registry.get_entity_count()} entities")

        return self.registry

    def _generate_addresses(self):
        """Generate address entities"""
        for i in range(self.config.address_count):
            force_shell = random.Random(self.seed_manager.get_seed("address") + i).random() < 0.08
            addr = self.address_gen.generate(force_shell=force_shell)
            self.registry.add_address(addr)

    def _generate_persons(self):
        """Generate person entities with PEP/sanctions"""
        address_ids = list(self.registry.addresses.keys())

        for i in range(self.config.person_count):
            seed = self.seed_manager.get_seed("person") + i
            person = self.person_gen.generate(seed_override=seed)

            if address_ids and random.Random(seed).random() < 0.6:
                person.address_id = random.Random(seed).choice(address_ids)

            self.registry.add_person(person)
            self._person_counter += 1

            if self._person_counter % 1000 == 0:
                logger.info(f"  Generated {self._person_counter} persons")

    def _generate_companies(self):
        """Generate company entities with offshore/shell injection"""
        address_ids = list(self.registry.addresses.keys())

        for i in range(self.config.company_count):
            seed = self.seed_manager.get_seed("company") + i
            r = random.Random(seed)

            force_offshore = r.random() < self.config.offshore_ratio
            force_shell = r.random() < self.config.shell_ratio

            company = self.company_gen.generate(
                seed_override=seed,
                force_offshore=force_offshore,
                force_shell=force_shell,
            )

            if address_ids and r.random() < 0.7:
                company.address_id = r.choice(address_ids)

            self.registry.add_company(company)
            self._company_counter += 1

            if self._company_counter % 1000 == 0:
                logger.info(f"  Generated {self._company_counter} companies")

    def _generate_accounts(self):
        """Generate account entities linked to persons and companies"""
        person_ids = list(self.registry.persons.keys())
        company_ids = list(self.registry.companies.keys())

        for i in range(self.config.account_count):
            seed = self.seed_manager.get_seed("account") + i
            r = random.Random(seed)

            owner_type = r.choice(["PERSON", "COMPANY"])
            if owner_type == "PERSON" and person_ids:
                owner_id = r.choice(person_ids)
            elif company_ids:
                owner_id = r.choice(company_ids)
            else:
                owner_id = f"P-{r.randint(1, self.config.person_count):06d}"

            force_offshore = r.random() < 0.05

            account = self.account_gen.generate(
                owner_id=owner_id,
                owner_type=owner_type,
                seed_override=seed,
                force_offshore=force_offshore,
            )

            self.registry.add_account(account)

            edge = EdgeBuilder.owner_has_account(owner_id, owner_type, account.id)
            self.registry.add_edge(edge)

            self._account_counter += 1

            if self._account_counter % 2000 == 0:
                logger.info(f"  Generated {self._account_counter} accounts")

    def _generate_baseline_transactions(self):
        """Generate baseline transactions for realistic financial ecosystem"""
        account_ids = list(self.registry.accounts.keys())
        if not account_ids:
            logger.warning("No accounts available for transactions")
            return

        baseline_tx_count = int(self.config.edge_target * 0.3)
        logger.info(f"Generating {baseline_tx_count} baseline transactions...")

        for i in range(baseline_tx_count):
            seed = self.seed_manager.get_seed("transaction") + i
            r = random.Random(seed)

            from_acc = r.choice(account_ids)
            to_acc = r.choice(account_ids)

            if from_acc == to_acc:
                continue

            tx = self.transaction_gen.generate(
                from_account=from_acc,
                to_account=to_acc,
                seed_override=seed,
            )

            self.registry.add_transaction(tx)

            edge = EdgeBuilder.account_transfer(
                from_acc,
                to_acc,
                amount=tx.amount,
            )
            self.registry.add_edge(edge)

            self._transaction_counter += 1

            if self._transaction_counter % 10000 == 0:
                logger.info(f"  Generated {self._transaction_counter} transactions")

    def get_registry(self) -> EntityRegistry:
        return self.registry