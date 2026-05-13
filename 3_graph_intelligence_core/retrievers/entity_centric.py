"""Entity-centric retriever — retrieves and ranks entities by relevance to a query."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EntityMatch:
    v_id: str
    vertex_type: str
    name: str
    score: float
    attributes: dict = field(default_factory=dict)
    risk_score: Optional[float] = None


class EntityCentricRetriever:
    """
    Finds entities in the graph relevant to a query.
    - entity_id lookup (primary_id or attribute match)
    - keyword-based search across vertex types
    - top-k filtering
    """

    def __init__(self, graph_client: "GraphClient"):
        self.client = graph_client

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        entity_types: Optional[list[str]] = None,
        min_score: float = 0.0,
    ) -> list[EntityMatch]:
        """
        Retrieve top-k entities matching a query string.
        Falls back to name attribute matching if no installed query.
        """
        if entity_types is None:
            entity_types = ["Person", "Company", "Account", "Device", "Transaction"]

        entity_id = self._extract_entity_id(query)
        if entity_id:
            match = self._get_entity_by_id(entity_id, entity_types)
            if match:
                return [match]

        results = []
        for vtype in entity_types:
            matches = self._search_by_name(query, vtype, limit=top_k)
            results.extend(matches)

        results.sort(key=lambda x: x.score, reverse=True)
        return [r for r in results if r.score >= min_score][:top_k]

    def _extract_entity_id(self, query: str) -> Optional[str]:
        import re
        patterns = [
            r'\bP-\d+\b',
            r'\bC-\d+\b',
            r'\bA-\d+\b',
            r'\bADDR-\d+\b',
            r'\bD-\d+\b',
            r'\bTX-\d+\b',
            r'\bT-\d+\b',
        ]
        for pat in patterns:
            m = re.search(pat, query)
            if m:
                return m.group(0)
        return None

    def _get_entity_by_id(self, entity_id: str, entity_types: list[str]) -> Optional[EntityMatch]:
        for vtype in entity_types:
            vertex = self.client.get_vertex(vtype, entity_id)
            if vertex:
                name = vertex.get("attributes", {}).get("name", entity_id)
                risk = vertex.get("attributes", {}).get("risk_score")
                return EntityMatch(
                    v_id=entity_id,
                    vertex_type=vtype,
                    name=name,
                    score=1.0,
                    attributes=vertex.get("attributes", {}),
                    risk_score=risk,
                )
        return None

    def _search_by_name(self, query: str, vertex_type: str, limit: int = 20) -> list[EntityMatch]:
        tokens = query.lower().split()
        vertices = self.client.get_vertices(vertex_type, limit=limit * 2)
        matches = []

        for v in vertices:
            attrs = v.get("attributes", {})
            name = attrs.get("name", "")
            if not name:
                continue

            name_lower = name.lower()
            score = 0.0

            if any(t in name_lower for t in tokens):
                score = sum(1 for t in tokens if t in name_lower) / len(tokens)
                matches.append(EntityMatch(
                    v_id=v.get("v_id", ""),
                    vertex_type=vertex_type,
                    name=name,
                    score=score,
                    attributes=attrs,
                    risk_score=attrs.get("risk_score"),
                ))

        return matches[:limit]

    def get_entity_profile(self, entity_id: str) -> dict:
        """Get full entity profile with neighbors."""
        profile = {"v_id": entity_id, "neighbors": [], "edges": []}

        for vtype in ["Person", "Company", "Account", "Device", "Transaction"]:
            vertex = self.client.get_vertex(vtype, entity_id)
            if vertex:
                profile["vertex_type"] = vtype
                profile["attributes"] = vertex.get("attributes", {})
                break

        neighbors = self.client.get_neighbors(entity_id, limit=50)
        if "results" in neighbors:
            profile["neighbors"] = neighbors["results"]

        return profile


def _score_entity(entity: dict, query_tokens: list[str]) -> float:
    name = entity.get("attributes", {}).get("name", "").lower()
    if not name:
        return 0.0
    return sum(1 for t in query_tokens if t in name) / max(len(query_tokens), 1)