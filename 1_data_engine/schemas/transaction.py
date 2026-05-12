"""
Transaction Schema - Financial transaction entities
"""
import random
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import Optional
from enum import Enum


class TransactionType(Enum):
    WIRE = "wire"
    ACH = "ach"
    CASH = "cash"
    CHECK = "check"
    CRYPTO = "crypto"
    INTERNATIONAL = "international"
    INTERNAL = "internal"


class TransactionStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FLAGGED = "flagged"
    BLOCKED = "blocked"
    RETURNED = "returned"


@dataclass
class TransactionSchema:
    """Financial transaction entity schema"""

    id: str
    from_account: str
    to_account: str
    amount: float
    currency: str = "USD"
    transaction_type: TransactionType = TransactionType.WIRE
    status: TransactionStatus = TransactionStatus.COMPLETED
    timestamp: datetime = field(default_factory=datetime.now)
    description: Optional[str] = None
    reference: Optional[str] = None
    is_suspicious: bool = False
    risk_score: float = 0.0
    is_layering: bool = False
    is_placement: bool = False
    is_integration: bool = False
    is_structuring: bool = False
    is_smurfing: bool = False
    related_transactions: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "from_account": self.from_account,
            "to_account": self.to_account,
            "amount": self.amount,
            "currency": self.currency,
            "transaction_type": self.transaction_type.value,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "description": self.description,
            "reference": self.reference,
            "is_suspicious": self.is_suspicious,
            "risk_score": self.risk_score,
            "is_layering": self.is_layering,
            "is_placement": self.is_placement,
            "is_integration": self.is_integration,
            "is_structuring": self.is_structuring,
            "is_smurfing": self.is_smurfing,
            "related_transactions": self.related_transactions,
            "metadata": self.metadata,
        }

    def to_tigergraph_row(self) -> dict:
        return {
            "transaction_id": self.id,
            "from_account": self.from_account,
            "to_account": self.to_account,
            "amount": self.amount,
            "currency": self.currency,
            "transaction_type": self.transaction_type.value,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "is_suspicious": int(self.is_suspicious),
            "risk_score": self.risk_score,
        }

    def to_chromadb_doc(self) -> str:
        doc = f"Transaction: {self.id}. "
        doc += f"From: {self.from_account} To: {self.to_account}. "
        doc += f"Amount: {self.amount} {self.currency}. "
        doc += f"Type: {self.transaction_type.value}. "
        if self.is_suspicious:
            doc += "FLAGGED. "
        if self.is_layering:
            doc += "Layering activity. "
        if self.is_smurfing:
            doc += "Smurfing pattern. "
        doc += f"Risk score: {self.risk_score}. "
        return doc


class TransactionGenerator:
    """Generator for financial transaction entities"""

    DESCRIPTIONS = [
        "Payment for services",
        "Invoice payment",
        "Transfer to savings",
        "Wire transfer",
        "ACH payment",
        "Business expense",
        "Consulting fee",
        "Investment",
        "Loan repayment",
        "Royalty payment",
        "Dividend distribution",
        "Rent payment",
        "Vendor payment",
        "Payroll",
        "Contractor payment",
    ]

    SUSPICIOUS_DESCRIPTIONS = [
        "Unusual activity",
        "Round amount transfer",
        "Quick round trip",
        "Layered transfer",
        "Structuring activity",
        "Offshore routing",
    ]

    NORMAL_AMOUNTS = [100, 250, 500, 1000, 2500, 5000, 7500, 10000]
    SUSPICIOUS_AMOUNTS = [9500, 9800, 9900, 15000, 20000, 25000, 30000, 45000, 49000, 50000]

    STRUCTURING_THRESHOLD = 10000

    def __init__(self, seed: Optional[int] = None):
        import random
        self._random = random.Random(seed)
        self._counter = 0

    def generate(
        self,
        from_account: str,
        to_account: str,
        seed_override: Optional[int] = None,
        inject_fraud: Optional[dict] = None,
    ) -> TransactionSchema:
        """Generate a single transaction entity"""
        if seed_override is not None:
            r = random.Random(seed_override)
        else:
            r = self._random

        self._counter += 1

        is_suspicious = r.random() < 0.05
        amount = 0.0

        if inject_fraud:
            is_suspicious = True
            fraud_type = inject_fraud.get("type", "layering")
            amount = inject_fraud.get("amount", r.choice(self.SUSPICIOUS_AMOUNTS))

            if fraud_type == "smurfing":
                amount = r.randint(8000, 9900)
            elif fraud_type == "structuring":
                amount = r.randint(9000, 9900)
            else:
                amount = r.choice(self.SUSPICIOUS_AMOUNTS)
        else:
            if is_suspicious:
                amount = r.choice(self.SUSPICIOUS_AMOUNTS)
            else:
                amount = r.choice(self.NORMAL_AMOUNTS)

        amount = round(amount + r.uniform(0, 99.99), 2)

        tx_type = r.choice([
            TransactionType.WIRE,
            TransactionType.ACH,
            TransactionType.CASH,
            TransactionType.CHECK,
        ])

        status = TransactionStatus.COMPLETED
        if r.random() < 0.02:
            status = TransactionStatus.FLAGGED
        elif r.random() < 0.01:
            status = TransactionStatus.PENDING

        timestamp = datetime.now() - timedelta(
            days=r.randint(0, 365),
            hours=r.randint(0, 23),
            minutes=r.randint(0, 59),
        )

        description = r.choice(self.DESCRIPTIONS)
        if is_suspicious:
            description = r.choice(self.SUSPICIOUS_DESCRIPTIONS)

        risk_score = round(r.uniform(0, 1), 4)
        if is_suspicious:
            risk_score = min(1.0, risk_score + 0.4)

        is_layering = inject_fraud and inject_fraud.get("type") == "layering"
        is_smurfing = inject_fraud and inject_fraud.get("type") == "smurfing"
        is_structuring = inject_fraud and inject_fraud.get("type") == "structuring"

        return TransactionSchema(
            id=f"TX-{self._counter:08d}",
            from_account=from_account,
            to_account=to_account,
            amount=amount,
            currency="USD",
            transaction_type=tx_type,
            status=status,
            timestamp=timestamp,
            description=description,
            reference=f"REF{r.randint(100000, 999999)}",
            is_suspicious=is_suspicious,
            risk_score=risk_score,
            is_layering=is_layering,
            is_smurfing=is_smurfing,
            is_structuring=is_structuring,
        )

    def generate_structuring_sequence(
        self,
        source_account: str,
        destination_account: str,
        num_transactions: int = 5,
    ) -> list:
        """Generate a structuring/smurfing sequence"""
        transactions = []
        for i in range(num_transactions):
            amount = random.Random(self._counter * 100 + i).randint(8000, 9900)
            tx = self.generate(
                from_account=source_account,
                to_account=destination_account,
                inject_fraud={"type": "structuring", "amount": float(amount)},
            )
            transactions.append(tx)
            self._counter += 1
        return transactions

    def generate_layering_sequence(
        self,
        chain: list,
    ) -> list:
        """Generate a multi-hop layering chain"""
        transactions = []
        for i in range(len(chain) - 1):
            tx = self.generate(
                from_account=chain[i],
                to_account=chain[i + 1],
                inject_fraud={"type": "layering"},
            )
            transactions.append(tx)
            self._counter += 1
        return transactions