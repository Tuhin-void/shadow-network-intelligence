"""
Generation Profiles - Configuration profiles for different scales
"""
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum


class GenerationProfile(Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    HACKATHON_DEFAULT = "hackathon_default"


@dataclass
class GenerationConfig:
    """Configuration for data generation"""

    profile: GenerationProfile = GenerationProfile.HACKATHON_DEFAULT
    seed: int = 42

    # Entity counts
    person_count: int = 6000
    company_count: int = 5000
    account_count: int = 10000
    address_count: int = 4000
    device_count: int = 3000

    # Transaction count
    transaction_count: int = 50000

    # Edge target
    edge_target: int = 500000

    # Fraud configuration
    fraud_ring_count: int = 15
    fraud_density: float = 0.03

    # Normal/suspicious/fraud distribution
    normal_ratio: float = 0.85
    suspicious_ratio: float = 0.12
    fraud_ratio: float = 0.03

    # Document generation
    document_count: int = 5000
    document_per_entity: float = 0.2

    # Token targets
    min_tokens: int = 100000
    max_tokens: int = 500000

    # Offshore/shell ratios
    offshore_ratio: float = 0.12
    shell_ratio: float = 0.10

    # PEP/sanctions
    pep_ratio: float = 0.05
    sanctioned_ratio: float = 0.02

    # Vector noise
    noise_ratio: float = 0.15
    semantic_trap_count: int = 100

    # Temporal
    temporal_window_days: int = 365
    burst_ratio: float = 0.05

    # Output
    output_dir: str = "./outputs"

    # Export formats
    export_tigergraph: bool = True
    export_csv: bool = True
    export_json: bool = True
    export_chromadb: bool = True

    def __post_init__(self):
        if isinstance(self.profile, str):
            self.profile = GenerationProfile(self.profile)


PROFILES: Dict[str, GenerationConfig] = {
    "small": GenerationConfig(
        profile=GenerationProfile.SMALL,
        person_count=300,
        company_count=200,
        account_count=400,
        address_count=100,
        device_count=150,
        transaction_count=5000,
        edge_target=15000,
        fraud_ring_count=3,
        document_count=500,
        min_tokens=10000,
        max_tokens=50000,
    ),
    "medium": GenerationConfig(
        profile=GenerationProfile.MEDIUM,
        person_count=3000,
        company_count=2000,
        account_count=4000,
        address_count=1000,
        device_count=1500,
        transaction_count=50000,
        edge_target=250000,
        fraud_ring_count=8,
        document_count=3000,
        min_tokens=100000,
        max_tokens=500000,
    ),
    "large": GenerationConfig(
        profile=GenerationProfile.LARGE,
        person_count=30000,
        company_count=20000,
        account_count=40000,
        address_count=10000,
        device_count=15000,
        transaction_count=500000,
        edge_target=1500000,
        fraud_ring_count=30,
        document_count=30000,
        min_tokens=1000000,
        max_tokens=5000000,
    ),
    "hackathon_default": GenerationConfig(
        profile=GenerationProfile.HACKATHON_DEFAULT,
        person_count=6000,
        company_count=5000,
        account_count=10000,
        address_count=4000,
        device_count=3000,
        transaction_count=50000,
        edge_target=500000,
        fraud_ring_count=15,
        document_count=5000,
        min_tokens=100000,
        max_tokens=500000,
    ),
}


def get_profile(name: str) -> GenerationConfig:
    """Get a generation profile by name"""
    return PROFILES.get(name, PROFILES["hackathon_default"])