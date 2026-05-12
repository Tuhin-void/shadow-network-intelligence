"""
Account Schema - Bank and crypto account entities
"""
import random
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List
from enum import Enum


class AccountType(Enum):
    CHECKING = "checking"
    SAVINGS = "savings"
    BUSINESS = "business"
    TRUST = "trust"
    CRYPTO_WALLET = "crypto_wallet"
    OFFSHORE = "offshore"
    CORRESPONDENT = "correspondent"


class AccountStatus(Enum):
    ACTIVE = "active"
    DORMANT = "dormant"
    SUSPENDED = "suspended"
    CLOSED = "closed"


@dataclass
class AccountSchema:
    """Bank/Crypto account entity schema"""

    id: str
    account_number: str
    routing_number: Optional[str] = None
    swift_code: Optional[str] = None
    iban: Optional[str] = None
    wallet_address: Optional[str] = None
    account_type: AccountType = AccountType.CHECKING
    owner_id: str = ""
    owner_type: str = "PERSON"
    balance: float = 0.0
    currency: str = "USD"
    opened_date: date = field(default_factory=date.today)
    status: AccountStatus = AccountStatus.ACTIVE
    risk_score: float = 0.0
    velocity_score: float = 0.0
    avg_transaction_size: float = 0.0
    transaction_count: int = 0
    last_activity_date: Optional[date] = None
    is_own_account: bool = False
    is_correspondent: bool = False
    risk_classification: str = "standard"
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "account_number": self.account_number,
            "routing_number": self.routing_number,
            "swift_code": self.swift_code,
            "iban": self.iban,
            "wallet_address": self.wallet_address,
            "account_type": self.account_type.value,
            "owner_id": self.owner_id,
            "owner_type": self.owner_type,
            "balance": self.balance,
            "currency": self.currency,
            "opened_date": self.opened_date.isoformat(),
            "status": self.status.value,
            "risk_score": self.risk_score,
            "velocity_score": self.velocity_score,
            "avg_transaction_size": self.avg_transaction_size,
            "transaction_count": self.transaction_count,
            "last_activity_date": self.last_activity_date.isoformat() if self.last_activity_date else None,
            "is_own_account": self.is_own_account,
            "is_correspondent": self.is_correspondent,
            "risk_classification": self.risk_classification,
            "created_at": self.created_at.isoformat(),
        }

    def to_tigergraph_row(self) -> dict:
        return {
            "account_id": self.id,
            "account_number": self.account_number[-4:] if self.account_number else "",
            "account_type": self.account_type.value,
            "owner_id": self.owner_id,
            "owner_type": self.owner_type,
            "balance": self.balance,
            "currency": self.currency,
            "opened_date": self.opened_date.isoformat(),
            "status": self.status.value,
            "risk_score": self.risk_score,
            "velocity_score": self.velocity_score,
            "is_correspondent": int(self.is_correspondent),
        }

    def to_chromadb_doc(self) -> str:
        doc = f"Account: {self.id}. Type: {self.account_type.value}. "
        doc += f"Owner: {self.owner_id}. Balance: {self.balance} {self.currency}. "
        if self.account_type == AccountType.CRYPTO_WALLET:
            doc += f"Wallet: {self.wallet_address[:16]}... "
        if self.status == AccountStatus.DORMANT:
            doc += "Dormant account. "
        if self.risk_score > 0.6:
            doc += f"High risk score: {self.risk_score}. "
        if self.velocity_score > 0.7:
            doc += f"High velocity: {self.velocity_score}. "
        return doc


class AccountGenerator:
    """Generator for bank and crypto account entities"""

    def __init__(self, seed: Optional[int] = None):
        import random
        self._random = random.Random(seed)
        self._counter = 0

    def generate(
        self,
        owner_id: str = "",
        owner_type: str = "PERSON",
        seed_override: Optional[int] = None,
        force_offshore: bool = False,
    ) -> AccountSchema:
        """Generate a single account entity"""
        if seed_override is not None:
            r = random.Random(seed_override)
        else:
            r = self._random

        self._counter += 1

        account_types = [AccountType.CHECKING, AccountType.SAVINGS, AccountType.BUSINESS]
        if r.random() < 0.08:
            account_types.append(AccountType.CRYPTO_WALLET)
        if force_offshore or r.random() < 0.05:
            account_types.append(AccountType.OFFSHORE)

        account_type = r.choice(account_types)

        if account_type == AccountType.CRYPTO_WALLET:
            wallet_address = self._generate_crypto_address(r)
            account_number = wallet_address[:20]
            routing_number = None
            swift_code = None
            iban = None
        else:
            account_number = f"{r.randint(100000, 999999)}{r.randint(100000, 999999)}"
            routing_number = f"{r.randint(100000, 999999)}"
            swift_code = f"{r.choice(['CHASUS', 'BOFA', 'CITI', 'HSBC', 'DB'])}{r.randint(1000, 9999)}"
            iban = f"{r.choice(['GB', 'DE', 'CH', 'KY'])}{r.randint(10, 99)}{account_number[:18]}"
            wallet_address = None

        is_offshore = force_offshore or account_type == AccountType.OFFSHORE
        currency = "USD"
        if is_offshore:
            currency = r.choice(["USD", "EUR", "CHF"])

        balance = round(r.uniform(0, 500000), 2)
        if owner_type == "COMPANY":
            balance = round(r.uniform(10000, 5000000), 2)

        opened_date = date(2015 + r.randint(0, 9), r.randint(1, 12), r.randint(1, 28))

        risk_score = round(r.uniform(0, 1), 4)
        if is_offshore:
            risk_score = min(1.0, risk_score + 0.25)

        velocity_score = round(r.uniform(0, 1), 4)

        status = AccountStatus.ACTIVE
        if r.random() < 0.03:
            status = AccountStatus.DORMANT
        elif r.random() < 0.01:
            status = AccountStatus.SUSPENDED

        return AccountSchema(
            id=f"A-{self._counter:06d}",
            account_number=account_number,
            routing_number=routing_number,
            swift_code=swift_code,
            iban=iban,
            wallet_address=wallet_address,
            account_type=account_type,
            owner_id=owner_id,
            owner_type=owner_type,
            balance=balance,
            currency=currency,
            opened_date=opened_date,
            status=status,
            risk_score=risk_score,
            velocity_score=velocity_score,
            transaction_count=r.randint(0, 500),
            avg_transaction_size=round(r.uniform(100, 10000), 2),
            last_activity_date=date.today() if r.random() > 0.1 else None,
        )

    def _generate_crypto_address(self, r) -> str:
        """Generate realistic crypto wallet address"""
        prefix = r.choice(["0x", "1", "3", "bc1"])
        chars = "0123456789abcdef"
        if prefix == "0x":
            address = "0x" + "".join(r.choice(chars) for _ in range(40))
        elif prefix == "bc1":
            address = "bc1" + "".join(r.choice(chars) for _ in range(39))
        else:
            address = prefix + "".join(r.choice(chars) for _ in range(33))
        return address