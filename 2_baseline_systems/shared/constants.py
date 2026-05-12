"""
Shared constants for 2_baseline_systems.
Re-exports from shared/ and benchmark-specific constants.
"""
from shared.constants.entity_types import ENTITY_TYPES
from shared.constants.fraud_thresholds import FRAUD_THRESHOLDS
try:
    from shared.constants.risk_weights import WEIGHTS as RISK_WEIGHTS, THRESHOLDS, RISK_SCORES
except ImportError:
    RISK_WEIGHTS = {}
    THRESHOLDS = {}
    RISK_SCORES = {}

BENCHMARK_TIERS = {
    1: {
        "name": "Direct Lookup",
        "description": "Single-hop, entity ID known, direct attribute lookup",
        "expected_hops": 1,
        "expected_graphrag_advantage_tokens": 0.10,
        "expected_graphrag_advantage_accuracy": 0.05,
    },
    2: {
        "name": "Semantic Synthesis",
        "description": "Cross-document retrieval, 1-2 hops, entity type known",
        "expected_hops": 2,
        "expected_graphrag_advantage_tokens": 0.25,
        "expected_graphrag_advantage_accuracy": 0.10,
    },
    3: {
        "name": "Multi-Hop Reasoning",
        "description": "Shell ownership discovery, laundering path reconstruction, 2-3 hops",
        "expected_hops": 3,
        "expected_graphrag_advantage_tokens": 0.50,
        "expected_graphrag_advantage_accuracy": 0.20,
    },
    4: {
        "name": "Distributed Evidence",
        "description": "Temporal fraud reconstruction, 3-4 hops, distributed evidence",
        "expected_hops": 4,
        "expected_graphrag_advantage_tokens": 0.65,
        "expected_graphrag_advantage_accuracy": 0.30,
    },
    5: {
        "name": "Adversarial Retrieval",
        "description": "Fragmented intelligence reconstruction, 4+ hops, adversarial cases",
        "expected_hops": 5,
        "expected_graphrag_advantage_tokens": 0.75,
        "expected_graphrag_advantage_accuracy": 0.40,
    },
}

EVALUATION_WEIGHTS = {
    "llm_judge": 0.5,
    "entity_match": 0.3,
    "token_efficiency": 0.1,
    "latency": 0.1,
}

PIPELINE_APPROACHES = ["pure_llm", "vector_rag", "graphrag"]

RETRIEVAL_FAILURE_TYPES = {
    "semantic_confusion": "Vector retrieval confused by similar entity names or terms",
    "context_pollution": "Too many irrelevant chunks retrieved, diluting signal",
    "missed_topology": "Failed to capture graph structure (ownership chains, shared addresses)",
    "hidden_relationship": "Missed indirect relationship path through intermediate entities",
    "fragmented_evidence": "Evidence scattered across non-contiguous chunks, lost in retrieval",
    "hallucination": "LLM invented entities or facts not present in retrieved context",
    "context_overload": "Retrieved context exceeds LLM context window capacity",
    "retrieval_irrelevance": "Retrieved chunks do not match query intent",
}

PROVIDER_PRICING = {
    "openai": {
        "gpt-4o-mini": {"input": 0.15 / 1e6, "output": 0.60 / 1e6},
        "gpt-4o": {"input": 2.50 / 1e6, "output": 10.00 / 1e6},
        "gpt-4-turbo": {"input": 10.00 / 1e6, "output": 30.00 / 1e6},
        "text-embedding-3-small": {"input": 0.02 / 1e6},
        "text-embedding-3-large": {"input": 0.13 / 1e6},
    },
    "anthropic": {
        "claude-3-haiku": {"input": 0.80 / 1e6, "output": 4.00 / 1e6},
        "claude-3-sonnet": {"input": 3.00 / 1e6, "output": 15.00 / 1e6},
        "claude-3-5-sonnet": {"input": 3.00 / 1e6, "output": 15.00 / 1e6},
    },
}

CHUNK_STRATEGIES = ["recursive", "semantic", "graph_aware", "sentence"]

ENTITY_TYPE_MAP = {
    "P-": "Person",
    "C-": "Company",
    "A-": "Account",
    "ADDR-": "Address",
    "D-": "Device",
    "TX-": "Transaction",
    "FR-": "FraudRing",
    "T-": "Transaction",
}

DOC_TYPE_MAP = {
    "entity_profile": "entity_profile",
    "transaction": "transaction",
    "authored": "authored",
}