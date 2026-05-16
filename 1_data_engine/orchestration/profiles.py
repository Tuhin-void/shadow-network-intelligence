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
    # Additive: a profile tuned for benchmark-grade GraphRAG superiority demos.
    # Heavier topology density, larger document corpus, more fraud rings.
    # Does NOT change the generation logic — only profile knobs.
    BENCHMARK_DENSE = "benchmark_dense"


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
        # Enough rings to make ring-identification queries visibly answerable
        # in the demo without bloating the small profile.
        fraud_ring_count=15,
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
    # benchmark_dense — opt-in profile used by adversarial benchmarks and
    # GraphRAG-superiority demos. Tuned for:
    #   • 1M+ token corpus  (document_count + per-entity ratio)
    #   • Higher fraud ring count and density  → more multi-hop traversal opportunities
    #   • Lower address/device counts relative to persons  → forces shared-infrastructure
    #     reuse, which is exactly what SHARES_ADDRESS_WITH / SHARES_DEVICE_WITH need
    #   • More vector noise + semantic traps  → exposes VectorRAG fragility
    #
    # Uses the existing generators verbatim — only the knob values are different.
    "benchmark_dense": GenerationConfig(
        profile=GenerationProfile.BENCHMARK_DENSE,
        person_count=12000,
        company_count=8000,
        account_count=20000,
        address_count=4500,         # intentionally sparse → forces collisions
        device_count=3500,          # intentionally sparse → forces SHARES_DEVICE_WITH
        transaction_count=120000,
        edge_target=1_400_000,
        fraud_ring_count=40,
        fraud_density=0.05,         # 5% vs 3% default → denser fraud topology
        document_count=18000,
        document_per_entity=0.35,
        min_tokens=1_200_000,
        max_tokens=2_400_000,
        offshore_ratio=0.15,
        shell_ratio=0.14,
        pep_ratio=0.07,
        sanctioned_ratio=0.04,
        noise_ratio=0.20,            # more noise → harder for VectorRAG
        semantic_trap_count=240,
        burst_ratio=0.08,
    ),
}


def get_profile(name: str) -> GenerationConfig:
    """Get a generation profile by name"""
    return PROFILES.get(name, PROFILES["hackathon_default"])