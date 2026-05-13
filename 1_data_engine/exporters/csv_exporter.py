"""
CSV Exporter - Multi-file CSV export
Produces one CSV per vertex type plus typed ring-membership edge CSVs.
"""
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict

from ..schemas.entity_registry import EntityRegistry
from ..utils.logger import get_logger

logger = get_logger(__name__)

_NOW_ISO = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


class CSVExporter:
    """Export entity data to CSV files (synchronized with live TigerGraph schema)."""

    def export(self, registry: EntityRegistry, output_dir: str) -> Dict[str, str]:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        files: Dict[str, str] = {}

        files["persons"]      = self._export_persons(registry,      output_path / "persons.csv")
        files["companies"]    = self._export_companies(registry,     output_path / "companies.csv")
        files["accounts"]     = self._export_accounts(registry,      output_path / "accounts.csv")
        files["addresses"]    = self._export_addresses(registry,     output_path / "addresses.csv")
        files["devices"]      = self._export_devices(registry,       output_path / "devices.csv")
        files["edges"]        = self._export_edges(registry,         output_path / "edges.csv")
        files["fraud_rings"]  = self._export_fraud_rings(registry,   output_path / "fraud_rings.csv")
        files["transactions"] = self._export_transactions(registry,  output_path / "transactions.csv")

        # Typed ring-membership edges (live schema: explicit per-type)
        ring_files = self._export_ring_memberships(registry, output_path)
        files.update(ring_files)

        logger.info(f"Exported CSV files to {output_dir}")
        return files

    # ── Vertex exporters ──────────────────────────────────────────────────────

    def _export_persons(self, registry: EntityRegistry, path: Path) -> str:
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "name", "first_name", "last_name", "date_of_birth",
                              "nationality", "tax_id", "risk_score", "is_pep",
                              "is_sanctioned", "is_watched"])
            for p in registry.persons.values():
                writer.writerow([p.id, p.name, p.first_name, p.last_name, p.date_of_birth,
                                  p.nationality, p.tax_id, p.risk_score,
                                  p.is_pep, p.is_sanctioned, p.is_watched])
        return str(path)

    def _export_companies(self, registry: EntityRegistry, path: Path) -> str:
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "name", "ein", "industry", "company_type",
                              "incorporation_date", "is_offshore", "is_shell", "risk_score"])
            for c in registry.companies.values():
                writer.writerow([c.id, c.name, c.ein, c.industry,
                                  c.company_type.value if hasattr(c.company_type, "value") else c.company_type,
                                  c.incorporation_date, c.is_offshore, c.is_shell, c.risk_score])
        return str(path)

    def _export_accounts(self, registry: EntityRegistry, path: Path) -> str:
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "account_number", "account_type", "owner_id",
                              "owner_type", "balance", "currency", "risk_score", "status"])
            for a in registry.accounts.values():
                writer.writerow([a.id, a.account_number,
                                  a.account_type.value if hasattr(a.account_type, "value") else a.account_type,
                                  a.owner_id, a.owner_type, a.balance, a.currency,
                                  a.risk_score,
                                  a.status.value if hasattr(a.status, "value") else a.status])
        return str(path)

    def _export_addresses(self, registry: EntityRegistry, path: Path) -> str:
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "street_address", "city", "state", "country",
                              "address_type", "is_shell_location", "risk_score"])
            for a in registry.addresses.values():
                writer.writerow([a.id, a.street_address, a.city, a.state, a.country,
                                  a.address_type.value if hasattr(a.address_type, "value") else a.address_type,
                                  a.is_shell_location, a.risk_score])
        return str(path)

    def _export_devices(self, registry: EntityRegistry, path: Path) -> str:
        """Export Device vertices — columns chosen to match the live TG schema."""
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "device_type", "ip_address", "operating_system",
                              "fingerprint", "geo_location", "risk_score",
                              "first_seen", "last_seen"])
            for d in getattr(registry, "devices", {}).values():
                device_type_str = d.device_type.value if hasattr(d.device_type, "value") else d.device_type
                os_str = (d.os_type.value if hasattr(d.os_type, "value") else d.os_type) if getattr(d, "os_type", None) else ""
                geo = ""
                if getattr(d, "city", None) or getattr(d, "country", None):
                    geo = f"{d.city or ''},{d.country or ''}".strip(",")
                first = d.first_seen.isoformat() if hasattr(d.first_seen, "isoformat") else str(getattr(d, "first_seen", ""))
                last  = d.last_seen.isoformat()  if hasattr(d.last_seen,  "isoformat") else str(getattr(d, "last_seen",  ""))
                writer.writerow([
                    d.id, device_type_str, d.ip_address or "", os_str,
                    getattr(d, "fingerprint", "") or "", geo,
                    d.risk_score, first, last,
                ])
        return str(path)

    def _export_edges(self, registry: EntityRegistry, path: Path) -> str:
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["from_id", "from_type", "to_id", "to_type",
                              "relationship", "weight", "is_fraud_related", "fraud_ring_id"])
            for e in registry.edges.values():
                writer.writerow([
                    e.from_id, e.from_type, e.to_id, e.to_type,
                    e.relationship.value if hasattr(e.relationship, "value") else e.relationship,
                    e.weight, e.is_fraud_related, e.fraud_ring_id or "",
                ])
        return str(path)

    def _export_fraud_rings(self, registry: EntityRegistry, path: Path) -> str:
        """Export FraudRing vertices — column `ring_type` matches live TigerGraph attribute."""
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "name", "ring_type", "severity", "description",
                              "entity_count", "edge_count", "key_entities"])
            for ring in registry.fraud_rings.values():
                writer.writerow([
                    ring.id, ring.name,
                    ring.ring_type.value if hasattr(ring.ring_type, "value") else ring.ring_type,
                    ring.severity.value if hasattr(ring.severity, "value") else ring.severity,
                    getattr(ring, "description", ""),
                    ring.get_entity_count(),
                    ring.get_edge_count(),
                    ",".join(ring.key_entities[:3]),
                ])
        return str(path)

    def _export_transactions(self, registry: EntityRegistry, path: Path) -> str:
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "id", "from_account", "to_account", "amount", "currency",
                "transaction_type", "status", "timestamp", "description", "reference",
                "is_suspicious", "risk_score",
                "is_layering", "is_placement", "is_integration", "is_structuring", "is_smurfing",
                "fraud_ring_id",
            ])
            for tx in registry.transactions.values():
                if hasattr(tx, "to_dict"):
                    writer.writerow([
                        tx.id, tx.from_account, tx.to_account, tx.amount, tx.currency,
                        tx.transaction_type.value if hasattr(tx.transaction_type, "value") else tx.transaction_type,
                        tx.status.value if hasattr(tx.status, "value") else tx.status,
                        tx.timestamp.isoformat() if hasattr(tx.timestamp, "isoformat") else str(tx.timestamp),
                        tx.description or "", tx.reference or "",
                        tx.is_suspicious, tx.risk_score,
                        getattr(tx, "is_layering",    False),
                        getattr(tx, "is_placement",   False),
                        getattr(tx, "is_integration", False),
                        getattr(tx, "is_structuring", False),
                        getattr(tx, "is_smurfing",    False),
                        getattr(tx, "fraud_ring_id",  "") or "",
                    ])
                else:
                    writer.writerow([
                        tx.get("id", ""), tx.get("from_account", ""), tx.get("to_account", ""),
                        tx.get("amount", 0), tx.get("currency", "USD"),
                        tx.get("transaction_type", "wire"), tx.get("status", "completed"),
                        tx.get("timestamp", ""), tx.get("description", ""), tx.get("reference", ""),
                        tx.get("is_suspicious", False), tx.get("risk_score", 0),
                        tx.get("is_layering", False), tx.get("is_placement", False),
                        tx.get("is_integration", False), tx.get("is_structuring", False),
                        tx.get("is_smurfing", False), tx.get("fraud_ring_id", "") or "",
                    ])
        return str(path)

    # ── Ring membership edge exporters ────────────────────────────────────────

    def _export_ring_memberships(self, registry: EntityRegistry, output_path: Path) -> Dict[str, str]:
        """
        Generate 6 typed ring-membership CSVs matching the live schema explicit edges:
          PERSON_MEMBER_OF_RING, COMPANY_MEMBER_OF_RING, ACCOUNT_MEMBER_OF_RING,
          TRANSACTION_MEMBER_OF_RING, DEVICE_CONNECTED_TO_RING, ADDRESS_CONNECTED_TO_RING.

        Determines entity type by checking registry collections, so no ID-prefix assumptions.
        """
        # Build type-lookup sets for fast membership checks
        person_ids      = set(registry.persons.keys())
        company_ids     = set(registry.companies.keys())
        account_ids     = set(registry.accounts.keys())
        transaction_ids = set(registry.transactions.keys())
        device_ids      = set(getattr(registry, "devices",  {}).keys())
        address_ids     = set(registry.addresses.keys())

        # Buckets: ring_id → list of (entity_id, role, confidence)
        persons_rows:       list[tuple] = []
        companies_rows:     list[tuple] = []
        accounts_rows:      list[tuple] = []
        transactions_rows:  list[tuple] = []
        devices_rows:       list[tuple] = []
        addresses_rows:     list[tuple] = []

        for ring in registry.fraud_rings.values():
            key_set = set(ring.key_entities)
            for eid in ring.entities:
                role       = "key_member" if eid in key_set else "member"
                confidence = 1.0 if eid in key_set else 0.8

                if eid in person_ids:
                    persons_rows.append((eid, ring.id, role, confidence, _NOW_ISO))
                elif eid in company_ids:
                    companies_rows.append((eid, ring.id, role, confidence, _NOW_ISO))
                elif eid in account_ids:
                    accounts_rows.append((eid, ring.id, role, confidence, _NOW_ISO))
                elif eid in transaction_ids:
                    transactions_rows.append((eid, ring.id, role, confidence, _NOW_ISO))
                elif eid in device_ids:
                    devices_rows.append((eid, ring.id, "used_device", confidence, _NOW_ISO))
                elif eid in address_ids:
                    addresses_rows.append((eid, ring.id, "shared_address", confidence, _NOW_ISO))

        files: Dict[str, str] = {}
        membership_header    = ["entity_id", "ring_id", "role",              "confidence_score", "discovered_at"]
        connection_header    = ["entity_id", "ring_id", "relationship_kind", "confidence_score", "discovered_at"]

        def _write(filename: str, header: list, rows: list) -> str:
            path = output_path / filename
            with open(path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(header)
                writer.writerows(rows)
            logger.info(f"Exported {len(rows)} rows → {filename}")
            return str(path)

        files["person_ring_memberships"]      = _write("person_ring_memberships.csv",      membership_header, persons_rows)
        files["company_ring_memberships"]     = _write("company_ring_memberships.csv",     membership_header, companies_rows)
        files["account_ring_memberships"]     = _write("account_ring_memberships.csv",     membership_header, accounts_rows)
        files["transaction_ring_memberships"] = _write("transaction_ring_memberships.csv", membership_header, transactions_rows)
        files["device_ring_connections"]      = _write("device_ring_connections.csv",      connection_header, devices_rows)
        files["address_ring_connections"]     = _write("address_ring_connections.csv",     connection_header, addresses_rows)

        return files
