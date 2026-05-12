"""
Adaptive data loader - the canonical sync point with 1_data_engine.
Reads from 1_data_engine outputs, or runs generation if absent.
"""
import csv
import json
import hashlib
import logging
import importlib.util
from pathlib import Path
from typing import Optional
from .schemas import ShadowDataset, GraphMetadata

logger = logging.getLogger(__name__)


class AdaptiveDataLoader:
    def __init__(self, profile: str = "hackathon_default", data_engine_dir: Optional[Path] = None):
        self.profile = profile
        self.project_root = Path(__file__).parent.parent.parent
        self.data_engine_dir = data_engine_dir or (self.project_root / "1_data_engine")
        self.output_dir = self.project_root / "outputs" / profile
        self.csv_dir = self.output_dir / "csv"
        self.json_dir = self.output_dir / "json"
        self._dataset: Optional[ShadowDataset] = None
        self._dataset_hash: str = ""

    def load(self, force_regenerate: bool = False) -> ShadowDataset:
        if self._dataset is not None and not force_regenerate:
            return self._dataset

        logger.info(f"AdaptiveDataLoader: profile={self.profile}, output_dir={self.output_dir}")

        if not self.output_dir.exists():
            logger.info(f"Data not found at {self.output_dir}, running 1_data_engine...")
            self._run_data_engine()

        self._dataset = self._load_from_outputs()
        self._dataset_hash = self._compute_hash()
        return self._dataset

    def _run_data_engine(self) -> None:
        import subprocess
        try:
            main_module = self.data_engine_dir / "main.py"
            if not main_module.exists():
                logger.error(f"1_data_engine/main.py not found at {main_module}")
                raise FileNotFoundError(f"1_data_engine not found at {self.data_engine_dir}")

            spec = importlib.util.spec_from_file_location("data_engine_main", str(main_module))
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

            if hasattr(module, "run_profile"):
                module.run_profile(self.profile)
            else:
                result = subprocess.run(
                    ["python3", "-m", "1_data_engine.main", "generate",
                     "--profile", self.profile, "--seed", "42"],
                    cwd=str(self.project_root),
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                if result.returncode != 0:
                    logger.error(f"1_data_engine failed: {result.stderr}")
                    raise RuntimeError(f"1_data_engine generation failed: {result.stderr}")
                logger.info(f"1_data_engine output: {result.stdout[-500:]}")

        except subprocess.TimeoutExpired:
            logger.error("1_data_engine generation timed out")
            raise
        except Exception as e:
            logger.error(f"Failed to run 1_data_engine: {e}")
            raise

    def _load_from_outputs(self) -> ShadowDataset:
        dataset = ShadowDataset()
        dataset.source_dir = str(self.output_dir)

        if self.csv_dir.exists():
            dataset.persons = self._read_csv(self.csv_dir / "persons.csv")
            dataset.companies = self._read_csv(self.csv_dir / "companies.csv")
            dataset.accounts = self._read_csv(self.csv_dir / "accounts.csv")
            dataset.addresses = self._read_csv(self.csv_dir / "addresses.csv")
            edges_file = self.csv_dir / "edges.csv"
            if edges_file.exists():
                dataset.edges = self._read_edges_csv(edges_file)
            devices_file = self.csv_dir / "devices.csv"
            if devices_file.exists():
                dataset.devices = self._read_csv(devices_file)

        if self.csv_dir.exists():
            tx_csv = self.csv_dir / "transactions.csv"
            if tx_csv.exists():
                dataset.transactions = self._read_csv(tx_csv)
                logger.info(f"Loaded {len(dataset.transactions)} transactions from transactions.csv")
                for tx in dataset.transactions:
                    tx["_source"] = "csv"

        if self.json_dir.exists():
            graph_file = self.json_dir / "graph.json"
            if graph_file.exists() and not dataset.transactions:
                try:
                    with open(graph_file, "r") as f:
                        graph_data = json.load(f)
                    if "transactions" in graph_data:
                        dataset.transactions = graph_data["transactions"]
                        for tx in dataset.transactions:
                            tx["_source"] = "json"
                except Exception as e:
                    logger.warning(f"Failed to load graph.json: {e}")
                    dataset.transactions = []

        if not dataset.transactions and dataset.edges:
            transferred_edges = [e for e in dataset.edges if e.get("relationship", "").lower() == "transferred_to"]
            for i, edge in enumerate(transferred_edges[:50000]):
                dataset.transactions.append({
                    "id": f"TX-{i+1:08d}",
                    "from_account": edge.get("from_id"),
                    "to_account": edge.get("to_id"),
                    "amount": edge.get("amount", 0),
                    "currency": "USD",
                    "transaction_type": "WIRE",
                    "timestamp": "",
                    "status": "COMPLETED",
                    "is_suspicious": bool(edge.get("is_fraud_related", False)),
                    "fraud_ring_id": edge.get("fraud_ring_id"),
                    "risk_score": 0.6 if edge.get("is_fraud_related") else 0.1,
                })
            if dataset.transactions:
                logger.info(f"Derived {len(dataset.transactions)} transactions from TRANSFERRED_TO edges")

        fraud_rings_csv = []
        if self.csv_dir.exists():
            fraud_rings_csv = self._read_csv(self.csv_dir / "fraud_rings.csv")

        fraud_rings_json_data = []
        if self.json_dir.exists():
            fraud_rings_json_path = self.json_dir / "fraud_rings.json"
            if fraud_rings_json_path.exists():
                try:
                    with open(fraud_rings_json_path, "r") as f:
                        raw = json.load(f)
                    if isinstance(raw, dict):
                        fraud_rings_json_data = list(raw.values())
                    elif isinstance(raw, list):
                        fraud_rings_json_data = raw
                except Exception as e:
                    logger.warning(f"Failed to load fraud_rings.json: {e}")

        json_map = {fr.get("id"): fr for fr in fraud_rings_json_data if fr.get("id")}
        for csv_ring in fraud_rings_csv:
            ring_id = csv_ring.get("id", "")
            merged = dict(csv_ring)
            if ring_id in json_map:
                json_ring = json_map[ring_id]
                for key in ["entities", "traversal_paths", "ring_type", "description"]:
                    if key in json_ring:
                        merged[key] = json_ring[key]
            dataset.fraud_rings.append(merged)

        for json_ring in fraud_rings_json_data:
            if json_ring.get("id") not in json_map:
                dataset.fraud_rings.append(json_ring)

        if not dataset.persons and not self.csv_dir.exists():
            logger.warning("No CSV data found, loading from sample dataset")
            dataset = self._load_sample_dataset()

        dataset.graph_metadata = self._compute_graph_metadata(dataset)
        logger.info(f"Loaded: {len(dataset.persons)} persons, {len(dataset.companies)} companies, "
                    f"{len(dataset.accounts)} accounts, {len(dataset.edges)} edges, "
                    f"{len(dataset.transactions)} transactions, {len(dataset.fraud_rings)} fraud rings")
        return dataset

    def _read_csv(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        results = []
        try:
            with open(path, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    row_clean = {k: v for k, v in row.items() if v != ""}
                    for k in ("risk_score", "balance", "amount", "annual_revenue", "velocity_score",
                              "transaction_count", "employee_count", "ownership_percentage"):
                        if k in row_clean:
                            try:
                                row_clean[k] = float(row_clean[k])
                            except (ValueError, TypeError):
                                pass
                    for k in ("is_pep", "is_sanctioned", "is_watched", "is_mule", "is_offshore",
                              "is_shell", "is_dormant", "is_suspicious", "is_shell_location",
                              "is_known_fraud_hub", "is_burner", "is_vpn", "is_structuring",
                              "is_smurfing"):
                        if k in row_clean:
                            row_clean[k] = row_clean[k].lower() in ("true", "1", "yes")
                    for k in ("key_entities", "entities"):
                        if k in row_clean and row_clean[k]:
                            row_clean[k] = [
                                x.strip() for x in str(row_clean[k]).split(",") if x.strip()
                            ]
                    if "traversal_paths" in row_clean and row_clean["traversal_paths"]:
                        val = row_clean["traversal_paths"]
                        try:
                            row_clean["traversal_paths"] = json.loads(val)
                        except (json.JSONDecodeError, TypeError):
                            if "," in val:
                                row_clean["traversal_paths"] = [
                                    x.strip() for x in val.split(",") if x.strip()
                                ]
                            else:
                                row_clean["traversal_paths"] = [val]
                    results.append(row_clean)
        except Exception as e:
            logger.warning(f"Failed to read {path}: {e}")
        return results

    def _read_edges_csv(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        results = []
        try:
            with open(path, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    row_clean = {k: v for k, v in row.items() if v != ""}
                    if "weight" in row_clean:
                        try:
                            row_clean["weight"] = float(row_clean["weight"])
                        except (ValueError, TypeError):
                            row_clean["weight"] = 1.0
                    if "is_fraud_related" in row_clean:
                        row_clean["is_fraud_related"] = row_clean["is_fraud_related"].lower() in ("true", "1", "yes")
                    results.append(row_clean)
        except Exception as e:
            logger.warning(f"Failed to read edges {path}: {e}")
        return results

    def _load_sample_dataset(self) -> ShadowDataset:
        sample_dir = self.project_root / "shadow_network_sample_dataset"
        if not sample_dir.exists():
            logger.warning(f"Sample dataset not found at {sample_dir}")
            return ShadowDataset()

        dataset = ShadowDataset()
        dataset.source_dir = str(sample_dir)
        entities_dir = sample_dir / "entities"
        edges_dir = sample_dir / "edges"

        for fname in ["persons.csv", "companies.csv", "accounts.csv", "addresses.csv"]:
            path = entities_dir / fname if entities_dir.exists() else sample_dir / fname
            data = self._read_csv(path)
            if "persons" in fname:
                dataset.persons = data
            elif "companies" in fname:
                dataset.companies = data
            elif "accounts" in fname:
                dataset.accounts = data
            elif "addresses" in fname:
                dataset.addresses = data

        for fname in ["owns.csv", "has_account.csv", "located_at.csv", "transferred_to.csv"]:
            path = edges_dir / fname if edges_dir.exists() else sample_dir / fname
            if path.exists():
                dataset.edges.extend(self._read_edges_csv(path))

        benchmark_dir = sample_dir / "benchmarks"
        if benchmark_dir.exists():
            fr_path = benchmark_dir / "fraud_ring_ground_truth.json"
            if fr_path.exists():
                try:
                    with open(fr_path, "r") as f:
                        dataset.fraud_rings = json.load(f)
                except Exception as e:
                    logger.warning(f"Failed to load fraud_ring_ground_truth: {e}")

        return dataset

    def _compute_graph_metadata(self, dataset: ShadowDataset) -> GraphMetadata:
        total_entities = (
            len(dataset.persons) + len(dataset.companies) + len(dataset.accounts)
            + len(dataset.addresses) + len(dataset.devices) + len(dataset.transactions)
        )
        edge_count = len(dataset.edges)
        n = max(total_entities, 1)
        density = (2 * edge_count) / (n * (n - 1)) if n > 1 else 0.0
        avg_degree = (2 * edge_count) / n if n > 0 else 0.0

        return GraphMetadata(
            person_count=len(dataset.persons),
            company_count=len(dataset.companies),
            account_count=len(dataset.accounts),
            address_count=len(dataset.addresses),
            device_count=len(dataset.devices),
            transaction_count=len(dataset.transactions),
            edge_count=edge_count,
            fraud_ring_count=len(dataset.fraud_rings),
            graph_density=round(density, 6),
            avg_degree=round(avg_degree, 2),
        )

    def _compute_hash(self) -> str:
        parts = [
            str(len(self._dataset.persons)) if self._dataset else "0",
            str(len(self._dataset.edges)) if self._dataset else "0",
            str(len(self._dataset.fraud_rings)) if self._dataset else "0",
            self.profile,
        ]
        combined = "|".join(parts)
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    @property
    def dataset_hash(self) -> str:
        return self._dataset_hash

    def get_output_dir(self) -> Path:
        return self.output_dir