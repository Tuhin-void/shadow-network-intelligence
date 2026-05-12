"""
Cycle Detector - Detects laundering cycles in the graph
"""
from typing import List, Set, Dict

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    nx = None
    HAS_NETWORKX = False

from ..schemas.entity_registry import EntityRegistry
from ..utils.logger import get_logger

logger = get_logger(__name__)


class CycleDetector:
    """Detects cycles in the graph representing laundering patterns"""

    def __init__(self):
        self.graph = None

    def build_graph(self, registry: EntityRegistry) -> nx.DiGraph:
        """Build NetworkX graph from registry"""
        G = nx.DiGraph()

        for edge in registry.edges.values():
            if edge.relationship.value == "transferred_to":
                G.add_edge(edge.from_id, edge.to_id, edge_id=edge.id, weight=edge.weight)

        self.graph = G
        return G

    def find_cycles(self, max_length: int = 10) -> List[List[str]]:
        """Find cycles in the graph"""
        if self.graph is None:
            return []

        cycles = []
        for node in self.graph.nodes():
            try:
                for cycle in nx.simple_cycles(self.graph):
                    if len(cycle) <= max_length and len(cycle) >= 3:
                        cycles.append(cycle)
            except:
                pass

        return cycles[:100]

    def find_circular_ownership(self, registry: EntityRegistry) -> List[List[str]]:
        """Find circular ownership patterns"""
        cycles = []

        for ring in registry.fraud_rings.values():
            if "circular" in ring.ring_type.value or "ownership" in ring.ring_type.value:
                cycles.append(ring.entities)

        return cycles