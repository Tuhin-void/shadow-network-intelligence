"""
Shadow Network Intelligence - GraphRAG Retriever
Graph-augmented retrieval for fraud detection
"""
import logging
import re
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class GraphRetriever:
    """
    Graph-augmented retrieval that combines:
    - Vector similarity search (optional)
    - Graph traversal via GraphClient
    - Community detection via GSQL queries
    - Entity/relationship extraction
    """

    def __init__(
        self,
        graph_client: "GraphClient",
        config: Optional[Dict] = None,
    ):
        self.client = graph_client
        self.config = config or {}
        self.traversal_depth = self.config.get("traversal_depth", 3)
        self.top_k = self.config.get("top_k", 10)

    def search(
        self,
        query: str,
        top_k: int = 5,
        depth: int = 2,
        include_neighbors: bool = True,
    ) -> Dict[str, Any]:
        """
        Perform graph-augmented search.

        1. Extract entity IDs from query
        2. Graph traversal from matched entities
        3. Return subgraph context
        """
        logger.info(f"GraphRAG search: {query}")

        entity_ids = self._extract_entity_ids(query)

        if not entity_ids and include_neighbors:
            entity_ids = self._keyword_search(query, top_k=top_k * 2)

        subgraph = {"entities": [], "edges": []}

        if entity_ids:
            expanded = self._expand_with_neighbors(
                entity_ids[:top_k],
                depth=depth,
            )
            subgraph = expanded

        return {
            "query": query,
            "entity_ids": entity_ids,
            "subgraph": subgraph,
            "context": self._build_context(subgraph),
        }

    def _expand_with_neighbors(
        self,
        entity_ids: List[str],
        depth: int = 2,
    ) -> Dict[str, Any]:
        """Expand entities with graph neighbors via GraphClient."""
        expanded = {"entities": [], "edges": []}

        for entity_id in entity_ids:
            neighbors = self.client.get_neighbors(entity_id, limit=50, depth=depth)
            results = neighbors.get("results", [])
            if results and isinstance(results[0], dict) and "neighbors" in results[0]:
                results = results[0].get("neighbors", [])

            for n in results:
                n_id = n.get("v_id") or n.get("id") or ""
                n_type = n.get("v_type") or n.get("type") or ""
                edge_type = n.get("edge_type") or ""

                expanded["entities"].append({
                    "id": n_id,
                    "type": n_type,
                    "name": n.get("name", n_id),
                    "risk_score": n.get("risk_score"),
                    "attributes": n,
                })
                expanded["edges"].append({
                    "from": entity_id,
                    "to": n_id,
                    "type": edge_type,
                })

        return expanded

    def _build_context(self, subgraph: Dict) -> str:
        """Build natural language context from subgraph."""
        entities = subgraph.get("entities", [])
        edges = subgraph.get("edges", [])
        entity_count = len(entities)
        edge_count = len(edges)

        context = f"Found {entity_count} entities and {edge_count} relationships. "

        for entity in entities[:5]:
            etype = entity.get("type", "Entity")
            name = entity.get("name", entity.get("id", "Unknown"))
            risk = entity.get("risk_score", 0)
            risk_str = f" (risk={risk:.2f})" if risk else ""
            context += f"{etype}: {name}{risk_str}. "

        return context

    def hybrid_search(
        self,
        query: str,
        community_level: int = 2,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """Community-aware hybrid search."""
        results = self.search(query, top_k=top_k, include_neighbors=True)

        if self.client._pygt_conn:
            try:
                community_results = self.client.run_installed_query(
                    "tg_shell_cluster",
                    params={"threshold": 0.6, "min_entities": 3},
                )
                results["communities"] = community_results
            except Exception as e:
                logger.warning(f"Community query failed: {e}")
                results["communities"] = []

        return results

    def _extract_entity_ids(self, query: str) -> List[str]:
        """Extract entity IDs from query string."""
        patterns = [
            r'\bP-\d+\b',
            r'\bC-\d+\b',
            r'\bA-\d+\b',
            r'\bADDR-\d+\b',
            r'\bD-\d+\b',
            r'\bTX-\d+\b',
            r'\bT-\d+\b',
            r'\bFR-[A-Z]+-\d+\b',
        ]
        ids = []
        for pat in patterns:
            ids.extend(re.findall(pat, query))
        return list(dict.fromkeys(ids))

    def _keyword_search(self, query: str, top_k: int = 10) -> List[str]:
        """Fallback keyword-based entity search."""
        tokens = query.lower().split()
        if not tokens:
            return []

        matches = []
        for vtype in ["Person", "Company", "Account", "Device", "Transaction"]:
            vertices = self.client.get_vertices(vtype, limit=top_k * 2)
            for v in vertices:
                name = v.get("attributes", {}).get("name", "")
                if name and any(t in name.lower() for t in tokens):
                    vid = v.get("v_id", "")
                    if vid:
                        matches.append(vid)

        return matches[:top_k]


def create_graph_retriever(graph_client: "GraphClient", config: Optional[Dict] = None) -> GraphRetriever:
    """Factory function to create GraphRetriever."""
    return GraphRetriever(graph_client=graph_client, config=config)