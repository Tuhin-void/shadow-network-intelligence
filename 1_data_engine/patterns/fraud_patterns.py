"""
Fraud Patterns - Concrete implementations of fraud detection patterns
"""

PATTERNS = {
    "address_collision": {
        "name": "Address Collision",
        "description": "Multiple entities sharing the same physical address",
        "severity": "HIGH",
        "indicators": [
            "Same address used by multiple persons",
            "Same address used by multiple companies",
            "Cross-entity address sharing (person + company)",
        ],
        "threshold": 3,
        "gsql_query": "MATCH (a1:Address)<-[:LOCATED_AT]-(e1) WHERE e1.address_id = a1.id WITH a1, collect(e1) as entities WHERE size(entities) >= {threshold} RETURN a1, entities",
        "risk_weight": 0.25,
    },
    "shell_company_ring": {
        "name": "Shell Company Ring",
        "description": "Circular ownership of shell companies for layering",
        "severity": "CRITICAL",
        "indicators": [
            "Companies owned by other companies",
            "Circular ownership chains",
            "Minimal operational activity",
            "Same officers across multiple entities",
        ],
        "max_hops": 3,
        "gsql_query": "MATCH path=(c1:Company)-[:OWNS*1..{max_hops}]->(c2:Company) WHERE c1 <> c2 RETURN path",
        "risk_weight": 0.40,
    },
    "laundering_chain": {
        "name": "Laundering Chain",
        "description": "Layered fund transfers through multiple accounts",
        "severity": "CRITICAL",
        "indicators": [
            "Multiple hops between accounts",
            "Increasing transaction fragmentation",
            "Timing patterns (same day transfers)",
            "Round amounts",
        ],
        "min_hops": 3,
        "max_amount_variance": 0.05,
        "gsql_query": "MATCH path=(a1:BankAccount)-[:TRANSFERRED_TO*3..]->(a2:BankAccount) RETURN path",
        "risk_weight": 0.45,
    },
    "offshore_hop": {
        "name": "Offshore Jurisdiction Hop",
        "description": "Transfers to or from offshore jurisdictions",
        "severity": "HIGH",
        "indicators": [
            "Account in offshore jurisdiction",
            "Transactions to high-risk countries",
            "Layered through offshore intermediaries",
        ],
        "offshore_codes": ["BS", "KY", "CH", "LU", "VG", "PA"],
        "gsql_query": "MATCH (a:BankAccount)-[:LOCATED_AT]->(c:Country) WHERE c.code IN {offshore_codes} WITH a MATCH (a)-[:TRANSFERRED_TO*1..2]->(other:BankAccount) RETURN a, other",
        "risk_weight": 0.30,
    },
    "rapid_transfer_loop": {
        "name": "Rapid Transfer Loop",
        "description": "Fast-cycling transfers between accounts",
        "severity": "HIGH",
        "indicators": [
            "Multiple transfers within short timeframe",
            "Transfer in, immediate transfer out",
            "Similar amounts across transfers",
            "Net balance near zero",
        ],
        "min_transfers": 5,
        "time_window_hours": 1,
        "gsql_query": "MATCH (a1:BankAccount)-[t:TRANSFERRED_TO]->(a2:BankAccount) WITH a1, a2, t, count(*) as transfer_count WHERE transfer_count >= {min_transfers} RETURN a1, a2, transfer_count",
        "risk_weight": 0.35,
    },
}


def get_pattern(name: str) -> dict:
    """Get pattern configuration by name"""
    return PATTERNS.get(name)


def get_all_patterns() -> dict:
    """Get all patterns"""
    return PATTERNS


def get_patterns_by_severity(severity: str) -> dict:
    """Filter patterns by severity"""
    return {k: v for k, v in PATTERNS.items() if v.get("severity") == severity}


def get_pattern_gsql(name: str) -> str:
    """Get GSQL query template for pattern"""
    pattern = PATTERNS.get(name)
    return pattern.get("gsql_query", "") if pattern else ""