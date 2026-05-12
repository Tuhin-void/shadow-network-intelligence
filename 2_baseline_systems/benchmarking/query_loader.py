"""
Query loader - loads benchmark queries from 1_data_engine fraud rings.
"""
import logging
import random
from typing import Optional
from ..shared.schemas import ShadowDataset, BenchmarkQuery
from ..shared.data_loader import AdaptiveDataLoader

logger = logging.getLogger(__name__)


class QueryLoader:
    def __init__(self, data_loader: AdaptiveDataLoader):
        self.data_loader = data_loader

    def load_queries(
        self,
        tier: Optional[int] = None,
        max_queries: Optional[int] = None,
        seed: int = 42,
    ) -> list[BenchmarkQuery]:
        dataset = self.data_loader.load()
        queries = self._generate_from_fraud_rings(dataset, seed)
        queries.extend(self._generate_synthetic_queries(dataset, seed))

        if tier is not None:
            queries = [q for q in queries if q.tier == tier]

        if max_queries:
            queries = queries[:max_queries]

        logger.info(f"Loaded {len(queries)} benchmark queries" + (f" (tier {tier})" if tier else ""))
        return queries

    def _generate_from_fraud_rings(self, dataset: ShadowDataset, seed: int) -> list[BenchmarkQuery]:
        queries = []
        r = random.Random(seed)

        for ring in dataset.fraud_rings:
            ring_id = ring.get("id", "unknown")
            ring_type = ring.get("type", ring.get("ring_type", "UNKNOWN"))
            severity = ring.get("severity", "MEDIUM")
            entities = ring.get("entities", [])
            key_entities = ring.get("key_entities", [])
            paths = ring.get("traversal_paths", [])

            if not entities and not key_entities:
                continue

            complexity = 0.5 + len(entities) * 0.02 + len(paths) * 0.05
            tier = self._classify_tier(ring_type, complexity, len(entities))

            if entities:
                e = r.choice(entities)
                queries.append(BenchmarkQuery(
                    id=f"Q-FR-{ring_id}-TRAVERSAL",
                    question=f"Find all entities connected to {e} within the fraud ring {ring_id}",
                    query_type="traversal",
                    required_hops=2,
                    tier=tier,
                    relevant_entities=entities,
                    relevant_paths=paths[:5],
                    fraud_ring_id=ring_id,
                    ground_truth_entities=entities,
                    ground_truth_paths=[str(p) if isinstance(p, list) else p for p in paths],
                    complexity_score=min(1.0, complexity),
                ))

            if key_entities:
                e = r.choice(key_entities)
                queries.append(BenchmarkQuery(
                    id=f"Q-FR-{ring_id}-IDENTIFY",
                    question=f"Identify the fraud ring containing {e}",
                    query_type="fraud_ring_identification",
                    required_hops=3,
                    tier=tier,
                    relevant_entities=[e],
                    relevant_paths=paths[:3],
                    fraud_ring_id=ring_id,
                    ground_truth_entities=entities,
                    ground_truth_paths=[str(p) if isinstance(p, list) else p for p in paths],
                    complexity_score=min(1.0, complexity + 0.1),
                ))

            if paths and len(paths) > 1:
                p = r.choice(paths)
                if isinstance(p, list) and len(p) >= 2:
                    queries.append(BenchmarkQuery(
                        id=f"Q-FR-{ring_id}-PATH",
                        question=f"Trace the fund flow from {p[0]} to {p[-1]}",
                        query_type="path_finding",
                        required_hops=len(p) - 1,
                        tier=tier,
                        relevant_entities=p,
                        relevant_paths=[p],
                        fraud_ring_id=ring_id,
                        ground_truth_entities=p,
                        ground_truth_paths=[str(p)],
                        complexity_score=min(1.0, complexity + 0.15),
                    ))

        return queries

    def _generate_synthetic_queries(self, dataset: ShadowDataset, seed: int) -> list[BenchmarkQuery]:
        queries = []
        r = random.Random(seed)

        if dataset.companies:
            offshore = [c for c in dataset.companies if c.get("is_offshore")]
            if offshore:
                c = r.choice(offshore)
                queries.append(BenchmarkQuery(
                    id="Q-SYN-OFFSHORE-1",
                    question=f"Find all details about offshore company {c.get('id')} and its ownership structure",
                    query_type="entity_resolution",
                    required_hops=2,
                    tier=2,
                    relevant_entities=[c.get("id")],
                    ground_truth_entities=[c.get("id")],
                    complexity_score=0.5,
                ))

        if dataset.persons:
            mules = [p for p in dataset.persons if p.get("is_mule")]
            if mules:
                p = r.choice(mules)
                queries.append(BenchmarkQuery(
                    id="Q-SYN-MULE-1",
                    question=f"Investigate money mule {p.get('id')} and trace their transaction history",
                    query_type="temporal",
                    required_hops=2,
                    tier=2,
                    relevant_entities=[p.get("id")],
                    ground_truth_entities=[p.get("id")],
                    complexity_score=0.55,
                ))

        if dataset.accounts:
            accounts = [a for a in dataset.accounts if a.get("velocity_score", 0) > 0.5]
            if accounts:
                a = r.choice(accounts)
                queries.append(BenchmarkQuery(
                    id="Q-SYN-VELOCITY-1",
                    question=f"Analyze high-velocity account {a.get('id')} for structuring patterns",
                    query_type="temporal",
                    required_hops=3,
                    tier=3,
                    relevant_entities=[a.get("id")],
                    ground_truth_entities=[a.get("id")],
                    complexity_score=0.65,
                ))

        for i in range(1, 4):
            tier = i
            templates = {
                1: ("entity_resolution", "What is the risk score of {entity}?", 1),
                2: ("semantic_synthesis", "Find all offshore shell companies in the dataset", 2),
                3: ("multi_hop_reasoning", "Trace money laundering from {entity} through shell companies to offshore accounts", 4),
            }
            qtype, template, hops = templates[tier]
            entity = ""
            if dataset.persons:
                entity = r.choice(dataset.persons).get("id", "P-000001")
            queries.append(BenchmarkQuery(
                id=f"Q-SYN-T{tier}-{i}",
                question=template.replace("{entity}", entity),
                query_type=qtype,
                required_hops=hops,
                tier=tier,
                relevant_entities=[entity] if entity else [],
                ground_truth_entities=[],
                complexity_score=tier * 0.2,
            ))

        return queries

    def _classify_tier(self, ring_type: str, complexity: float, entity_count: int) -> int:
        ring_type_lower = ring_type.lower()
        if any(t in ring_type_lower for t in ["circular", "layering", "laundering", "shell_ring"]):
            if complexity > 0.7 or entity_count > 10:
                return 4
            return 3
        if any(t in ring_type_lower for t in ["funnel", "offshore", "smurfing", "structuring"]):
            return 3
        if entity_count > 5:
            return 3
        if entity_count > 2:
            return 2
        return 1