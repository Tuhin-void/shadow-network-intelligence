"""
Difficulty tier classification for benchmark queries.
"""
from ..shared.schemas import BenchmarkQuery

TIER_DEFINITIONS = {
    1: {
        "name": "Direct Lookup",
        "description": "Single-hop, entity ID known, direct attribute lookup",
        "expected_hops": 1,
        "expected_graphrag_token_advantage": 0.10,
        "expected_graphrag_accuracy_advantage": 0.05,
        "example": "What is the risk score of P-000001?",
    },
    2: {
        "name": "Semantic Synthesis",
        "description": "Cross-document retrieval, 1-2 hops, entity type known",
        "expected_hops": 2,
        "expected_graphrag_token_advantage": 0.25,
        "expected_graphrag_accuracy_advantage": 0.10,
        "example": "Find all offshore companies in the dataset",
    },
    3: {
        "name": "Multi-Hop Reasoning",
        "description": "Shell ownership discovery, laundering path reconstruction, 2-3 hops",
        "expected_hops": 3,
        "expected_graphrag_token_advantage": 0.50,
        "expected_graphrag_accuracy_advantage": 0.20,
        "example": "Trace the laundering chain from P-000001 to offshore accounts",
    },
    4: {
        "name": "Distributed Evidence",
        "description": "Temporal fraud reconstruction, 3-4 hops, distributed evidence",
        "expected_hops": 4,
        "expected_graphrag_token_advantage": 0.65,
        "expected_graphrag_accuracy_advantage": 0.30,
        "example": "Reconstruct the full fraud ring FR-001 structure",
    },
    5: {
        "name": "Adversarial Retrieval",
        "description": "Fragmented intelligence reconstruction, 4+ hops, adversarial cases",
        "expected_hops": 5,
        "expected_graphrag_token_advantage": 0.75,
        "expected_graphrag_accuracy_advantage": 0.40,
        "example": "Find all entities that transferred funds through shell companies to offshore accounts within 7 days",
    },
}


class DifficultyTierClassifier:
    def classify(self, query: BenchmarkQuery) -> int:
        if query.tier > 0:
            return query.tier

        complexity = query.complexity_score
        hops = query.required_hops
        qtype = query.query_type

        if qtype == "entity_resolution" and hops <= 1 and complexity < 0.3:
            return 1
        if qtype in ("semantic_synthesis", "entity_resolution") and hops <= 2 and complexity < 0.5:
            return 2
        if qtype in ("traversal", "path_finding") and 2 <= hops <= 3 and complexity < 0.7:
            return 3
        if qtype in ("fraud_ring_identification", "path_finding") and hops >= 3 and complexity >= 0.7:
            return 4
        if complexity >= 0.85 or hops >= 5:
            return 5
        if complexity >= 0.6:
            return 3
        if complexity >= 0.4:
            return 2
        return 1

    def get_tier_info(self, tier: int) -> dict:
        return TIER_DEFINITIONS.get(tier, TIER_DEFINITIONS[1])

    def get_expected_advantage(self, tier: int) -> dict:
        info = self.get_tier_info(tier)
        return {
            "tier": tier,
            "name": info["name"],
            "expected_graphrag_token_reduction_pct": info["expected_graphrag_token_advantage"] * 100,
            "expected_graphrag_accuracy_delta": info["expected_graphrag_accuracy_advantage"],
        }

    def summarize(self, queries: list[BenchmarkQuery]) -> dict:
        tier_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for q in queries:
            tier = self.classify(q)
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
        return {
            "total": len(queries),
            "by_tier": tier_counts,
            "tier_info": {t: self.get_tier_info(t) for t in range(1, 6)},
        }