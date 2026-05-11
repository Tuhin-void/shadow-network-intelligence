"""
Shadow Network Intelligence - Pattern Definition
Fraud pattern configurations
"""
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

class PatternType(Enum):
    CIRCULAR = "circular"
    LAYERED = "layered"
    SHELL_COMPANY = "shell_company"
    STRUCTURING = "structuring"
    OFFSHORE_HOP = "offshore_hop"
    RAPID_LOOP = "rapid_loop"

@dataclass
class PatternConfig:
    name: str
    type: PatternType
    thresholds: Dict[str, float]
    indicators: List[str]
    severity: str
    description: str

PATTERN_CONFIGS = {
    "address_collision": PatternConfig(
        name="Address Collision",
        type=PatternType.SHELL_COMPANY,
        thresholds={
            "min_entities": 3,
            "max_distance": 0.0
        },
        indicators=[
            "shared_address",
            "same_registration_date",
            "common_owners"
        ],
        severity="MEDIUM",
        description="Multiple entities share the same address"
    ),
    "shell_company_ring": PatternConfig(
        name="Shell Company Ring",
        type=PatternType.SHELL_COMPANY,
        thresholds={
            "min_companies": 3,
            "min_transactions": 10,
            "max_age_days": 365
        },
        indicators=[
            "shell_indicator",
            "minimal_employees",
            "frequentOwnership_changes",
            "circular_payments"
        ],
        severity="HIGH",
        description="Network of shell companies used for layering"
    ),
    "laundering_chain": PatternConfig(
        name="Laundering Chain",
        type=PatternType.LAYERED,
        thresholds={
            "min_hops": 3,
            "max_amount": 1000000.0
        },
        indicators=[
            "layered_transactions",
            "offshore_entities",
            "round_amounts"
        ],
        severity="CRITICAL",
        description="Multi-hop transaction chain for money laundering"
    ),
    "offshore_hop": PatternConfig(
        name="Offshore Hop",
        type=PatternType.OFFSHORE_HOP,
        thresholds={
            "min_hops": 2,
            "jurisdiction_risk_min": 0.7
        },
        indicators=[
            "offshore_jurisdiction",
            "unusual_route",
            "tax_haven_indicator"
        ],
        severity="HIGH",
        description="Transactions routed through offshore jurisdictions"
    ),
    "rapid_transfer_loop": PatternConfig(
        name="Rapid Transfer Loop",
        type=PatternType.RAPID_LOOP,
        thresholds={
            "min_transfers": 5,
            "time_window_hours": 24,
            "circularity_threshold": 0.8
        },
        indicators=[
            "high_frequency",
            "circular_flow",
            "same_day_layering"
        ],
        severity="CRITICAL",
        description="Rapid circular transfers to obscure funds"
    ),
    "structuring": PatternConfig(
        name="Structuring / Smurfing",
        type=PatternType.STRUCTURING,
        thresholds={
            "threshold": 10000.0,
            "lookback_days": 30,
            "min_transactions": 3
        },
        indicators=[
            "sub_threshold_amounts",
            "frequent_deposits",
            "same_day_multiple"
        ],
        severity="MEDIUM",
        description="Breaking transactions to avoid CTR reporting"
    )
}

def get_pattern_config(pattern_name: str) -> Optional[PatternConfig]:
    """Get pattern configuration by name"""
    return PATTERN_CONFIGS.get(pattern_name)

def get_all_patterns() -> List[PatternConfig]:
    """Get all pattern configurations"""
    return list(PATTERN_CONFIGS.values())

def get_patterns_by_severity(severity: str) -> List[PatternConfig]:
    """Get patterns filtered by severity"""
    return [p for p in PATTERN_CONFIGS.values() if p.severity == severity]

def get_patterns_by_type(pattern_type: PatternType) -> List[PatternConfig]:
    """Get patterns filtered by type"""
    return [p for p in PATTERN_CONFIGS.values() if p.type == pattern_type]