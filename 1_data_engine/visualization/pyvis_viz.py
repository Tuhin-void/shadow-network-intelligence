"""
PyVis Visualization - Interactive HTML visualization
"""
from pathlib import Path

from ..schemas.entity_registry import EntityRegistry
from ..utils.logger import get_logger

logger = get_logger(__name__)


class PyVisViz:
    """PyVis-based interactive graph visualization"""

    def visualize(self, registry: EntityRegistry, output_path: str = "graph.html"):
        """Create interactive visualization"""
        try:
            from pyvis.network import Network
        except ImportError:
            logger.warning("PyVis not installed, skipping interactive visualization")
            return None

        net = Network(height="800px", width="100%", bgcolor="#222222", font_color="white")

        for entity_id in registry.get_fraud_entities()[:500]:
            entity = registry.get_entity(entity_id)
            if entity:
                entity_type = registry.get_entity_type(entity_id)
                color = self._get_color(entity_type)
                net.add_node(entity_id, label=entity_id, color=color, title=str(entity))

        for edge in list(registry.edges.values())[:1000]:
            if edge.is_fraud_related:
                net.add_edge(edge.from_id, edge.to_id, color="red", width=2)
            else:
                net.add_edge(edge.from_id, edge.to_id, color="gray", width=1)

        net.save_graph(output_path)
        logger.info(f"Saved interactive visualization to {output_path}")
        return output_path

    def _get_color(self, entity_type: str) -> str:
        colors = {
            "PERSON": "#ff9999",
            "COMPANY": "#99ff99",
            "ACCOUNT": "#9999ff",
            "ADDRESS": "#ffff99",
        }
        return colors.get(entity_type, "#ffffff")