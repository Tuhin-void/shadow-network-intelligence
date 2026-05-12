"""
Shadow Network Intelligence - Benchmark Data Loader

Loads benchmark questions and ground truth. Prefers the sample dataset's
benchmark_questions.json + fraud_ring_ground_truth.json. Falls back to a
small hardcoded set if the dataset is unavailable.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .config import DATASET_DIR

logger = logging.getLogger(__name__)


FALLBACK_QUESTIONS: list[dict[str, Any]] = [
    {
        "id": "Q001",
        "category": "pattern_detection",
        "question": "Detect all circular transaction patterns in the recent transactions.",
        "expected_patterns": ["circular"],
    },
    {
        "id": "Q002",
        "category": "entity_search",
        "question": "Find all companies sharing an address.",
        "expected_patterns": ["shell_company", "address_collision"],
    },
    {
        "id": "Q003",
        "category": "risk_scoring",
        "question": "What is the risk score for account A-000001?",
        "expected_risk_min": 0.5,
    },
    {
        "id": "Q004",
        "category": "network_analysis",
        "question": "Who owns ShadowCorp Holdings?",
        "expected_entities": ["Person"],
    },
]


class BenchmarkDataLoader:
    """Loads and manages benchmark test data."""

    def __init__(self, dataset_dir: Path | None = None):
        self.dataset_dir = Path(dataset_dir) if dataset_dir else DATASET_DIR
        self.questions: list[dict[str, Any]] = self._load_questions()
        self.fraud_ring: dict[str, Any] = self._load_fraud_ring()

    def _load_questions(self) -> list[dict[str, Any]]:
        path = self.dataset_dir / "benchmarks" / "benchmark_questions.json"
        if path.exists():
            with path.open() as f:
                raw = json.load(f)
            for i, q in enumerate(raw, start=1):
                q.setdefault("id", f"Q{i:03d}")
            return raw
        logger.warning("Sample benchmark questions not found at %s; using fallback set", path)
        return FALLBACK_QUESTIONS

    def _load_fraud_ring(self) -> dict[str, Any]:
        path = self.dataset_dir / "benchmarks" / "fraud_ring_ground_truth.json"
        if path.exists():
            with path.open() as f:
                return json.load(f)
        return {}

    def get_questions(self, category: str | None = None) -> list[dict[str, Any]]:
        if category:
            return [q for q in self.questions if q.get("category") == category]
        return self.questions

    def load_custom_questions(self, filepath: str | Path) -> list[dict[str, Any]]:
        path = Path(filepath)
        if not path.exists():
            logger.warning("Custom questions file not found: %s", filepath)
            return []
        try:
            with path.open() as f:
                data = json.load(f)
            for i, q in enumerate(data, start=1):
                q.setdefault("id", f"CUSTOM_{i:03d}")
            return data
        except Exception as exc:
            logger.error("Failed to load questions: %s", exc)
            return []

    def evaluate_against_ground_truth(self, answer_text: str) -> dict[str, Any]:
        """
        Tiny rubric: did the answer mention the fraud-ring entities or
        the shared address? Used as a coarse signal, not real accuracy.
        """
        if not self.fraud_ring or not answer_text:
            return {"score": None, "matched_entities": [], "matched_address": False}

        text = answer_text.lower()
        entities = self.fraud_ring.get("entities", [])
        matched = [e for e in entities if e.lower() in text]
        shared_addr = self.fraud_ring.get("shared_address", "")
        addr_match = bool(shared_addr) and shared_addr.lower() in text

        score = (len(matched) + (1 if addr_match else 0)) / (len(entities) + 1)
        return {
            "score": round(score, 3),
            "matched_entities": matched,
            "matched_address": addr_match,
        }
