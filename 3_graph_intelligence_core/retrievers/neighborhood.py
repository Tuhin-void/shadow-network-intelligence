"""Neighborhood retriever — retrieves local graph neighborhoods around entities."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class NeighborNode:
    v_id: str
    vertex_type: str
    name: str
    edge_type: str
    depth: int
    risk_score: Optional[float] = None
    attributes: dict = field(default_factory=dict)


class NeighborhoodRetriever:
    """
    Retrieves graph neighborhoods around entity seeds.
    - 1-hop direct neighbors
    - Multi-hop traversal (depth 2-3)
    - Edge-type filtering
    """

    def __init__(self, graph_client: "GraphClient"):
        self.client = graph_client

    def retrieve(
        self,
        seed_ids: list[str],
        max_hops: int = 2,
        edge_types: Optional[list[str]] = None,
        max_neighbors: int = 50,
        entity_types: Optional[list[str]] = None,
    ) -> dict:
        """
        Retrieve neighborhood subgraph around seed entities.
        Returns {nodes: [], edges: [], stats: {}}.
        """
        result = {"nodes": [], "edges": [], "stats": {"total_nodes": 0, "total_edges": 0}}
        seen = set()
        frontier = list(seed_ids)
        current_depth = 0

        while frontier and current_depth < max_hops:
            next_frontier = []
            for entity_id in frontier:
                if entity_id in seen:
                    continue
                seen.add(entity_id)

                neighbors = self.client.get_neighbors(entity_id, limit=max_neighbors)
                neighbor_list = neighbors.get("results", [])
                if isinstance(neighbor_list, list) and len(neighbor_list) > 0:
                    first = neighbor_list[0]
                    if isinstance(first, dict) and "neighbors" in first:
                        neighbor_list = first.get("neighbors", [])

                for n in neighbor_list:
                    n_id = n.get("v_id") or n.get("id") or ""
                    n_type = n.get("v_type") or n.get("type") or ""
                    edge_type = n.get("edge_type") or ""
                    n_name = n.get("name", "")
                    n_risk = n.get("risk_score")

                    if entity_types and n_type not in entity_types:
                        continue
                    if edge_types and edge_type not in edge_types:
                        continue

                    result["nodes"].append(NeighborNode(
                        v_id=n_id,
                        vertex_type=n_type,
                        name=n_name,
                        edge_type=edge_type,
                        depth=current_depth + 1,
                        risk_score=n_risk,
                        attributes=n,
                    ))
                    result["edges"].append({
                        "from": entity_id,
                        "to": n_id,
                        "edge_type": edge_type,
                    })
                    next_frontier.append(n_id)

            frontier = next_frontier
            current_depth += 1

        result["stats"]["total_nodes"] = len(result["nodes"])
        result["stats"]["total_edges"] = len(result["edges"])
        return result

    def get_ego_graph(
        self,
        entity_id: str,
        depth: int = 1,
        edge_types: Optional[list[str]] = None,
    ) -> dict:
        """Get ego-centric subgraph for a single entity."""
        result = self.retrieve(
            seed_ids=[entity_id],
            max_hops=depth,
            edge_types=edge_types,
            max_neighbors=30,
        )
        return result

    def batch_retrieve(
        self,
        entity_ids: list[str],
        depth: int = 2,
        limit_per_entity: int = 30,
    ) -> list[dict]:
        """Retrieve neighborhoods for multiple entities in batch."""
        results = []
        for eid in entity_ids:
            r = self.get_ego_graph(eid, depth=depth)
            results.append({"entity_id": eid, "neighborhood": r})
        return results