"""Data loader — reads CSV exports from 1_data_engine and loads into TigerGraph."""
import csv
import logging
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)


class CSVDataLoader:
    """
    Reads CSV files from 1_data_engine outputs and yields batched records
    ready for TigerGraph upsert via GraphClient.
    """

    def __init__(self, base_dir: str = "outputs"):
        self.base_dir = Path(base_dir)

    def load_all_profiles(self, profile: str) -> dict[str, list[dict]]:
        """Load all CSV files for a given profile."""
        profile_dir = self.base_dir / profile / "csv"
        if not profile_dir.exists():
            raise FileNotFoundError(f"CSV directory not found: {profile_dir}")

        results = {}
        for csv_file in sorted(profile_dir.glob("*.csv")):
            name = csv_file.stem
            records = self._load_csv(csv_file)
            results[name] = records
            logger.info(f"Loaded {len(records)} records from {csv_file.name}")

        return results

    def _load_csv(self, path: Path) -> list[dict]:
        records = []
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cleaned = {k.strip(): v.strip() if isinstance(v, str) else v for k, v in row.items()}
                records.append(cleaned)
        return records

    def iter_batches(self, records: list[dict], batch_size: int) -> Iterator[list[dict]]:
        for i in range(0, len(records), batch_size):
            yield records[i : i + batch_size]

    def load_vertices(self, profile: str, vertex_type: str) -> list[dict]:
        """Load specific vertex type from profile's CSV."""
        profile_dir = self.base_dir / profile / "csv"
        mapping = {
            "Person": "persons",
            "Company": "companies",
            "Account": "accounts",
            "Address": "addresses",
            "Device": "devices",
            "Transaction": "transactions",
        }
        csv_name = mapping.get(vertex_type, vertex_type.lower() + "s")
        csv_path = profile_dir / f"{csv_name}.csv"
        if not csv_path.exists():
            return []
        return self._load_csv(csv_path)


class GraphLoader:
    """
    Loads data into TigerGraph via GraphClient upsert methods.
    Supports batched upsert with parallelization.
    """

    VERTEX_TYPE_MAP = {
        "persons": "Person",
        "companies": "Company",
        "accounts": "Account",
        "addresses": "Address",
        "devices": "Device",
        "transactions": "Transaction",
    }

    EDGE_DEFINITIONS = [
        ("KNOWS", "persons", "persons", ["person1_id", "person2_id"]),
        ("EMPLOYED_BY", "persons", "companies", ["person_id", "company_id"]),
        ("OWNS", "companies", "accounts", ["owner_id", "account_id"]),
        ("RELATED_TO", "persons", "companies", ["entity1_id", "entity2_id"]),
    ]

    def __init__(self, graph_client: "GraphClient", batch_size: int = 5000, parallel_batches: int = 4):
        self.client = graph_client
        self.batch_size = batch_size
        self.parallel_batches = parallel_batches
        self.csv_loader = CSVDataLoader()

    def load_profile(
        self,
        profile: str,
        source_dir: str = "outputs",
        upsert: bool = True,
    ) -> dict:
        """
        Load all CSV data from a profile into TigerGraph.
        Returns summary of loaded vertices and edges.
        """
        csv_loader = CSVDataLoader(source_dir)
        results = {"vertices": {}, "edges": {}, "success": True}

        all_data = csv_loader.load_all_profiles(profile)

        for csv_name, records in all_data.items():
            vt = self.VERTEX_TYPE_MAP.get(csv_name, csv_name.capitalize())
            if not records:
                continue

            total = 0
            for batch in csv_loader.iter_batches(records, self.batch_size):
                formatted = self._format_vertex_batch(vt, batch)
                resp = self.client.upsert_batch_vertices(vt, formatted)
                if "error" in resp:
                    results["success"] = False
                    logger.error(f"Vertex upsert error for {vt}: {resp}")
                else:
                    total += len(batch)

            results["vertices"][vt] = total
            logger.info(f"Loaded {total} {vt} vertices")

        return results

    def _format_vertex_batch(self, vertex_type: str, batch: list[dict]) -> list[dict]:
        formatted = []
        for rec in batch:
            attrs = self._clean_record(rec, vertex_type)
            formatted.append(attrs)
        return formatted

    def _clean_record(self, rec: dict, vertex_type: str) -> dict:
        cleaned = {}
        for k, v in rec.items():
            if v == "" or v is None:
                continue
            key = k.strip()
            val = v

            if key in ("risk_score", "amount", "balance", "ownership_pct"):
                try:
                    val = float(v)
                except (ValueError, TypeError):
                    continue
            elif key in ("is_shell", "is_offshore", "is_suspicious"):
                val = str(v).lower() in ("true", "1", "yes")
            elif key in ("created_at", "timestamp", "opened_date", "closed_date", "incorporated_date", "last_used"):
                try:
                    val = int(float(v))
                except (ValueError, TypeError):
                    continue
            elif key in ("tags",):
                val = v.split(",") if isinstance(v, str) and v else []
            elif key == "id":
                key = "v_id"
            elif key not in ("v_id", "tx_hash", "account_number", "name", "email", "phone",
                              "country", "jurisdiction", "industry", "bank_name", "account_type",
                              "currency", "city", "postal_code", "address_type", "device_type",
                              "ip_address", "user_agent", "full_address", "tx_type", "from_account",
                              "to_account", "relationship_type", "role", "description", "link_type"):
                pass

            cleaned[key] = val

        if "v_id" not in cleaned:
            for id_key in ("id", "person_id", "company_id", "account_id"):
                if id_key in rec:
                    cleaned["v_id"] = rec[id_key].strip()
                    break

        return cleaned

    def load_transactions(self, profile: str, source_dir: str = "outputs") -> dict:
        """Load transactions.csv specifically with edge creation."""
        csv_path = Path(source_dir) / profile / "csv" / "transactions.csv"
        if not csv_path.exists():
            return {"loaded": 0, "error": "transactions.csv not found"}

        records = []
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cleaned = {k.strip(): v.strip() if isinstance(v, str) else v for k, v in row.items()}
                records.append(cleaned)

        loader = CSVDataLoader()
        total = 0
        for batch in loader.iter_batches(records, self.batch_size):
            formatted = []
            for rec in batch:
                v_id = f"TX-{rec.get('id', '')}"
                amount = float(rec.get("amount", 0) or 0)
                timestamp = int(float(rec.get("timestamp", 0) or 0))
                risk_score = float(rec.get("risk_score", 0) or 0)
                is_suspicious = str(rec.get("is_suspicious", "false")).lower() in ("true", "1", "yes")

                attrs = {
                    "v_id": v_id,
                    "tx_hash": rec.get("tx_hash", ""),
                    "amount": amount,
                    "currency": rec.get("currency", "USD"),
                    "tx_type": rec.get("tx_type", ""),
                    "timestamp": timestamp,
                    "from_account": rec.get("from_account", ""),
                    "to_account": rec.get("to_account", ""),
                    "risk_score": risk_score,
                    "is_suspicious": is_suspicious,
                    "tags": rec.get("tags", "").split(",") if rec.get("tags") else [],
                }
                formatted.append(attrs)

            resp = self.client.upsert_batch_vertices("Transaction", formatted)
            if "error" not in resp:
                total += len(batch)

        logger.info(f"Loaded {total} Transaction vertices")

        for rec in records[:5000]:
            from_acc = rec.get("from_account", "").strip()
            to_acc = rec.get("to_account", "").strip()
            if from_acc and to_acc:
                self.client.upsert_edge("RECEIVED_TRANSACTION", f"TX-{rec.get('id', '')}", from_acc)
                self.client.upsert_edge("SENT_TRANSACTION", from_acc, f"TX-{rec.get('id', '')}")

        return {"loaded": total}