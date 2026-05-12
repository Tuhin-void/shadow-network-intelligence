"""
Graph analytics - compute metrics from loaded dataset.
"""
from ..shared.data_loader import AdaptiveDataLoader
from ..shared.schemas import ShadowDataset


class GraphAnalytics:
    def __init__(self, data_loader: AdaptiveDataLoader):
        self.data_loader = data_loader

    def compute(self) -> dict:
        dataset = self.data_loader.load()
        return self._compute_metrics(dataset)

    def _compute_metrics(self, dataset: ShadowDataset) -> dict:
        total_entities = (
            len(dataset.persons) + len(dataset.companies)
            + len(dataset.accounts) + len(dataset.addresses)
            + len(dataset.devices)
        )
        edge_count = len(dataset.edges)
        n = max(total_entities, 1)

        degree_map = {}
        for edge in dataset.edges:
            for key in ("from_id", "to_id"):
                eid = edge.get(key)
                if eid:
                    degree_map[eid] = degree_map.get(eid, 0) + 1

        degrees = list(degree_map.values())
        avg_degree = sum(degrees) / n if n > 0 else 0
        max_degree = max(degrees) if degrees else 0
        min_degree = min(degrees) if degrees else 0

        fraud_edges = sum(1 for e in dataset.edges if e.get("is_fraud_related"))
        fraud_entities = set()
        rings = dataset.fraud_rings
        if isinstance(rings, dict):
            rings = [rings]
        elif not isinstance(rings, list):
            rings = []
        for ring in rings:
            if isinstance(ring, dict):
                for eid in ring.get("entities", []):
                    fraud_entities.add(eid)
                for eid in ring.get("key_entities", []):
                    fraud_entities.add(eid)

        offshore_companies = [c for c in dataset.companies if c.get("is_offshore")]
        shell_companies = [c for c in dataset.companies if c.get("is_shell")]
        mule_persons = [p for p in dataset.persons if p.get("is_mule")]

        return {
            "total_entities": total_entities,
            "total_edges": edge_count,
            "total_transactions": len(dataset.transactions),
            "graph_density": round((2 * edge_count) / (n * (n - 1)) if n > 1 else 0, 6),
            "avg_degree": round(avg_degree, 4),
            "max_degree": max_degree,
            "min_degree": min_degree,
            "degree_variance": round(sum((d - avg_degree) ** 2 for d in degrees) / n if n > 0 else 0, 4),
            "fraud_edges": fraud_edges,
            "fraud_edge_ratio": round(fraud_edges / edge_count, 4) if edge_count > 0 else 0,
            "fraud_entities": len(fraud_entities),
            "fraud_ring_count": len(rings),
            "offshore_companies": len(offshore_companies),
            "shell_companies": len(shell_companies),
            "mule_accounts": len(mule_persons),
            "avg_entities_per_fraud_ring": round(len(fraud_entities) / max(len(rings), 1), 2),
            "by_type": {
                "persons": len(dataset.persons),
                "companies": len(dataset.companies),
                "accounts": len(dataset.accounts),
                "addresses": len(dataset.addresses),
                "devices": len(dataset.devices),
                "transactions": len(dataset.transactions),
            },
        }