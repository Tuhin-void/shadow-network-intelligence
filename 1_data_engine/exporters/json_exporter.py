"""
JSON Exporter - JSON graph export
"""
import json
from pathlib import Path
from typing import Dict

from ..schemas.entity_registry import EntityRegistry
from ..utils.logger import get_logger

logger = get_logger(__name__)


class JSONExporter:
    """Export entity data to JSON format"""

    def export(self, registry: EntityRegistry, output_dir: str) -> Dict[str, str]:
        """Export all data to JSON files"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        files = {}

        files["graph"] = self._export_graph(registry, output_path / "graph.json")
        files["fraud_rings"] = self._export_fraud_rings(registry, output_path / "fraud_rings.json")
        files["metadata"] = self._export_metadata(registry, output_path / "metadata.json")

        logger.info(f"Exported JSON files to {output_dir}")
        return files

    def _export_graph(self, registry: EntityRegistry, path: Path) -> str:
        data = {
            "entities": {
                "persons": [p.to_dict() for p in registry.persons.values()],
                "companies": [c.to_dict() for c in registry.companies.values()],
                "accounts": [a.to_dict() for a in registry.accounts.values()],
                "addresses": [a.to_dict() for a in registry.addresses.values()],
            },
            "edges": [e.to_dict() for e in registry.edges.values()],
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        return str(path)

    def _export_fraud_rings(self, registry: EntityRegistry, path: Path) -> str:
        data = {
            ring.id: ring.to_dict()
            for ring in registry.fraud_rings.values()
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        return str(path)

    def _export_metadata(self, registry: EntityRegistry, path: Path) -> str:
        data = registry.to_dict()
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        return str(path)