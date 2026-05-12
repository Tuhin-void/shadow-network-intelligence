"""
TigerGraph Exporter - TigerGraph CSV loaders
"""
import csv
from pathlib import Path
from typing import Dict

from ..schemas.entity_registry import EntityRegistry
from ..utils.logger import get_logger

logger = get_logger(__name__)


class TigerGraphExporter:
    """Export data in TigerGraph-compatible CSV format"""

    def export(self, registry: EntityRegistry, output_dir: str) -> Dict[str, str]:
        """Export all data in TigerGraph format"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        files = {}

        files["persons"] = self._export_vertex(registry.persons, output_path / "Person.csv", "person_id")
        files["companies"] = self._export_vertex(registry.companies, output_path / "Company.csv", "company_id")
        files["accounts"] = self._export_vertex(registry.accounts, output_path / "Account.csv", "account_id")
        files["addresses"] = self._export_vertex(registry.addresses, output_path / "Address.csv", "address_id")
        files["transactions"] = self._export_edges_tigergraph(registry, output_path / "Transaction.csv")
        files["relationships"] = self._export_relationships_tigergraph(registry, output_path / "Relationship.csv")

        logger.info(f"Exported TigerGraph files to {output_dir}")
        return files

    def _export_vertex(self, entities: dict, path: Path, id_field: str) -> str:
        if not entities:
            path.touch()
            return str(path)

        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            first_entity = list(entities.values())[0]
            tg_row = first_entity.to_tigergraph_row()
            writer.writerow(tg_row.keys())
            for entity in entities.values():
                writer.writerow(entity.to_tigergraph_row().values())
        return str(path)

    def _export_edges_tigergraph(self, registry: EntityRegistry, path: Path) -> str:
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["from_id", "to_id", "amount", "is_suspicious"])
            for e in registry.edges.values():
                if e.relationship.value == "transferred_to":
                    writer.writerow([e.from_id, e.to_id, e.metadata.get("amount", 0), e.is_fraud_related])
        return str(path)

    def _export_relationships_tigergraph(self, registry: EntityRegistry, path: Path) -> str:
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["from_id", "from_type", "to_id", "to_type", "relationship"])
            for e in registry.edges.values():
                if e.relationship.value != "transferred_to":
                    writer.writerow([e.from_id, e.from_type, e.to_id, e.to_type, e.relationship.value])
        return str(path)