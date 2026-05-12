"""
Account Generator - Bank and crypto account entities
"""
from typing import Optional
import random
from datetime import date

from ..schemas.account import AccountSchema, AccountType, AccountStatus


class AccountGenerator:
    """Generator for bank and crypto account entities"""

    def __init__(self, seed: Optional[int] = None):
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
        r = random.Random(seed_override) if seed_override else self._random
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