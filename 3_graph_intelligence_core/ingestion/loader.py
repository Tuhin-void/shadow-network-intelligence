"""Data loader — reads CSV exports from 1_data_engine and loads into TigerGraph."""
import csv
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)


def _emit(stage: str, msg: str) -> None:
    """Unbuffered stage progress line for live visibility."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{stage:<12}] {msg}", flush=True)


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
        profile_dir = self.base_dir / profile / "csv"
        mapping = {
            "Person":      "persons",
            "Company":     "companies",
            "Account":     "accounts",
            "Address":     "addresses",
            "Device":      "devices",
            "Transaction": "transactions",
            "FraudRing":   "fraud_rings",
        }
        csv_name = mapping.get(vertex_type, vertex_type.lower() + "s")
        csv_path = profile_dir / f"{csv_name}.csv"
        if not csv_path.exists():
            return []
        return self._load_csv(csv_path)


class GraphLoader:
    """
    Loads data into TigerGraph via GraphClient upsert methods.
    Supports batched upsert for all 7 vertex types and 19 edge types.
    """

    VERTEX_TYPE_MAP = {
        "persons":      "Person",
        "companies":    "Company",
        "accounts":     "Account",
        "addresses":    "Address",
        "devices":      "Device",
        "transactions": "Transaction",
        "fraud_rings":  "FraudRing",
    }

    # (csv_stem, edge_type, from_col, to_col, from_type, to_type)
    RING_EDGE_MAP = [
        ("person_ring_memberships",     "PERSON_MEMBER_OF_RING",     "entity_id", "ring_id", "Person",      "FraudRing"),
        ("company_ring_memberships",    "COMPANY_MEMBER_OF_RING",    "entity_id", "ring_id", "Company",     "FraudRing"),
        ("account_ring_memberships",    "ACCOUNT_MEMBER_OF_RING",    "entity_id", "ring_id", "Account",     "FraudRing"),
        ("transaction_ring_memberships","TRANSACTION_MEMBER_OF_RING","entity_id", "ring_id", "Transaction", "FraudRing"),
        ("device_ring_connections",     "DEVICE_CONNECTED_TO_RING",  "entity_id", "ring_id", "Device",      "FraudRing"),
        ("address_ring_connections",    "ADDRESS_CONNECTED_TO_RING", "entity_id", "ring_id", "Address",     "FraudRing"),
    ]

    # Generic edges.csv `relationship` column → canonical live edge type.
    _RELATIONSHIP_TO_EDGE: dict[str, str] = {
        "owns":                "OWNS",
        "has_account":         "HAS_ACCOUNT",
        "transferred_to":      "TRANSFERRED_TO",
        "located_at":          "LOCATED_AT",
        "associated_with":     "ASSOCIATED_WITH",
        "uses_device":         "USES_DEVICE",
        "accessed_from":       "ACCESSED_FROM",
        "registered_at":       "REGISTERED_AT",
        "benefits_from":       "BENEFITS_FROM",
        "beneficial_owner_of": "BENEFITS_FROM",
        "shares_device_with":  "SHARES_DEVICE_WITH",
        "shares_address_with": "SHARES_ADDRESS_WITH",
    }

    # from_type/to_type from edges.csv (UPPERCASE) → canonical TG type name.
    _CSV_TYPE_TO_TG: dict[str, str] = {
        "PERSON":      "Person",
        "COMPANY":     "Company",
        "ACCOUNT":     "Account",
        "ADDRESS":     "Address",
        "DEVICE":      "Device",
        "TRANSACTION": "Transaction",
        "FRAUDRING":   "FraudRing",
    }

    def __init__(self, graph_client: "GraphClient", batch_size: int = 5000, parallel_batches: int = 4):
        self.client = graph_client
        self.batch_size = batch_size
        self.parallel_batches = parallel_batches
        self.csv_loader = CSVDataLoader()

    # CSV stems we actually consume; anything else (e.g. edges.csv) is skipped.
    _CONSUMED_CSVS: frozenset[str] = frozenset({
        "persons", "companies", "accounts", "addresses", "devices",
        "fraud_rings", "transactions",
        "person_ring_memberships", "company_ring_memberships",
        "account_ring_memberships", "transaction_ring_memberships",
        "device_ring_connections", "address_ring_connections",
    })

    def load_profile(
        self,
        profile: str,
        source_dir: str = "outputs",
        upsert: bool = True,
        sample_limit: int | None = None,
    ) -> dict:
        """
        Load vertex and edge CSV data for a profile into TigerGraph.

        Stages, with per-stage timing emitted to stdout (unbuffered):
          1. discovery      — locate CSVs
          2. read_vertices  — read vertex CSVs into memory
          3. upsert_vertices — batched vertex upserts (Transaction handled separately)
          4. upsert_tx       — Transaction vertices + SENT/RECEIVED edges (batched)
          5. upsert_rings    — Ring membership edges (batched)

        sample_limit: if set, truncate every CSV to this many rows (smoke-test mode).
        """
        t_total = time.perf_counter()
        profile_csv_dir = Path(source_dir) / profile / "csv"
        results: dict = {"vertices": {}, "edges": {}, "success": True}

        # ── Stage 1: discovery ────────────────────────────────────────────────
        t0 = time.perf_counter()
        if not profile_csv_dir.exists():
            raise FileNotFoundError(f"CSV directory not found: {profile_csv_dir}")
        present = sorted(p.stem for p in profile_csv_dir.glob("*.csv")
                         if p.stem in self._CONSUMED_CSVS)
        _emit("discovery",
              f"profile={profile} dir={profile_csv_dir} csvs={len(present)} "
              f"({', '.join(present)}) sample_limit={sample_limit} took={time.perf_counter()-t0:.2f}s")

        # ── Stage 2: read vertex CSVs ─────────────────────────────────────────
        t0 = time.perf_counter()
        vertex_data: dict[str, list[dict]] = {}
        for csv_stem, vt in self.VERTEX_TYPE_MAP.items():
            if csv_stem == "transactions":
                continue  # handled in upsert_tx stage
            csv_path = profile_csv_dir / f"{csv_stem}.csv"
            if not csv_path.exists():
                continue
            recs = self.csv_loader._load_csv(csv_path)
            if sample_limit:
                recs = recs[:sample_limit]
            vertex_data[csv_stem] = recs
            _emit("read_vertices", f"{csv_stem}: {len(recs)} rows")
        _emit("read_vertices", f"done in {time.perf_counter()-t0:.2f}s")

        # ── Stage 3: upsert vertices (non-Transaction) ────────────────────────
        t0 = time.perf_counter()
        for csv_stem, records in vertex_data.items():
            vt = self.VERTEX_TYPE_MAP[csv_stem]
            if not records:
                continue
            self._upsert_vertex_type(vt, records, results)
        _emit("upsert_vertices", f"done in {time.perf_counter()-t0:.2f}s")

        # ── Stage 4: transactions (vertices + edges, BATCHED) ─────────────────
        t0 = time.perf_counter()
        tx_result = self.load_transactions(profile, source_dir, sample_limit=sample_limit)
        results["vertices"]["Transaction"] = tx_result.get("loaded", 0)
        results["edges"].update(tx_result.get("edges", {}))
        _emit("upsert_tx", f"done in {time.perf_counter()-t0:.2f}s")

        # ── Stage 4b: generic topology edges from edges.csv (BATCHED) ─────────
        t0 = time.perf_counter()
        edges_path = profile_csv_dir / "edges.csv"
        if edges_path.exists():
            self._load_generic_edges(edges_path, results, sample_limit=sample_limit)
        else:
            _emit("upsert_edges", "edges.csv not found — skipping topology edges")
        _emit("upsert_edges", f"done in {time.perf_counter()-t0:.2f}s")

        # ── Stage 5: ring membership edges (BATCHED per edge_type) ────────────
        t0 = time.perf_counter()
        for csv_stem, edge_type, from_col, to_col, from_vt, to_vt in self.RING_EDGE_MAP:
            csv_path = profile_csv_dir / f"{csv_stem}.csv"
            if not csv_path.exists():
                continue
            records = self.csv_loader._load_csv(csv_path)
            if sample_limit:
                records = records[:sample_limit]
            self._upsert_ring_edges(edge_type, from_vt, to_vt, from_col, to_col, records, results)
        _emit("upsert_rings", f"done in {time.perf_counter()-t0:.2f}s")

        _emit("TOTAL",
              f"profile={profile} success={results['success']} "
              f"vertices={sum(results['vertices'].values())} "
              f"edges={sum(results['edges'].values())} "
              f"elapsed={time.perf_counter()-t_total:.2f}s")
        return results

    def _upsert_vertex_type(self, vt: str, records: list[dict], results: dict) -> None:
        """Batched vertex upsert with fail-fast on persistent schema errors."""
        total = 0
        consecutive_errors = 0
        batches = list(self.csv_loader.iter_batches(records, self.batch_size))
        for i, batch in enumerate(batches):
            t0 = time.perf_counter()
            formatted = [self._clean_record(rec, vt) for rec in batch]
            resp = self.client.upsert_batch_vertices(vt, formatted)
            dur = (time.perf_counter() - t0) * 1000
            if "error" in resp:
                consecutive_errors += 1
                results["success"] = False
                _emit("upsert_vertices",
                      f"  {vt} batch {i+1}/{len(batches)} ({len(batch)}): "
                      f"ERROR after {dur:.0f}ms — {str(resp['error'])[:120]}")
                # Fail-fast: schema mismatch will repeat for every batch.
                if consecutive_errors >= 2:
                    _emit("upsert_vertices",
                          f"  {vt}: aborting after {consecutive_errors} consecutive errors")
                    break
            else:
                consecutive_errors = 0
                total += resp.get("loadSuccess", len(batch))
                _emit("upsert_vertices",
                      f"  {vt} batch {i+1}/{len(batches)} ({len(batch)}): "
                      f"ok in {dur:.0f}ms (cumulative={total})")
        results["vertices"][vt] = total

    def _upsert_ring_edges(
        self, edge_type: str, from_vt: str, to_vt: str,
        from_col: str, to_col: str, records: list[dict], results: dict,
    ) -> None:
        """Batched ring-edge upsert. Builds edge records then calls upsert_batch_edges."""
        if not records:
            return
        edge_records = []
        for rec in records:
            from_id = rec.get(from_col, "").strip()
            to_id   = rec.get(to_col,   "").strip()
            if not from_id or not to_id:
                continue
            attrs: dict = {"from_id": from_id, "to_id": to_id,
                           "from_type": from_vt, "to_type": to_vt}
            if rec.get("role"):
                attrs["role"] = rec["role"]
            if rec.get("relationship_kind"):
                attrs["relationship_kind"] = rec["relationship_kind"]
            if rec.get("confidence_score"):
                try:
                    attrs["confidence_score"] = float(rec["confidence_score"])
                except (ValueError, TypeError):
                    pass
            if rec.get("discovered_at"):
                attrs["discovered_at"] = self._to_tg_datetime(rec["discovered_at"])
            edge_records.append(attrs)

        t0 = time.perf_counter()
        resp = self.client.upsert_batch_edges(edge_type, edge_records)
        dur = (time.perf_counter() - t0) * 1000
        if "error" in resp:
            results["success"] = False
            _emit("upsert_rings",
                  f"  {edge_type}: ERROR after {dur:.0f}ms — {str(resp['error'])[:120]}")
        else:
            n = resp.get("loadSuccess", len(edge_records))
            results["edges"][edge_type] = n
            _emit("upsert_rings",
                  f"  {edge_type}: {n}/{len(edge_records)} edges in {dur:.0f}ms")

    def _load_generic_edges(
        self, edges_path: Path, results: dict, sample_limit: int | None = None,
    ) -> None:
        """
        Ingest edges.csv — generic topology edges (OWNS, HAS_ACCOUNT, LOCATED_AT,
        BENEFITS_FROM, ASSOCIATED_WITH, TRANSFERRED_TO, etc.).

        CSV columns: from_id, from_type, to_id, to_type, relationship, weight,
                     is_fraud_related, fraud_ring_id

        Strategy:
          1. Read + normalize each row (uppercase relationship → canonical edge type,
             uppercase from/to_type → canonical TG vertex type)
          2. Group by canonical edge_type
          3. Batched upsert per edge_type via upsert_batch_edges
        """
        t0 = time.perf_counter()
        records = self.csv_loader._load_csv(edges_path)
        if sample_limit:
            records = records[:sample_limit]
        _emit("upsert_edges", f"read {len(records)} rows from edges.csv in {time.perf_counter()-t0:.2f}s")

        # Bucket by canonical edge type. Skip unknown relationship strings (logged once).
        buckets: dict[str, list[dict]] = {}
        skipped_rels: dict[str, int] = {}
        invalid_rows = 0

        for rec in records:
            rel_raw = (rec.get("relationship") or "").strip().lower()
            edge_type = self._RELATIONSHIP_TO_EDGE.get(rel_raw)
            if not edge_type:
                skipped_rels[rel_raw] = skipped_rels.get(rel_raw, 0) + 1
                continue

            from_id = (rec.get("from_id") or "").strip()
            to_id   = (rec.get("to_id")   or "").strip()
            if not from_id or not to_id:
                invalid_rows += 1
                continue

            from_type = self._CSV_TYPE_TO_TG.get((rec.get("from_type") or "").strip().upper())
            to_type   = self._CSV_TYPE_TO_TG.get((rec.get("to_type")   or "").strip().upper())
            if not from_type or not to_type:
                invalid_rows += 1
                continue

            edge_rec: dict = {
                "from_id":   from_id,
                "to_id":     to_id,
                "from_type": from_type,
                "to_type":   to_type,
            }
            self._apply_edge_attrs(edge_type, rec, edge_rec)
            buckets.setdefault(edge_type, []).append(edge_rec)

        if skipped_rels:
            _emit("upsert_edges",
                  f"  skipped unknown relationships: "
                  + ", ".join(f"{k}({v})" for k, v in skipped_rels.items()))
        if invalid_rows:
            _emit("upsert_edges", f"  skipped {invalid_rows} rows with missing/unknown ids or types")

        # Upsert each bucket in batches.
        for edge_type, edge_recs in buckets.items():
            n_ok = 0
            chunks = list(self.csv_loader.iter_batches(edge_recs, self.batch_size))
            for i, chunk in enumerate(chunks):
                t_batch = time.perf_counter()
                resp = self.client.upsert_batch_edges(edge_type, chunk)
                dur = (time.perf_counter() - t_batch) * 1000
                if "error" in resp:
                    results["success"] = False
                    _emit("upsert_edges",
                          f"  {edge_type} batch {i+1}/{len(chunks)}: ERROR after {dur:.0f}ms — "
                          f"{str(resp['error'])[:120]}")
                    break  # next edge type; same schema error will repeat
                got = resp.get("loadSuccess", len(chunk))
                n_ok += got
                _emit("upsert_edges",
                      f"  {edge_type} batch {i+1}/{len(chunks)} ({len(chunk)}): "
                      f"ok in {dur:.0f}ms (cumulative={n_ok})")
            # Merge into results (sum if some edges of this type already loaded by tx stage).
            results["edges"][edge_type] = results["edges"].get(edge_type, 0) + n_ok

    def _apply_edge_attrs(self, edge_type: str, rec: dict, edge_rec: dict) -> None:
        """Populate per-edge-type attributes from edges.csv row.

        edges.csv has minimal info (weight, is_fraud_related). We populate only the
        attributes the live schema accepts and leave optional ones unset.
        """
        weight = rec.get("weight")
        is_fraud = str(rec.get("is_fraud_related", "")).lower() in ("true", "1", "yes")

        if edge_type == "OWNS":
            # ownership_percent DOUBLE, beneficial_owner BOOL
            if weight:
                try:
                    edge_rec["ownership_percent"] = float(weight)
                except (ValueError, TypeError):
                    pass
            edge_rec["beneficial_owner"] = is_fraud  # fraud-related ownership often beneficial
        elif edge_type == "HAS_ACCOUNT":
            # role STRING
            edge_rec["role"] = "primary"
        elif edge_type == "TRANSFERRED_TO":
            # amount DOUBLE, suspicious_flag BOOL
            if weight:
                try:
                    edge_rec["amount"] = float(weight)
                except (ValueError, TypeError):
                    pass
            edge_rec["suspicious_flag"] = is_fraud
        elif edge_type == "LOCATED_AT":
            edge_rec["address_role"] = "primary"
        elif edge_type == "ASSOCIATED_WITH":
            edge_rec["relationship_type"] = "associated"
            if weight:
                try:
                    edge_rec["confidence_score"] = float(weight)
                except (ValueError, TypeError):
                    pass
        elif edge_type == "BENEFITS_FROM":
            if weight:
                try:
                    edge_rec["relationship_strength"] = float(weight)
                except (ValueError, TypeError):
                    pass
        # Other edge types (USES_DEVICE, ACCESSED_FROM, REGISTERED_AT, SHARES_*) —
        # attributes left empty; live schema accepts edges without optional attrs.

    def load_transactions(
        self, profile: str, source_dir: str = "outputs",
        sample_limit: int | None = None,
    ) -> dict:
        """Load transactions.csv: upsert Transaction vertices + SENT/RECEIVED edges (all batched)."""
        csv_path = Path(source_dir) / profile / "csv" / "transactions.csv"
        if not csv_path.exists():
            _emit("upsert_tx", "transactions.csv not found — skipping")
            return {"loaded": 0, "edges": {}}

        t0 = time.perf_counter()
        records = self.csv_loader._load_csv(csv_path)
        if sample_limit:
            records = records[:sample_limit]
        _emit("upsert_tx", f"read {len(records)} tx rows in {time.perf_counter()-t0:.2f}s")

        # ── Transaction vertices (batched) ────────────────────────────────────
        tx_total = 0
        consecutive_errors = 0
        batches = list(self.csv_loader.iter_batches(records, self.batch_size))
        for i, batch in enumerate(batches):
            t_batch = time.perf_counter()
            formatted = []
            for rec in batch:
                v_id = rec.get("id", "").strip()
                if not v_id:
                    continue
                timestamp_raw = rec.get("timestamp", "")
                tx_vertex: dict = {
                    "v_id":             v_id,
                    "amount":           float(rec.get("amount", 0) or 0),
                    "currency":         rec.get("currency", "USD"),
                    "transaction_type": rec.get("transaction_type", rec.get("tx_type", "")),
                    "timestamp":        self._to_tg_datetime(timestamp_raw) if timestamp_raw else "",
                    "risk_score":       int(float(rec.get("risk_score", 0) or 0)),
                    "suspicious_flag":  str(rec.get("is_suspicious", "false")).lower() in ("true", "1", "yes"),
                }
                if rec.get("description"):
                    tx_vertex["description"] = rec["description"]
                formatted.append(tx_vertex)

            resp = self.client.upsert_batch_vertices("Transaction", formatted)
            dur = (time.perf_counter() - t_batch) * 1000
            if "error" in resp:
                consecutive_errors += 1
                _emit("upsert_tx",
                      f"  Transaction batch {i+1}/{len(batches)}: ERROR after {dur:.0f}ms — "
                      f"{str(resp['error'])[:120]}")
                if consecutive_errors >= 2:
                    _emit("upsert_tx", "  aborting Transaction upsert after 2 errors")
                    break
            else:
                consecutive_errors = 0
                tx_total += resp.get("loadSuccess", len(formatted))
                _emit("upsert_tx",
                      f"  Transaction batch {i+1}/{len(batches)} ({len(formatted)}): "
                      f"ok in {dur:.0f}ms (cumulative={tx_total})")

        # ── SENT_TRANSACTION + RECEIVED_TRANSACTION edges (BATCHED) ───────────
        sent_records: list[dict] = []
        recv_records: list[dict] = []
        for rec in records:
            tx_id = rec.get("id", "").strip()
            if not tx_id:
                continue
            from_acc = rec.get("from_account", "").strip()
            to_acc   = rec.get("to_account",   "").strip()
            timestamp_raw = rec.get("timestamp", "")
            timestamp = self._to_tg_datetime(timestamp_raw) if timestamp_raw else ""
            attrs: dict = {"timestamp": timestamp} if timestamp else {}

            if from_acc:
                sent_records.append({
                    "from_id": from_acc, "to_id": tx_id,
                    "from_type": "Account", "to_type": "Transaction",
                    **attrs,
                })
            if to_acc:
                recv_records.append({
                    "from_id": tx_id, "to_id": to_acc,
                    "from_type": "Transaction", "to_type": "Account",
                    **attrs,
                })

        edge_counts: dict[str, int] = {}
        for edge_type, edge_recs in (
            ("SENT_TRANSACTION", sent_records),
            ("RECEIVED_TRANSACTION", recv_records),
        ):
            if not edge_recs:
                edge_counts[edge_type] = 0
                continue
            # Chunk into batch_size pieces — each chunk is one HTTP call.
            n_ok = 0
            chunks = list(self.csv_loader.iter_batches(edge_recs, self.batch_size))
            for i, chunk in enumerate(chunks):
                t_batch = time.perf_counter()
                resp = self.client.upsert_batch_edges(edge_type, chunk)
                dur = (time.perf_counter() - t_batch) * 1000
                if "error" in resp:
                    _emit("upsert_tx",
                          f"  {edge_type} batch {i+1}/{len(chunks)}: ERROR after {dur:.0f}ms — "
                          f"{str(resp['error'])[:120]}")
                    break
                got = resp.get("loadSuccess", len(chunk))
                n_ok += got
                _emit("upsert_tx",
                      f"  {edge_type} batch {i+1}/{len(chunks)} ({len(chunk)}): "
                      f"ok in {dur:.0f}ms (cumulative={n_ok})")
            edge_counts[edge_type] = n_ok

        return {"loaded": tx_total, "edges": edge_counts}

    # ── Helpers ───────────────────────────────────────────────────────────────

    # CSV column → live TigerGraph attribute name per vertex type.
    _COLUMN_RENAME: dict[str, dict[str, str]] = {
        "Person": {
            "date_of_birth": "dob",
            "is_pep":        "pep_flag",
            "is_sanctioned": "sanctions_flag",
        },
        "Company": {
            "ein":          "tax_id",
            "company_type": "company_status",
            "is_offshore":  "offshore_flag",
            "is_shell":     "shell_company_flag",
        },
        "Account": {
            "account_number": "iban",
            "status":         "account_status",
        },
        "Address": {
            "street_address": "full_address",
        },
        "Device": {
            "fingerprint": "browser_fingerprint",
            "last_used":   "last_seen",
        },
        "Transaction": {
            "is_suspicious": "suspicious_flag",
        },
        "FraudRing": {
            "type": "ring_type",
        },
    }

    # Live-schema attribute whitelist per vertex type (authoritative).
    # Columns absent from this set are silently dropped before upsert.
    _VERTEX_ALLOWED_COLS: dict[str, set] = {
        "Person": {
            "v_id", "name", "dob", "nationality", "email", "phone",
            "risk_score", "pep_flag", "sanctions_flag", "aliases",
            "occupation", "source_country",
        },
        "Company": {
            "v_id", "name", "registration_country", "incorporation_date",
            "industry", "risk_score", "offshore_flag", "shell_company_flag",
            "aliases", "tax_id", "company_status",
        },
        "Account": {
            "v_id", "bank_name", "currency", "balance", "account_type",
            "account_status", "risk_score", "iban", "swift_code",
        },
        "Address": {
            "v_id", "full_address", "city", "country", "postal_code",
            "address_type", "risk_level",
        },
        "Device": {
            "v_id", "ip_address", "device_type", "geo_location",
            "operating_system", "browser_fingerprint", "risk_score",
        },
        "Transaction": {
            "v_id", "amount", "currency", "transaction_type", "timestamp",
            "risk_score", "suspicious_flag", "description", "channel",
        },
        "FraudRing": {
            "v_id", "name", "ring_type", "severity", "description",
        },
    }

    # Fields with DATETIME type in live schema
    _DATETIME_COLS = frozenset({
        "dob", "incorporation_date", "opened_date", "first_seen", "last_seen",
        "timestamp", "created_at",
    })
    # Fields with BOOL type
    _BOOL_COLS = frozenset({
        "pep_flag", "sanctions_flag", "offshore_flag", "shell_company_flag",
        "suspicious_flag",
    })
    # Fields with INT type
    _INT_COLS = frozenset({"risk_score"})
    # Fields with DOUBLE type
    _FLOAT_COLS = frozenset({"amount", "balance", "latitude", "longitude", "confidence_score"})

    def _to_tg_datetime(self, val: str) -> str:
        """Convert ISO/epoch datetime to TigerGraph DATETIME format YYYY-MM-DD HH:MM:SS."""
        try:
            # Try ISO string first
            dt = datetime.fromisoformat(str(val).replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            try:
                # Numeric epoch
                from datetime import timezone
                dt = datetime.fromtimestamp(float(val), tz=timezone.utc)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                return str(val)

    def _float_risk_to_level(self, v: str) -> str:
        """Convert numeric risk_score to Address risk_level string."""
        try:
            score = float(v)
            if score >= 0.7:
                return "high"
            elif score >= 0.4:
                return "medium"
            return "low"
        except Exception:
            return "low"

    def _clean_record(self, rec: dict, vertex_type: str) -> dict:
        rename_map = self._COLUMN_RENAME.get(vertex_type, {})
        allowed    = self._VERTEX_ALLOWED_COLS.get(vertex_type, set())
        cleaned: dict = {}

        for k, v in rec.items():
            key = k.strip()
            # Map id → v_id
            if key == "id":
                key = "v_id"
            # Apply per-type column renames
            key = rename_map.get(key, key)

            if v == "" or v is None:
                continue
            # Drop columns not in live schema whitelist
            if allowed and key not in allowed and key != "v_id":
                continue

            val: object = v
            if key in self._INT_COLS:
                try:
                    val = int(float(v))
                except (ValueError, TypeError):
                    continue
            elif key in self._FLOAT_COLS:
                try:
                    val = float(v)
                except (ValueError, TypeError):
                    continue
            elif key in self._BOOL_COLS:
                val = str(v).lower() in ("true", "1", "yes")
            elif key in self._DATETIME_COLS:
                val = self._to_tg_datetime(v)
            elif key == "aliases":
                val = v.split(",") if isinstance(v, str) and v else []
            # Address risk_level is STRING — convert from numeric risk_score if needed
            elif key == "risk_level" and v and v not in ("low", "medium", "high"):
                val = self._float_risk_to_level(v)

            cleaned[key] = val

        if "v_id" not in cleaned:
            for id_key in ("id", "person_id", "company_id", "account_id"):
                if id_key in rec:
                    cleaned["v_id"] = str(rec[id_key]).strip()
                    break

        return cleaned
