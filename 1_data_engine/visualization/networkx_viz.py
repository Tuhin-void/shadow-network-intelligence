"""
NetworkX Visualization - Static graph visualization
"""
import networkx as nx
import matplotlib.pyplot as plt
from pathlib import Path

from ..schemas.entity_registry import EntityRegistry
from ..utils.logger import get_logger

logger = get_logger(__name__)


class NetworkXViz:
    """NetworkX-based graph visualization"""

    def visualize(self, registry: EntityRegistry, output_path: str = None):
        """Visualize the graph using NetworkX"""
        G = nx.Graph()

        for edge in registry.edges.values():
            G.add_edge(edge.from_id, edge.to_id, relationship=edge.relationship.value)

        logger.info(f"Created NetworkX graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

        if output_path:
            plt.figure(figsize=(20, 20))
            nx.draw(G, with_labels=True, node_size=50, font_size=6)
            plt.savefig(output_path)
            logger.info(f"Saved visualization to {output_path}")

        return G