"""
Core schemas for 2_baseline_systems.
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Any


@dataclass
class GraphMetadata:
    person_count: int = 0
    company_count: int = 0
    account_count: int = 0
    address_count: int = 0
    device_count: int = 0
    transaction_count: int = 0
    edge_count: int = 0
    fraud_ring_count: int = 0
    graph_density: float = 0.0
    avg_degree: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RetrievalTrace:
    retrieved_chunks: list[dict] = field(default_factory=list)
    retrieval_depth: int = 0
    total_retrieved: int = 0
    cache_hits: int = 0
    retrieval_strategy: str = ""
    traversal_paths: list[dict] = field(default_factory=list)
    visited_nodes: list[str] = field(default_factory=list)
    traversed_edges: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TraversalPath:
    path: list[str] = field(default_factory=list)
    path_type: str = ""
    weight: float = 0.0
    hops: int = 0
    narrative: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PipelineResult:
    approach: str = ""
    question: str = ""
    answer: Optional[str] = None
    sources: list[dict] = field(default_factory=list)
    latency_ms: float = 0.0
    retrieval_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_estimate: float = 0.0
    model: str = ""
    error: Optional[str] = None
    retrieval_trace: Optional[RetrievalTrace] = None
    traversal_paths: list[TraversalPath] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        if d.get("retrieval_trace") is not None:
            d["retrieval_trace"] = self.retrieval_trace.to_dict()
        return d


@dataclass
class EntityMatchResult:
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    matched_entities: list[str] = field(default_factory=list)
    missed_entities: list[str] = field(default_factory=list)
    extra_entities: list[str] = field(default_factory=list)
    path_coverage: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class EvaluationResult:
    query_id: str = ""
    approach: str = ""
    llm_judge_score: float = 0.0
    entity_match: Optional[EntityMatchResult] = None
    accuracy: float = 0.0
    hallucination_score: float = 0.0
    completeness_score: float = 0.0
    tokens_used: int = 0
    total_cost: float = 0.0
    failure_reasons: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        if d.get("entity_match") is not None:
            d["entity_match"] = self.entity_match.to_dict()
        return d


@dataclass
class BenchmarkRun:
    run_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    config: dict = field(default_factory=dict)
    dataset_hash: str = ""
    profile: str = ""
    queries_loaded: int = 0
    queries_run: int = 0
    results: dict[str, list[dict]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d


@dataclass
class BenchmarkQuery:
    id: str = ""
    question: str = ""
    query_type: str = ""
    required_hops: int = 0
    tier: int = 0
    relevant_entities: list[str] = field(default_factory=list)
    relevant_paths: list[list[str]] = field(default_factory=list)
    fraud_ring_id: Optional[str] = None
    ground_truth_entities: list[str] = field(default_factory=list)
    ground_truth_paths: list[str] = field(default_factory=list)
    complexity_score: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Document:
    id: str = ""
    text: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ShadowDataset:
    persons: list[dict] = field(default_factory=list)
    companies: list[dict] = field(default_factory=list)
    accounts: list[dict] = field(default_factory=list)
    addresses: list[dict] = field(default_factory=list)
    devices: list[dict] = field(default_factory=list)
    transactions: list[dict] = field(default_factory=list)
    edges: list[dict] = field(default_factory=list)
    fraud_rings: list[dict] = field(default_factory=list)
    graph_metadata: Optional[GraphMetadata] = None
    source_dir: str = ""

    def get_entity_by_id(self, entity_id: str) -> Optional[dict]:
        prefix = entity_id.split("-")[0] + "-" if "-" in entity_id else ""
        collection_map = {
            "P-": self.persons,
            "C-": self.companies,
            "A-": self.accounts,
            "ADDR-": self.addresses,
            "D-": self.devices,
            "TX-": self.transactions,
            "T-": self.transactions,
        }
        collection = collection_map.get(prefix, [])
        for entity in collection:
            if entity.get("id") == entity_id:
                return entity
        return None

    def get_edges_for_entity(self, entity_id: str) -> list[dict]:
        if not hasattr(self, "_edge_index") or self._edge_index is None:
            self._edge_index = {}
            for e in self.edges:
                fid = e.get("from_id")
                tid = e.get("to_id")
                if fid:
                    self._edge_index.setdefault(fid, []).append(e)
                if tid:
                    self._edge_index.setdefault(tid, []).append(e)
        return self._edge_index.get(entity_id, [])

    def get_transaction_chain(self, from_id: str, to_id: str) -> list[dict]:
        chain = []
        visited = set()
        queue = [from_id]
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            for edge in self.edges:
                if edge.get("from_id") == current and edge.get("relationship") == "TRANSFERRED_TO":
                    chain.append(edge)
                    if edge.get("to_id") == to_id:
                        return chain
                    queue.append(edge.get("to_id"))
        return chain

    def to_graph_summary(self) -> dict:
        return {
            "total_entities": sum([
                len(self.persons), len(self.companies), len(self.accounts),
                len(self.addresses), len(self.devices), len(self.transactions)
            ]),
            "total_edges": len(self.edges),
            "fraud_rings": len(self.fraud_rings),
            "persons": len(self.persons),
            "companies": len(self.companies),
            "accounts": len(self.accounts),
            "addresses": len(self.addresses),
            "devices": len(self.devices),
            "transactions": len(self.transactions),
        }