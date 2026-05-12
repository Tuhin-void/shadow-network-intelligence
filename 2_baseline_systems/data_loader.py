"""
Loads the shadow_network_sample_dataset/ into a single in-memory dict.

Pure read-only. Does not mutate or write anything inside the dataset folder.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import DATASET_DIR


@dataclass
class ShadowDataset:
    persons: list[dict[str, Any]] = field(default_factory=list)
    companies: list[dict[str, Any]] = field(default_factory=list)
    accounts: list[dict[str, Any]] = field(default_factory=list)
    addresses: list[dict[str, Any]] = field(default_factory=list)
    transactions: list[dict[str, Any]] = field(default_factory=list)

    owns_edges: list[dict[str, Any]] = field(default_factory=list)
    has_account_edges: list[dict[str, Any]] = field(default_factory=list)
    located_at_edges: list[dict[str, Any]] = field(default_factory=list)

    semantic_documents: list[dict[str, Any]] = field(default_factory=list)
    benchmark_questions: list[dict[str, Any]] = field(default_factory=list)
    fraud_ring_ground_truth: dict[str, Any] = field(default_factory=dict)

    def entity_index(self) -> dict[str, dict[str, Any]]:
        idx: dict[str, dict[str, Any]] = {}
        for row in self.persons:
            idx[row["person_id"]] = {**row, "_type": "Person"}
        for row in self.companies:
            idx[row["company_id"]] = {**row, "_type": "Company"}
        for row in self.accounts:
            idx[row["account_id"]] = {**row, "_type": "Account"}
        for row in self.addresses:
            idx[row["address_id"]] = {**row, "_type": "Address"}
        return idx

    def stats(self) -> dict[str, int]:
        return {
            "persons": len(self.persons),
            "companies": len(self.companies),
            "accounts": len(self.accounts),
            "addresses": len(self.addresses),
            "transactions": len(self.transactions),
            "owns_edges": len(self.owns_edges),
            "has_account_edges": len(self.has_account_edges),
            "located_at_edges": len(self.located_at_edges),
            "semantic_documents": len(self.semantic_documents),
            "benchmark_questions": len(self.benchmark_questions),
        }


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open() as f:
        return json.load(f)


def _coerce_numbers(rows: list[dict[str, Any]], numeric_cols: tuple[str, ...]) -> None:
    for row in rows:
        for col in numeric_cols:
            if col in row and row[col] not in (None, ""):
                try:
                    row[col] = float(row[col]) if "." in str(row[col]) else int(row[col])
                except (TypeError, ValueError):
                    pass


def load_dataset(dataset_dir: Path | None = None) -> ShadowDataset:
    root = Path(dataset_dir) if dataset_dir else DATASET_DIR
    if not root.exists():
        raise FileNotFoundError(
            f"Sample dataset not found at {root}. "
            f"Set SHADOW_DATASET_DIR or place data at the default location."
        )

    ds = ShadowDataset(
        persons=_read_csv(root / "entities" / "persons.csv"),
        companies=_read_csv(root / "entities" / "companies.csv"),
        accounts=_read_csv(root / "entities" / "accounts.csv"),
        addresses=_read_csv(root / "entities" / "addresses.csv"),
        transactions=_read_csv(root / "entities" / "transactions.csv"),
        owns_edges=_read_csv(root / "edges" / "owns_edges.csv"),
        has_account_edges=_read_csv(root / "edges" / "has_account_edges.csv"),
        located_at_edges=_read_csv(root / "edges" / "located_at_edges.csv"),
        semantic_documents=_read_json(root / "documents" / "semantic_documents.json") or [],
        benchmark_questions=_read_json(root / "benchmarks" / "benchmark_questions.json") or [],
        fraud_ring_ground_truth=_read_json(root / "benchmarks" / "fraud_ring_ground_truth.json") or {},
    )

    _coerce_numbers(ds.persons, ("risk_score",))
    _coerce_numbers(ds.companies, ("risk_score",))
    _coerce_numbers(ds.accounts, ("risk_score", "balance"))
    _coerce_numbers(ds.transactions, ("risk_score", "amount"))
    _coerce_numbers(ds.owns_edges, ("ownership_percent",))

    return ds


if __name__ == "__main__":
    ds = load_dataset()
    print(json.dumps(ds.stats(), indent=2))
