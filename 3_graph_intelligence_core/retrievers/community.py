"""Community retriever — detects clusters and communities in the graph."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Community:
    id: str
    members: list[dict]
    size: int
    avg_risk: float
    cluster_type: str = "unknown"


class CommunityRetriever:
    """
    Detects communities/clusters in the graph.
    - Shell company clusters
    - Fraud rings
    - Connected components
    - High-risk entity groups
    """

    def __init__(self, graph_client: "GraphClient"):
        self.client = graph_client

    def find_shell_clusters(
        self,
        risk_threshold: float = 0.6,
        min_entities: int = 3,
    ) -> list[Community]:
        """Find clusters of shell/offshore companies."""
        result = self.client.run_installed_query(
            "tg_shell_cluster",
            {"threshold": risk_threshold, "min_entities": min_entities},
        )

        if "error" in result:
            shell_companies = self.client.get_vertices("Company", limit=500)
            companies = [c for c in shell_companies if c.get("attributes", {}).get("is_shell", False) or
                         c.get("attributes", {}).get("is_offshore", False) or
                         c.get("attributes", {}).get("risk_score", 0) >= risk_threshold]

            clusters = self._group_by_risk(companies, risk_threshold)
            return [Community(
                id=f"shell_cluster_{i}",
                members=cl,
                size=len(cl),
                avg_risk=sum(c.get("attributes", {}).get("risk_score", 0) for c in cl) / max(len(cl), 1),
                cluster_type="shell_offshore",
            ) for i, cl in enumerate(clusters)]

        communities = []
        for i, c in enumerate(result.get("results", [])):
            if isinstance(c, dict):
                communities.append(Community(
                    id=f"shell_cluster_{i}",
                    members=[c],
                    size=1,
                    avg_risk=c.get("risk_score", 0),
                    cluster_type="shell_offshore",
                ))
        return communities

    def find_fraud_rings(
        self,
        entity_id: str,
        risk_threshold: float = 0.7,
    ) -> dict:
        """Find fraud ring around an entity."""
        result = self.client.run_installed_query(
            "tg_fraud_ring",
            {"entity_id": entity_id, "threshold": risk_threshold},
        )
        return result if "error" not in result else {"detected": False}

    def find_connected_components(self, seed_id: str, max_depth: int = 3) -> list[str]:
        """Find all entities connected to seed (connected component)."""
        visited = set()
        frontier = [seed_id]

        while frontier:
            next_frontier = []
            for eid in frontier:
                if eid in visited:
                    continue
                visited.add(eid)
                neighbors = self.client.get_neighbors(eid, limit=100)
                for n in neighbors.get("results", []):
                    nid = n.get("v_id") or n.get("id") or ""
                    if nid and nid not in visited:
                        next_frontier.append(nid)
            frontier = next_frontier

        return list(visited)

    def detect_high_risk_cluster(
        self,
        min_risk: float = 0.7,
        vertex_types: Optional[list[str]] = None,
        limit: int = 100,
    ) -> list[dict]:
        """Find all high-risk entities across vertex types."""
        if vertex_types is None:
            vertex_types = ["Person", "Company", "Account"]

        high_risk = []
        for vtype in vertex_types:
            vertices = self.client.get_vertices(vtype, limit=limit)
            for v in vertices:
                attrs = v.get("attributes", {})
                if attrs.get("risk_score", 0) >= min_risk:
                    high_risk.append({
                        "v_id": v.get("v_id", ""),
                        "type": vtype,
                        "name": attrs.get("name", ""),
                        "risk_score": attrs.get("risk_score"),
                    })

        return sorted(high_risk, key=lambda x: x["risk_score"], reverse=True)

    def _group_by_risk(self, entities: list[dict], threshold: float) -> list[list[dict]]:
        clusters = []
        for e in entities:
            risk = e.get("attributes", {}).get("risk_score", 0)
            if risk >= threshold:
                clusters.append([e])
        return clusters

    def community_summary(self, community: Community) -> str:
        """Generate a summary description of a community."""
        types = {}
        for m in community.members:
            vt = m.get("type", "unknown")
            types[vt] = types.get(vt, 0) + 1

        type_str = ", ".join(f"{k}: {v}" for k, v in types.items())
        return (f"Community '{community.id}' ({community.cluster_type}): "
                f"{community.size} entities ({type_str}), avg risk={community.avg_risk:.2f}")