"""
Ingest API — real CSV upload + schema-validated promotion to TigerGraph.

Endpoints:
  POST /ingest/upload                multipart CSV upload; previews + saves
  GET  /ingest/list                  list previously uploaded files
  POST /ingest/promote/{upload_id}   load a recognized upload into TG
  GET  /ingest/upload/{upload_id}    inspect an upload (preview + status)
  DELETE /ingest/upload/{upload_id}  remove an upload from disk

Schema recognition: the upload header is sniffed and matched against the
canonical CSV shapes produced by `1_data_engine`:

  persons.csv      → upsert as Person vertices
  companies.csv    → upsert as Company vertices
  accounts.csv     → upsert as Account vertices
  addresses.csv    → upsert as Address vertices
  devices.csv      → upsert as Device vertices
  transactions.csv → upsert as Transaction vertices

Unrecognized headers can still be uploaded and previewed but cannot be
promoted (promotion returns 400 with the documented expected columns).
"""
from __future__ import annotations

import csv
import io
import json
import logging
import sys
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request, UploadFile, File

logger = logging.getLogger(__name__)
router = APIRouter()

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_UPLOAD_ROOT = _PROJECT_ROOT / "outputs" / "uploads"
_UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

# Per-vertex schema hints. Each entry maps CSV column names (as produced
# by `1_data_engine`) to the LIVE TigerGraph attribute names + their type
# coercion. CSV columns absent from `csv_to_tg` are dropped silently at
# promotion time — TG complains loudly on unknown attrs.
#
# Sources of truth:
#   • CSV layout: outputs/small/csv/*.csv (1_data_engine output)
#   • TG schema:  3_graph_intelligence_core/validation/schema_def.py
_SCHEMA_HINTS: dict[str, dict[str, Any]] = {
    "Person": {
        "id_col": "id",
        "required": {"id"},
        # CSV columns the platform accepts (must be a subset of these)
        "accept": {"id", "name", "first_name", "last_name", "date_of_birth",
                   "nationality", "tax_id", "risk_score", "is_pep",
                   "is_sanctioned", "is_watched", "email", "phone",
                   "occupation", "source_country"},
        # CSV → TG attribute remapping + type coercion
        "csv_to_tg": {
            "name":          ("name", None),
            "date_of_birth": ("dob", None),
            "nationality":   ("nationality", None),
            "email":         ("email", None),
            "phone":         ("phone", None),
            "risk_score":    ("risk_score", "int_pct"),
            "is_pep":        ("pep_flag", "bool"),
            "is_sanctioned": ("sanctions_flag", "bool"),
            "occupation":    ("occupation", None),
            "source_country": ("source_country", None),
        },
    },
    "Company": {
        "id_col": "id",
        "required": {"id"},
        "accept": {"id", "name", "ein", "industry", "company_type",
                   "incorporation_date", "is_offshore", "is_shell",
                   "risk_score", "registration_country", "tax_id",
                   "company_status"},
        "csv_to_tg": {
            "name":               ("name", None),
            "registration_country": ("registration_country", None),
            "incorporation_date": ("incorporation_date", None),
            "industry":           ("industry", None),
            "risk_score":         ("risk_score", "int_pct"),
            "is_offshore":        ("offshore_flag", "bool"),
            "is_shell":           ("shell_company_flag", "bool"),
            "tax_id":             ("tax_id", None),
            "ein":                ("tax_id", None),       # EIN ≡ tax_id slot
            "company_status":     ("company_status", None),
        },
    },
    "Account": {
        "id_col": "id",
        "required": {"id"},
        "accept": {"id", "account_number", "account_type", "owner_id",
                   "owner_type", "balance", "currency", "risk_score",
                   "status", "bank_name", "iban", "swift_code"},
        "csv_to_tg": {
            "bank_name":      ("bank_name", None),
            "currency":       ("currency", None),
            "balance":        ("balance", "float"),
            "account_type":   ("account_type", None),
            "status":         ("account_status", None),
            "risk_score":     ("risk_score", "int_pct"),
            "iban":           ("iban", None),
            "swift_code":     ("swift_code", None),
        },
    },
    "Address": {
        "id_col": "id",
        "required": {"id"},
        "accept": {"id", "street", "street_address", "city", "state", "country",
                   "postal_code", "address_type", "is_shell_location",
                   "risk_score", "full_address", "risk_level"},
        "csv_to_tg": {
            "street_address": ("full_address", None),
            "street":         ("full_address", None),
            "full_address":   ("full_address", None),
            "city":           ("city", None),
            "country":        ("country", None),
            "postal_code":    ("postal_code", None),
            "address_type":   ("address_type", None),
        },
    },
    "Device": {
        "id_col": "id",
        "required": {"id"},
        "accept": {"id", "device_type", "ip_address", "operating_system",
                   "fingerprint", "geo_location", "risk_score",
                   "first_seen", "last_seen", "browser_fingerprint"},
        "csv_to_tg": {
            "ip_address":          ("ip_address", None),
            "device_type":         ("device_type", None),
            "operating_system":    ("operating_system", None),
            "fingerprint":         ("browser_fingerprint", None),
            "browser_fingerprint": ("browser_fingerprint", None),
            "geo_location":        ("geo_location", None),
            "risk_score":          ("risk_score", "int_pct"),
        },
    },
    "Transaction": {
        "id_col": "id",
        "required": {"id"},
        "accept": {"id", "amount", "currency", "transaction_type",
                   "timestamp", "status", "from_account", "to_account",
                   "description", "is_suspicious", "risk_score", "channel"},
        "csv_to_tg": {
            "amount":            ("amount", "float"),
            "currency":          ("currency", None),
            "transaction_type":  ("transaction_type", None),
            "timestamp":         ("timestamp", None),
            "risk_score":        ("risk_score", "int_pct"),
            "is_suspicious":     ("suspicious_flag", "bool"),
            "description":       ("description", None),
            "channel":           ("channel", None),
        },
    },
}


def _coerce(raw: Any, kind: str) -> Any:
    """Best-effort type coercion for TG attribute values."""
    s = str(raw).strip()
    if kind == "bool":
        return s.lower() in ("true", "1", "yes", "y", "t")
    if kind == "float":
        try:
            return float(s)
        except ValueError:
            return 0.0
    if kind == "int":
        try:
            return int(float(s))
        except ValueError:
            return 0
    if kind == "int_pct":
        # The live schema declares risk_score as INT, but the dataset uses
        # 0.0-1.0 floats. Coerce to 0-100 ints (TG-compatible).
        try:
            f = float(s)
            if f <= 1.0:
                return max(0, min(100, int(round(f * 100))))
            return max(0, min(100, int(round(f))))
        except ValueError:
            return 0
    return raw

_PREVIEW_ROWS = 5
_MAX_UPLOAD_BYTES = 32 * 1024 * 1024  # 32 MB cap


# ── Helpers ────────────────────────────────────────────────────────────────


def _upload_dir(upload_id: str) -> Path:
    return _UPLOAD_ROOT / upload_id


def _manifest_path(upload_id: str) -> Path:
    return _upload_dir(upload_id) / "manifest.json"


def _csv_path(upload_id: str) -> Path:
    return _upload_dir(upload_id) / "data.csv"


def _detect_schema(header: list[str]) -> str | None:
    """Return the matching vertex type, or None if no schema fits."""
    cols = {c.strip().lower() for c in header}
    for vtype, hints in _SCHEMA_HINTS.items():
        req = {c.lower() for c in hints["required"]}
        accept = {c.lower() for c in hints["accept"]}
        if not req.issubset(cols):
            continue
        # All present columns must be within the accept set (strict mode).
        if cols.issubset(accept):
            return vtype
    return None


def _read_manifest(upload_id: str) -> dict | None:
    p = _manifest_path(upload_id)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def _write_manifest(upload_id: str, m: dict) -> None:
    _manifest_path(upload_id).write_text(json.dumps(m, indent=2, default=str))


def _list_uploads() -> list[dict]:
    out: list[dict] = []
    if not _UPLOAD_ROOT.exists():
        return out
    for d in sorted(_UPLOAD_ROOT.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if not d.is_dir():
            continue
        m = _read_manifest(d.name)
        if m:
            out.append(m)
    return out


# ── Endpoints ─────────────────────────────────────────────────────────────


@router.post("/ingest/upload")
async def upload_csv(file: UploadFile = File(...)) -> dict:
    """
    Accept a CSV file, persist it to outputs/uploads/<id>/, sniff the
    schema against the live TigerGraph vertex types, return preview rows.
    No graph mutation happens here — promotion is a separate explicit step.
    """
    if not file.filename or not file.filename.lower().endswith((".csv", ".tsv", ".txt")):
        raise HTTPException(status_code=400, detail="only .csv / .tsv / .txt uploads are supported")

    upload_id = f"upl_{uuid.uuid4().hex[:10]}"
    udir = _upload_dir(upload_id)
    udir.mkdir(parents=True, exist_ok=True)

    raw = await file.read()
    if len(raw) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413,
                            detail=f"upload exceeds {_MAX_UPLOAD_BYTES} bytes")
    _csv_path(upload_id).write_bytes(raw)

    # Parse header + preview
    text = raw.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
    except StopIteration:
        raise HTTPException(status_code=400, detail="empty file")
    preview: list[list[str]] = []
    row_count = 0
    for row in reader:
        if len(preview) < _PREVIEW_ROWS:
            preview.append(row)
        row_count += 1

    detected_type = _detect_schema(header)

    manifest = {
        "upload_id":      upload_id,
        "filename":       file.filename,
        "size_bytes":     len(raw),
        "row_count":      row_count,
        "header":         header,
        "preview":        preview,
        "uploaded_at":    time.time(),
        "detected_type":  detected_type,
        "promoted":       False,
        "promotion":      None,
    }
    _write_manifest(upload_id, manifest)
    return manifest


@router.get("/ingest/list")
def list_uploads() -> dict:
    return {"uploads": _list_uploads()}


@router.get("/ingest/upload/{upload_id}")
def get_upload(upload_id: str) -> dict:
    m = _read_manifest(upload_id)
    if not m:
        raise HTTPException(status_code=404, detail="upload not found")
    return m


@router.delete("/ingest/upload/{upload_id}")
def delete_upload(upload_id: str) -> dict:
    udir = _upload_dir(upload_id)
    if not udir.exists():
        raise HTTPException(status_code=404, detail="upload not found")
    for child in udir.iterdir():
        child.unlink()
    udir.rmdir()
    return {"ok": True, "upload_id": upload_id}


@router.post("/ingest/promote/{upload_id}")
def promote_upload(request: Request, upload_id: str) -> dict:
    """
    Load an upload into the LIVE TigerGraph instance via the orchestrator's
    GraphClient. Only uploads whose header matched a known schema are
    accepted. Each row becomes a vertex; the operation is idempotent
    (upsert).

    Returns the real `inserted_count` and any per-row warnings from TG.
    """
    m = _read_manifest(upload_id)
    if not m:
        raise HTTPException(status_code=404, detail="upload not found")
    vtype = m.get("detected_type")
    if not vtype:
        raise HTTPException(
            status_code=400,
            detail=(
                "upload schema not recognized. Expected header to match one of: "
                + ", ".join(_SCHEMA_HINTS.keys())
                + ". Promotion blocked."
            ),
        )

    orch = getattr(request.app.state, "orchestrator", None)
    if orch is None:
        raise HTTPException(status_code=503, detail="orchestrator not initialized")
    client = getattr(orch, "_client", None)
    if client is None:
        raise HTTPException(status_code=503, detail="graph client unavailable")
    if getattr(client, "_offline_mode", True):
        raise HTTPException(
            status_code=503,
            detail="TigerGraph is in offline-fallback mode — promotion suspended",
        )

    # Parse the CSV into upsert records.
    text = _csv_path(upload_id).read_text(encoding="utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    hints = _SCHEMA_HINTS[vtype]
    id_col = hints["id_col"]
    csv_to_tg: dict[str, tuple[str, str | None]] = hints["csv_to_tg"]

    records: list[dict] = []
    skipped: list[dict] = []
    for line_no, row in enumerate(reader, start=2):
        vid = (row.get(id_col) or "").strip()
        if not vid:
            skipped.append({"line": line_no, "reason": "missing id"})
            continue
        # GraphClient.upsert_batch_vertices expects FLAT records:
        # {v_id: ..., <tg_attr>: <value>, ...}
        # CSV columns are renamed to TG attribute names + type-coerced;
        # columns absent from csv_to_tg are dropped (TG rejects unknown attrs).
        rec: dict[str, Any] = {"v_id": vid}
        for k, v in row.items():
            if k is None:
                continue
            kl = k.lower()
            if kl == id_col:
                continue
            mapping = csv_to_tg.get(kl)
            if not mapping:
                continue
            tg_attr, kind = mapping
            if v in (None, ""):
                continue
            rec[tg_attr] = _coerce(v, kind) if kind else v
        records.append(rec)

    t0 = time.time()
    try:
        result = client.upsert_batch_vertices(vtype, records)
    except Exception as e:
        logger.exception("upsert failure")
        raise HTTPException(status_code=502, detail=f"TigerGraph upsert failed: {e}")
    elapsed_s = round(time.time() - t0, 2)

    promotion = {
        "vertex_type":  vtype,
        "records":      len(records),
        "skipped":      skipped,
        "tg_response":  result,
        "elapsed_s":    elapsed_s,
        "promoted_at":  time.time(),
    }

    m["promoted"] = True
    m["promotion"] = promotion
    _write_manifest(upload_id, m)

    # Trigger a vertex-count refresh so downstream UIs reflect the new state.
    try:
        counts = client.get_vertex_counts()
    except Exception:
        counts = None
    return {
        "upload_id":       upload_id,
        "vertex_type":     vtype,
        "records":         len(records),
        "skipped":         len(skipped),
        "tg_response":     result,
        "elapsed_s":       elapsed_s,
        "vertex_counts":   counts,
    }


def _bulk_csv_upsert(client, csv_path: Path, vtype: str) -> dict:
    """
    Read a CSV file matching `vtype`'s schema and upsert into the live
    graph. Returns {records, skipped, elapsed_s, tg_response}.

    Reuses the same column-rename + coercion logic as /ingest/promote.
    """
    if not csv_path.exists():
        return {"records": 0, "skipped": 0, "elapsed_s": 0,
                "tg_response": {"error": f"file not found: {csv_path.name}"}}
    hints = _SCHEMA_HINTS[vtype]
    id_col = hints["id_col"]
    csv_to_tg: dict[str, tuple[str, str | None]] = hints["csv_to_tg"]
    text = csv_path.read_text(encoding="utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    records: list[dict] = []
    skipped: list[dict] = []
    for line_no, row in enumerate(reader, start=2):
        vid = (row.get(id_col) or "").strip()
        if not vid:
            skipped.append({"line": line_no, "reason": "missing id"})
            continue
        rec: dict[str, Any] = {"v_id": vid}
        for k, v in row.items():
            if k is None:
                continue
            mapping = csv_to_tg.get(k.lower())
            if not mapping:
                continue
            tg_attr, kind = mapping
            if v in (None, ""):
                continue
            rec[tg_attr] = _coerce(v, kind) if kind else v
        records.append(rec)
    t0 = time.time()
    try:
        tg_response = client.upsert_batch_vertices(vtype, records)
    except Exception as e:
        tg_response = {"error": f"{type(e).__name__}: {e}"}
    return {
        "records":    len(records),
        "skipped":    len(skipped),
        "elapsed_s":  round(time.time() - t0, 2),
        "tg_response": tg_response,
    }


@router.post("/ingest/sample")
def launch_sample_ecosystem(request: Request,
                            profile: str = "small") -> dict:
    """
    One-click bulk hydration of the curated benchmark fraud ecosystem.

    Reads outputs/{profile}/csv/*.csv and upserts each vertex bundle into
    the live TigerGraph instance. Returns per-stage real counts + timing.

    This is REAL ingestion — every vertex/edge written is observable via
    `client.get_vertex_counts()` after completion. There is no simulation.
    """
    orch = getattr(request.app.state, "orchestrator", None)
    if orch is None:
        raise HTTPException(status_code=503, detail="orchestrator not initialized")
    client = getattr(orch, "_client", None)
    if client is None:
        raise HTTPException(status_code=503, detail="graph client unavailable")
    if getattr(client, "_offline_mode", True):
        raise HTTPException(
            status_code=503,
            detail="TigerGraph is in offline-fallback mode — sample ingestion suspended",
        )

    csv_dir = _PROJECT_ROOT / "outputs" / profile / "csv"
    if not csv_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                f"No curated bundle at outputs/{profile}/csv. "
                f"Generate first: python -m 1_data_engine generate --profile {profile} --new-pipeline"
            ),
        )

    # Bulk-load each vertex type in dependency order (no FK validation
    # required for upserts — TG accepts in any order, but this is the
    # natural reading order for an analyst).
    plan = [
        ("Person",      csv_dir / "persons.csv"),
        ("Company",     csv_dir / "companies.csv"),
        ("Account",     csv_dir / "accounts.csv"),
        ("Address",     csv_dir / "addresses.csv"),
        ("Device",      csv_dir / "devices.csv"),
        ("Transaction", csv_dir / "transactions.csv"),
    ]

    t_global = time.time()
    stages: list[dict] = []
    for vtype, path in plan:
        result = _bulk_csv_upsert(client, path, vtype)
        result["vertex_type"] = vtype
        result["file"]        = path.name
        stages.append(result)

    # Capture the live post-ingest vertex counts for confirmation.
    try:
        vertex_counts = client.get_vertex_counts()
    except Exception:
        vertex_counts = None

    return {
        "profile":         profile,
        "csv_dir":         str(csv_dir.relative_to(_PROJECT_ROOT)),
        "stages":          stages,
        "elapsed_s":       round(time.time() - t_global, 2),
        "vertex_counts":   vertex_counts,
        "total_records":   sum(s["records"] for s in stages),
        "total_skipped":   sum(s["skipped"] for s in stages),
    }


@router.get("/ingest/environment")
def active_environment(request: Request, probe: bool = False) -> dict:
    """
    Surface the active intelligence environment: live TG state, vertex
    counts per type, recent upload activity, and a structured readiness
    verdict so the UI can show one honest "investigation-ready" signal
    instead of inferring it from raw counts.

    Self-healing: if the client is currently in offline-fallback mode,
    we trigger `client.reconnect_if_offline()` (rate-limited) so the
    long-running orchestrator recovers automatically when the workspace
    is unpaused — no restart required.

    Args:
        probe: when true, force a fresh `get_vertex_counts()` round-trip
            to TG even if the client thinks it's online — this catches
            "online flag is stale, TG is actually down" cases. Caller
            opts into the latency.
    """
    orch = getattr(request.app.state, "orchestrator", None)
    if orch is None:
        raise HTTPException(status_code=503, detail="orchestrator not initialized")
    client = getattr(orch, "_client", None)
    if client is None:
        return _shape_env(
            tg_online=False, vertex_counts={}, uploads=_list_uploads(),
            reconnect_attempted=False, probe_failed=False, fresh_probe=False,
        )

    reconnect_attempted = False
    if getattr(client, "_offline_mode", True):
        # Try to self-heal. The method is rate-limited internally so
        # high-frequency callers can't hammer TG.
        reconnect_attempted = True
        try:
            client.reconnect_if_offline()
        except Exception:
            pass

    offline = getattr(client, "_offline_mode", True)
    counts: dict[str, int] = {}
    probe_failed = False
    if not offline:
        # The cached `_offline_mode` flag is best-effort. When `probe=True`
        # is set we force a real TG round-trip and treat a failure as
        # honestly offline so the UI stops showing stale `online` state.
        try:
            counts = client.get_vertex_counts() or {}
        except Exception:
            counts = {}
            if probe:
                probe_failed = True
                offline = True
                try:
                    # Mark the client offline so subsequent calls reflect
                    # the truth rather than relying on the next failed
                    # call to flip the flag.
                    client._offline_mode = True
                except Exception:
                    pass

    uploads = _list_uploads()

    return _shape_env(
        tg_online=not offline,
        vertex_counts=counts,
        uploads=uploads,
        reconnect_attempted=reconnect_attempted,
        probe_failed=probe_failed,
        fresh_probe=probe,
    )


def _shape_env(
    *,
    tg_online: bool,
    vertex_counts: dict,
    uploads: list,
    reconnect_attempted: bool,
    probe_failed: bool,
    fresh_probe: bool,
) -> dict:
    """Compose the single source of truth for environment state + readiness."""
    promoted = sum(1 for u in uploads if u.get("promoted"))
    total = sum(v for v in vertex_counts.values() if isinstance(v, int))
    hydrated = tg_online and total > 0
    # Retrieval / benchmark / reasoning are downstream — they need at
    # least a hydrated graph. We don't fake readiness signals when the
    # underlying surface isn't ready.
    readiness = {
        "graph": {
            "ready": tg_online,
            "reason": (
                "tigergraph reachable · schema accessible"
                if tg_online else "tigergraph unreachable · investigations blocked"
            ),
        },
        "topology": {
            "ready": hydrated,
            "reason": (
                f"{total:,} vertices · hydrated"
                if hydrated else
                "graph empty · launch sample ecosystem or upload"
                if tg_online else "tigergraph offline"
            ),
        },
        "retrieval": {
            "ready": hydrated,
            "reason": (
                "graphRAG retrieval operational"
                if hydrated else "retrieval requires a hydrated graph"
            ),
        },
        "benchmark": {
            "ready": hydrated,
            "reason": (
                "benchmark runner ready for live execution"
                if hydrated else "benchmark requires a hydrated graph"
            ),
        },
        "reasoning": {
            "ready": hydrated,
            "reason": (
                "cognitive layer ready"
                if hydrated else "reasoning requires retrieval"
            ),
        },
    }
    return {
        "tigergraph_online":   tg_online,
        "vertex_counts":       vertex_counts,
        "total_vertices":      total,
        "uploads_total":       len(uploads),
        "uploads_promoted":    promoted,
        "supported_profiles":  _list_available_profiles(),
        "reconnect_attempted": reconnect_attempted,
        "fresh_probe":         fresh_probe,
        "probe_failed":        probe_failed,
        "environment_kind":    _classify_env(promoted, total),
        "investigation_ready": hydrated,
        "readiness":           readiness,
    }


def _classify_env(promoted: int, total: int) -> str:
    """One word for what flavor of environment is currently active.

    NB: the platform has a single live TigerGraph graph — sample data and
    promoted uploads merge by vertex ID. This classification reflects
    *what was loaded most recently*, not isolated namespaces.
    """
    if total <= 0:
        return "empty"
    if promoted > 0:
        return "uploaded"
    return "sample"


def _list_available_profiles() -> list[str]:
    base = _PROJECT_ROOT / "outputs"
    if not base.exists():
        return []
    return sorted(
        d.name for d in base.iterdir()
        if d.is_dir() and (d / "csv").exists()
    )


@router.get("/ingest/schema")
def supported_schemas() -> dict:
    """Return the schema hints so the UI can document expected CSV headers."""
    return {
        "supported": [
            {
                "vertex_type": vtype,
                "required":    sorted(hints["required"]),
                "optional":    sorted(hints["accept"] - hints["required"]),
            }
            for vtype, hints in _SCHEMA_HINTS.items()
        ],
        "notes": [
            "Headers are case-insensitive.",
            "Recognized CSV columns are renamed to their live TigerGraph attribute counterparts.",
            "Unrecognized columns are dropped at promotion time (TG rejects unknown attrs).",
            "Promotion is idempotent — re-uploading the same data is safe.",
            "Promotion requires the orchestrator to be online with a live TigerGraph connection.",
        ],
    }
