"""
CSV Exporter - Multi-file CSV export
"""
import csv
from pathlib import Path
from typing import Dict

from ..schemas.entity_registry import EntityRegistry
from ..utils.logger import get_logger

logger = get_logger(__name__)


class CSVExporter:
    """Export entity data to CSV files"""

    def export(self, registry: EntityRegistry, output_dir: str) -> Dict[str, str]:
        """Export all entities to CSV files"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        files = {}

        files["persons"] = self._export_persons(registry, output_path / "persons.csv")
        files["companies"] = self._export_companies(registry, output_path / "companies.csv")
        files["accounts"] = self._export_accounts(registry, output_path / "accounts.csv")
        files["addresses"] = self._export_addresses(registry, output_path / "addresses.csv")
        files["edges"] = self._export_edges(registry, output_path / "edges.csv")
        files["fraud_rings"] = self._export_fraud_rings(registry, output_path / "fraud_rings.csv")

        logger.info(f"Exported CSV files to {output_dir}")
        return files

    def _export_persons(self, registry: EntityRegistry, path: Path) -> str:
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "name", "first_name", "last_name", "date_of_birth", "nationality", "tax_id", "risk_score", "is_pep", "is_sanctioned", "is_watched"])
            for p in registry.persons.values():
                writer.writerow([p.id, p.name, p.first_name, p.last_name, p.date_of_birth, p.nationality, p.tax_id, p.risk_score, p.is_pep, p.is_sanctioned, p.is_watched])
        return str(path)

    def _export_companies(self, registry: EntityRegistry, path: Path) -> str:
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "name", "ein", "industry", "company_type", "incorporation_date", "is_offshore", "is_shell", "risk_score"])
            for c in registry.companies.values():
                writer.writerow([c.id, c.name, c.ein, c.industry, c.company_type.value, c.incorporation_date, c.is_offshore, c.is_shell, c.risk_score])
        return str(path)

    def _export_accounts(self, registry: EntityRegistry, path: Path) -> str:
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "account_number", "account_type", "owner_id", "owner_type", "balance", "currency", "risk_score", "status"])
            for a in registry.accounts.values():
                writer.writerow([a.id, a.account_number[-4:], a.account_type.value, a.owner_id, a.owner_type, a.balance, a.currency, a.risk_score, a.status.value])
        return str(path)

    def _export_addresses(self, registry: EntityRegistry, path: Path) -> str:
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "street_address", "city", "state", "country", "address_type", "is_shell_location", "risk_score"])
            for a in registry.addresses.values():
                writer.writerow([a.id, a.street_address, a.city, a.state, a.country, a.address_type.value, a.is_shell_location, a.risk_score])
        return str(path)

    def _export_edges(self, registry: EntityRegistry, path: Path) -> str:
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["from_id", "from_type", "to_id", "to_type", "relationship", "weight", "is_fraud_related", "fraud_ring_id"])
            for e in registry.edges.values():
                writer.writerow([e.from_id, e.from_type, e.to_id, e.to_type, e.relationship.value, e.weight, e.is_fraud_related, e.fraud_ring_id or ""])
        return str(path)

    def _export_fraud_rings(self, registry: EntityRegistry, path: Path) -> str:
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "name", "type", "severity", "entity_count", "edge_count", "key_entities"])
            for ring in registry.fraud_rings.values():
                writer.writerow([ring.id, ring.name, ring.ring_type.value, ring.severity.value, ring.get_entity_count(), ring.get_edge_count(), ",".join(ring.key_entities[:3])])
        return str(path)