"""
Shadow Network Intelligence - GraphRAG Retriever
Graph-augmented retrieval for fraud detection
"""
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class GraphRetriever:
    """
    Graph-augmented retrieval that combines:
    - Vector similarity search
    - Graph traversal
    - Community detection
    """
    
    def __init__(
        self,
        embedding_model,
        vector_store,
        llm_provider,
        db_connection,
        config: Optional[Dict] = None
    ):
        self.embedding_model = embedding_model
        self.vector_store = vector_store
        self.llm = llm_provider
        self.conn = db_connection
        self.config = config or {}
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        depth: int = 2,
        include_neighbors: bool = True
    ) -> Dict[str, Any]:
        """
        Perform graph-augmented search.
        
        1. Embed query
        2. Vector similarity search
        3. Graph traversal from matched entities
        4. Return subgraph context
        """
        logger.info(f"GraphRAG search: {query}")
        
        query_embedding = self.embedding_model.embed_query(query)
        
        vector_results = self.vector_store.search(query_embedding, top_k=top_k)
        
        if include_neighbors and vector_results:
            subgraph = self._expand_with_neighbors(
                [r["id"] for r in vector_results],
                depth=depth
            )
        else:
            subgraph = {"entities": vector_results, "edges": []}
        
        return {
            "query": query,
            "vector_results": vector_results,
            "subgraph": subgraph,
            "context": self._build_context(subgraph)
        }
    
    def _expand_with_neighbors(
        self,
        entity_ids: List[str],
        depth: int = 2
    ) -> Dict[str, Any]:
        """Expand entities with graph neighbors"""
        expanded = {"entities": [], "edges": []}
        
        for entity_id in entity_ids:
            neighbors = self.conn.getNeighbors(entity_id, limit=depth * 5)
            expanded["entities"].extend(neighbors.get("results", []))
            expanded["edges"].extend(neighbors.get("edges", []))
        
        return expanded
    
    def _build_context(self, subgraph: Dict) -> str:
        """Build natural language context from subgraph"""
        entity_count = len(subgraph.get("entities", []))
        edge_count = len(subgraph.get("edges", []))
        
        context = f"Found {entity_count} entities and {edge_count} relationships. "
        
        for entity in subgraph.get("entities", [])[:5]:
            context += f"{entity.get('type', 'Entity')}: {entity.get('name', 'Unknown')}. "
        
        return context
    
    def hybrid_search(
        self,
        query: str,
        community_level: int = 2,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """Community-aware hybrid search"""
        results = self.search(query, top_k=top_k)
        
        community_results = self.conn.runInstalledQuery(
            "community_detection",
            params={"top_k": top_k, "level": community_level}
        )
        
        results["communities"] = community_results
        results["context"] += f" Found {len(community_results)} related communities."
        
        return results


def create_graph_retriever(config: Dict) -> GraphRetriever:
    """Factory function to create GraphRetriever"""
    return GraphRetriever(
        embedding_model=None,
        vector_store=None,
        llm_provider=None,
        db_connection=None,
        config=config
    )
