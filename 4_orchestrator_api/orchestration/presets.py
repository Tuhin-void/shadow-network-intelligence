"""
Demo presets — curated investigations that demonstrate GraphRAG's
structural-intelligence superiority on contractually known queries.

Each preset is a (key, title, query, top_k, depth) tuple. The preset key
is a stable demo-time identifier the operator can fire from the UI or CLI.

These match the adversarial-benchmark queries so the demo and the
benchmark use the same reproducible inputs.
"""
from __future__ import annotations

from typing import Optional

# Note: queries can be edited freely; the keys are the stable contract.
DEMO_PRESETS: list[dict] = [
    {
        "key":   "ring-identification",
        "title": "Identify members of fraud ring FR-002",
        "query": "Identify all entities participating in fraud ring FR-002, including indirect members reachable through ring membership.",
        "top_k": 5, "depth": 2,
        "showcases": ["reverse-edge traversal", "ring-member promotion", "tg_ring_members"],
    },
    {
        "key":   "hidden-beneficial-owner",
        "title": "Hidden beneficial owners",
        "query": "Who are the hidden beneficial owners of companies in the laundering network? Surface persons that benefit from companies without explicit ownership.",
        "top_k": 5, "depth": 2,
        "showcases": ["BENEFITS_FROM traversal", "topology-aware reranking"],
    },
    {
        "key":   "shared-address-collusion",
        "title": "Co-located collusion network",
        "query": "Find pairs of persons that share addresses with shell-company controllers. These co-located individuals are likely co-conspirators.",
        "top_k": 5, "depth": 2,
        "showcases": ["SHARES_ADDRESS_WITH", "multi-hop join"],
    },
    {
        "key":   "shared-device-cluster",
        "title": "Shared-device mule cluster",
        "query": "Identify persons sharing devices — a strong coordination signal. Which person clusters reuse the same device infrastructure?",
        "top_k": 5, "depth": 2,
        "showcases": ["SHARES_DEVICE_WITH", "hidden coordination"],
    },
    {
        "key":   "layering-chain",
        "title": "Multi-hop laundering chain",
        "query": "Trace a layering chain of 5+ accounts moving funds sequentially through a fraud ring. Output the chain in order.",
        "top_k": 5, "depth": 3,
        "showcases": ["TRANSFERRED_TO multi-hop", "TRANSACTION_MEMBER_OF_RING"],
    },
    {
        "key":   "funnel-pattern",
        "title": "Funnel-account pattern",
        "query": "Find a funnel-account pattern where 5+ source accounts feed a single destination account. List the destination and its sources.",
        "top_k": 5, "depth": 2,
        "showcases": ["fan-in degree analysis"],
    },
    {
        "key":   "circular-ownership",
        "title": "Circular ownership ring",
        "query": "Identify a circular ownership ring — a cycle of companies where each owns the next. List the cycle in order.",
        "top_k": 5, "depth": 3,
        "showcases": ["cycle detection via OWNS"],
    },
    {
        "key":   "hidden-controller",
        "title": "Hidden controller of shell-company cluster",
        "query": "Find the hidden controller of a shell-company cluster — a person who owns or benefits from multiple companies that share addresses.",
        "top_k": 5, "depth": 3,
        "showcases": ["3-hop join: Person → Company → Address ← Company"],
    },
]


def get_preset(key: str) -> Optional[dict]:
    for p in DEMO_PRESETS:
        if p["key"] == key:
            return p
    return None


def list_presets() -> list[dict]:
    return [
        {k: v for k, v in p.items() if k in ("key", "title", "showcases")}
        for p in DEMO_PRESETS
    ]
