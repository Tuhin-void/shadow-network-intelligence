"""Hybrid retriever — orchestrates multiple retrievers into a unified retrieval strategy."""
from typing import Optional


class HybridRetriever:
    """
    Orchestrates entity_centric, neighborhood, path_aware, community,
    and temporal retrievers based on query type.
    """

    def __init__(self, graph_client: "GraphClient"):
        from retrievers.entity_centric import EntityCentricRetriever
        from retrievers.neighborhood import NeighborhoodRetriever
        from retrievers.path_aware import PathAwareRetriever
        from retrievers.community import CommunityRetriever
        from retrievers.temporal import TemporalRetriever

        self.entity_retriever = EntityCentricRetriever(graph_client)
        self.neighborhood_retriever = NeighborhoodRetriever(graph_client)
        self.path_retriever = PathAwareRetriever(graph_client)
        self.community_retriever = CommunityRetriever(graph_client)
        self.temporal_retriever = TemporalRetriever(graph_client)

    def retrieve(
        self,
        query: str,
        strategy: str = "auto",
        top_k: int = 10,
        entity_id: Optional[str] = None,
        depth: int = 2,
    ) -> dict:
        """
        Unified retrieval that selects the best strategy based on query.
        Strategies: auto, entity, neighborhood, path, community, temporal, full
        """
        if strategy == "auto":
            strategy = self._detect_strategy(query)

        results = {"strategy": strategy, "entities": [], "context": [], "paths": [], "communities": []}

        if strategy in ("auto", "entity"):
            entities = self.entity_retriever.retrieve(query, top_k=top_k)
            results["entities"] = [
                {"v_id": e.v_id, "type": e.vertex_type, "name": e.name, "score": e.score, "risk": e.risk_score}
                for e in entities
            ]

        if strategy in ("auto", "neighborhood", "full"):
            seed_ids = [e["v_id"] for e in results.get("entities", [])] or ([entity_id] if entity_id else [])
            if seed_ids:
                neighborhood = self.neighborhood_retriever.retrieve(seed_ids, max_hops=depth)
                results["context"] = [
                    {"v_id": n.v_id, "type": n.vertex_type, "name": n.name, "edge": n.edge_type, "depth": n.depth}
                    for n in neighborhood.get("nodes", [])
                ]

        if strategy in ("auto", "path", "full"):
            if entity_id:
                pass

        if strategy in ("auto", "community", "full"):
            high_risk = self.community_retriever.detect_high_risk_cluster(min_risk=0.7)
            results["communities"] = high_risk[:top_k]

        return results

    def _detect_strategy(self, query: str) -> str:
        q = query.lower()
        if any(k in q for k in ["path", "route", "connect", "between", "link"]):
            return "path"
        if any(k in q for k in ["temporal", "time", "spike", "burst", "when", "date"]):
            return "temporal"
        if any(k in q for k in ["cluster", "community", "ring", "shell", "group"]):
            return "community"
        if any(k in q for k in ["neighbor", "around", "connected", "related"]):
            return "neighborhood"
        return "entity"

    def full_context(self, entity_id: str, depth: int = 2) -> dict:
        """Get full context for an entity across all retrieval modes."""
        profile = self.entity_retriever.get_entity_profile(entity_id)
        neighborhood = self.neighborhood_retriever.get_ego_graph(entity_id, depth=depth)
        risk_result = self.community_retriever.find_fraud_rings(entity_id)
        temporal = self.temporal_retriever.detect_spike(entity_id)

        return {
            "entity_id": entity_id,
            "profile": profile,
            "neighborhood_size": neighborhood["stats"]["total_nodes"],
            "neighbors": neighborhood["nodes"],
            "fraud_ring": risk_result,
            "temporal_spike": temporal,
        }