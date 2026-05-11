"""
Shadow Network Intelligence - Graph Search Agent
Searches transaction graph for patterns
"""
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

class GraphSearchAgent:
    """
    Graph Search Agent - Searches transaction network
    
    Responsibilities:
    - Traverse graph relationships
    - Find entity connections
    - Detect network patterns
    """
    
    def __init__(self, graph_connection, llm_provider):
        self.conn = graph_connection
        self.llm = llm_provider
    
    def search_entity(
        self,
        entity_id: str,
        depth: int = 2,
        entity_types: List[str] = None
    ) -> Dict[str, Any]:
        """
        Search for entity and its connections.
        """
        logger.info(f"Searching entity: {entity_id} (depth={depth})")
        
        entity = self._get_entity(entity_id)
        if not entity:
            return {"error": "Entity not found"}
        
        neighbors = self._get_neighbors(entity_id, depth, entity_types)
        paths = self._find_paths(entity_id, depth)
        
        return {
            "entity": entity,
            "neighbors": neighbors,
            "paths": paths,
            "network_metrics": self._calculate_network_metrics(neighbors)
        }
    
    def _get_entity(self, entity_id: str) -> Optional[Dict]:
        """Fetch entity details"""
        try:
            result = self.conn.run_taql(
                f'GET Vertex FROM Account WHERE id = "{entity_id}"'
            )
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Error fetching entity: {e}")
            return None
    
    def _get_neighbors(
        self,
        entity_id: str,
        depth: int,
        entity_types: List[str] = None
    ) -> List[Dict]:
        """Get neighboring entities"""
        try:
            query = f'''
            INTERPRET GSQL QUERY nearest_neighbors() {{
                start = {{Acc:{{entity_id}}}};
                results = {{}};
                FROM start -(:e)-> -(:v)-(:v2) AT depth <= {depth};
                results = {{v2}};
                PRINT results;
            }}
            '''
            result = self.conn.run_gsql(query)
            return result.get("results", [])
        except Exception as e:
            logger.error(f"Error fetching neighbors: {e}")
            return []
    
    def _find_paths(self, entity_id: str, depth: int) -> List[List[str]]:
        """Find paths from entity"""
        paths = []
        try:
            query = f'''
            INTERPRET GSQL QUERY find_paths() {{
                start = {{Acc:{{entity_id}}}};
                paths = {{}};
                FROM start -(:e)-> -(:v) AT depth <= {depth};
                paths = {{e}};
                PRINT paths;
            }}
            '''
            result = self.conn.run_gsql(query)
            return result.get("paths", [])
        except Exception as e:
            logger.error(f"Error finding paths: {e}")
            return []
    
    def _calculate_network_metrics(self, neighbors: List[Dict]) -> Dict:
        """Calculate network centrality metrics"""
        return {
            "degree": len(neighbors),
            "connected_accounts": sum(1 for n in neighbors if n.get("type") == "Account"),
            "connected_companies": sum(1 for n in neighbors if n.get("type") == "Company"),
            "network_density": min(len(neighbors) / 100, 1.0)
        }
    
    def find_patterns(
        self,
        pattern_type: str,
        filters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Find entities matching a pattern type.
        """
        logger.info(f"Finding patterns: {pattern_type}")
        
        pattern_queries = {
            "circular": self._find_circular_patterns,
            "layered": self._find_layered_patterns,
            "shell_ring": self._find_shell_rings
        }
        
        query_func = pattern_queries.get(pattern_type)
        if query_func:
            return query_func(filters or {})
        
        return []
    
    def _find_circular_patterns(self, filters: Dict) -> List[Dict]:
        """Find circular transaction patterns"""
        return []
    
    def _find_layered_patterns(self, filters: Dict) -> List[Dict]:
        """Find layered transaction patterns"""
        return []
    
    def _find_shell_rings(self, filters: Dict) -> List[Dict]:
        """Find shell company rings"""
        return []