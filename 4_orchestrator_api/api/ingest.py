"""
Ingest API — real CSV upload + schema-validated promotion to TigerGraph.

Endpoints:
  POST /ingest/upload                multipart CSV upload; previews + saves
  GET  /ingest/list                  list previously uploaded files
  POST /ingest/promote/{upload_id}   load a recognized upload into TG
  POST /ingest/promote-ecosystem     load multiple uploads as one ecosystem
  GET  /ingest/upload/{upload_id}    inspect an upload (preview + status)
  DELETE /ingest/upload/{upload_id}  remove an upload from disk
  GET  /ingest/schema                document supported schemas

Schema recognition is FILENAME-first + HEADER-validated, with column-alias
normalization (snake / camel / case-insensitive). It supports:

  Vertices: Person, Company, Account, Address, Device, Transaction, FraudRing
  Edges:   *_edges.csv, *_ring_memberships.csv, *_ring_connections.csv,
           or any header containing a from/to + relationship column pair.

When TigerGraph is online, vertex/edge uploads are upserted into the live
graph and ALSO incrementally indexed into the OfflineFallback so the
upload survives a subsequent TG outage. Promotion is idempotent.
"""
from __future__ import annotations

import csv
import io
import json
import logging
import re
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from pydantic import BaseModel, Field

from orchestration.activation import get_activation

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
                   "description", "is_suspicious", "risk_score", "channel",
                   "reference", "is_layering", "is_placement",
                   "is_integration", "is_structuring", "is_smurfing",
                   "fraud_ring_id"},
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
    "FraudRing": {
        "id_col": "id",
        "required": {"id"},
        "accept": {"id", "name", "ring_type", "severity", "description",
                   "entity_count", "edge_count", "key_entities"},
        "csv_to_tg": {
            "name":        ("name", None),
            "ring_type":   ("ring_type", None),
            "severity":    ("severity", None),
            "description": ("description", None),
        },
    },
}


# ── Filename hints (singular / plural / common aliases) ───────────────────
#
# Filename is the strongest schema signal. We normalize (strip extension,
# lowercase, drop non-alphanumerics) and look up by exact match first, then
# by suffix/prefix containment so things like `customer_persons.csv` or
# `persons_2026.csv` still resolve.
_FILENAME_HINTS: dict[str, str] = {
    "person": "Person",     "persons": "Person",     "people": "Person",
    "company": "Company",   "companies": "Company",  "corp": "Company",
    "account": "Account",   "accounts": "Account",   "acct": "Account",
    "address": "Address",   "addresses": "Address",
    "device": "Device",     "devices": "Device",
    "transaction": "Transaction", "transactions": "Transaction",
    "tx": "Transaction",    "txn": "Transaction",    "txns": "Transaction",
    "fraudring": "FraudRing",   "fraudrings": "FraudRing",
    "ring": "FraudRing",        "rings": "FraudRing",
}

# Per-vertex ID column aliases. The first alias whose normalized form
# matches a header column wins. `id` is always tried first as a fallback.
_ID_ALIASES: dict[str, tuple[str, ...]] = {
    "Person":      ("id", "person_id", "personid", "entity_id", "uid"),
    "Company":     ("id", "company_id", "companyid", "entity_id", "corp_id"),
    "Account":     ("id", "account_id", "accountid", "entity_id", "acct_id"),
    "Address":     ("id", "address_id", "addressid"),
    "Device":      ("id", "device_id", "deviceid"),
    "Transaction": ("id", "transaction_id", "transactionid", "tx_id", "txn_id"),
    "FraudRing":   ("id", "ring_id", "ringid", "fraud_ring_id"),
}

# Token tests for edge-shaped files. Filename containment is a strong hint;
# header shape (a from-like + to-like column pair) is the definitive check.
_EDGE_FILENAME_TOKENS: tuple[str, ...] = (
    "edges", "edge", "relationship", "relationships", "rels",
    "memberships", "membership", "connections", "connection", "links",
)
_EDGE_FROM_ALIASES: tuple[str, ...] = (
    "from_id", "source_id", "source", "src", "from",
    # `entity_id` is used by 1_data_engine's *_ring_memberships.csv files
    # — the entity is always the "from" side of the membership edge.
    "entity_id",
)
_EDGE_TO_ALIASES: tuple[str, ...] = (
    "to_id", "target_id", "target", "dst", "to",
    "ring_id",  # *_ring_memberships.csv — the ring is always the "to" side
)
_EDGE_TYPE_ALIASES: tuple[str, ...] = (
    "relationship", "edge_type", "type", "rel", "relation", "relationship_kind",
)

# Filename → (default edge_type, from_vtype, to_vtype). Used when the file
# doesn't carry a relationship column itself (the *_ring_memberships.csv
# files in 1_data_engine output). Filename tokens are matched as substrings
# after normalization.
_EDGE_FILENAME_TYPE_MAP: tuple[tuple[str, str, str, str], ...] = (
    # (filename substring,                 default edge_type,                from_vtype,    to_vtype)
    ("personringmembership",               "PERSON_MEMBER_OF_RING",          "Person",      "FraudRing"),
    ("companyringmembership",              "COMPANY_MEMBER_OF_RING",         "Company",     "FraudRing"),
    ("accountringmembership",              "ACCOUNT_MEMBER_OF_RING",         "Account",     "FraudRing"),
    ("transactionringmembership",          "TRANSACTION_MEMBER_OF_RING",     "Transaction", "FraudRing"),
    ("deviceringconnection",               "DEVICE_CONNECTED_TO_RING",       "Device",      "FraudRing"),
    ("addressringconnection",              "ADDRESS_CONNECTED_TO_RING",      "Address",     "FraudRing"),
)


def _normalize(s: str) -> str:
    """Lowercase + drop non-alphanumerics. Used for header/filename matching."""
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


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


def _filename_hint(filename: str) -> str | None:
    """Match a filename against `_FILENAME_HINTS`.

    Resolution: exact normalized match wins; otherwise the longest matching
    token contained in the normalized filename wins. Returns the canonical
    vertex type name (`Person`, `Company`, …) or None.
    """
    if not filename:
        return None
    base = Path(filename).stem
    norm = _normalize(base)
    if norm in _FILENAME_HINTS:
        return _FILENAME_HINTS[norm]
    # Sort tokens longest-first so `transactions` matches before `tx`.
    for token in sorted(_FILENAME_HINTS.keys(), key=len, reverse=True):
        if token in norm:
            return _FILENAME_HINTS[token]
    return None


def _find_id_column(vtype: str, header: list[str]) -> str | None:
    """Return the actual header column matching one of vtype's ID aliases."""
    if not header:
        return None
    norm_map = {_normalize(c): c for c in header if c}
    for alias in _ID_ALIASES.get(vtype, ("id",)):
        actual = norm_map.get(_normalize(alias))
        if actual:
            return actual
    return None


def _detect_vertex_schema(filename: str, header: list[str]) -> dict | None:
    """Filename-first vertex detection. Returns a detection record or None.

    Detection record shape:
        {"kind": "vertex", "vertex_type": str, "id_col": str,
         "via": "filename" | "header_only"}
    """
    if not header:
        return None
    hint = _filename_hint(filename)
    if hint and hint in _SCHEMA_HINTS:
        id_col = _find_id_column(hint, header)
        if id_col:
            return {"kind": "vertex", "vertex_type": hint,
                    "id_col": id_col, "via": "filename"}
    # No filename hint, or filename hint had no matching ID column. Fall
    # back to header-only: try every vertex type and accept only if EXACTLY
    # one has its ID alias present in the header (otherwise ambiguous).
    candidates: list[tuple[str, str]] = []
    for vtype in _SCHEMA_HINTS:
        idc = _find_id_column(vtype, header)
        if idc:
            candidates.append((vtype, idc))
    if len(candidates) == 1:
        vt, idc = candidates[0]
        return {"kind": "vertex", "vertex_type": vt,
                "id_col": idc, "via": "header_only"}
    return None


def _detect_edge_schema(filename: str, header: list[str]) -> dict | None:
    """Detect edge-shaped files. Returns a detection record or None.

    Detection record shape:
        {"kind": "edge", "from_col": str, "to_col": str,
         "rel_col": str | None,
         "default_edge_type": str | None,
         "default_from_type": str | None,
         "default_to_type":   str | None,
         "via": "filename_map" | "header_only"}
    """
    if not header:
        return None
    norm_map = {_normalize(c): c for c in header if c}

    def _find(aliases: tuple[str, ...]) -> str | None:
        for a in aliases:
            actual = norm_map.get(_normalize(a))
            if actual:
                return actual
        return None

    from_col = _find(_EDGE_FROM_ALIASES)
    to_col   = _find(_EDGE_TO_ALIASES)
    rel_col  = _find(_EDGE_TYPE_ALIASES)

    if not (from_col and to_col):
        return None

    # Filename-based edge_type + endpoint types (highest signal — wins over
    # the row's relationship column when both are present, because the
    # filename encodes the EDGE TYPE while the relationship col may just
    # say "membership").
    base_norm = _normalize(Path(filename).stem)
    default_edge_type = None
    default_from_type = None
    default_to_type = None
    via = "header_only"
    for token, etype, ft, tt in _EDGE_FILENAME_TYPE_MAP:
        if token in base_norm:
            default_edge_type = etype
            default_from_type = ft
            default_to_type = tt
            via = "filename_map"
            break

    # Also require a filename "edge token" OR a relationship column — guards
    # against accidentally classifying a vertex file with a `from_id` column
    # as an edge.
    has_edge_token = any(t in base_norm for t in (
        _normalize(t) for t in _EDGE_FILENAME_TOKENS
    ))
    if not (has_edge_token or rel_col or default_edge_type):
        return None

    return {
        "kind": "edge",
        "from_col": from_col,
        "to_col":   to_col,
        "rel_col":  rel_col,
        "default_edge_type": default_edge_type,
        "default_from_type": default_from_type,
        "default_to_type":   default_to_type,
        "via":      via,
    }


def _detect_schema(filename: str, header: list[str]) -> dict | None:
    """Top-level schema detection. Vertex check first, edge fallback.

    Returns a detection record (see `_detect_vertex_schema` /
    `_detect_edge_schema`) or None when the file matches neither shape.
    """
    # Edge detection runs FIRST when the filename clearly says "edge" —
    # otherwise an edges.csv that happens to share an `id` column with a
    # vertex schema (rare but possible) would be mis-detected.
    base_norm = _normalize(Path(filename or "").stem)
    looks_edge = any(t in base_norm for t in (
        _normalize(t) for t in _EDGE_FILENAME_TOKENS
    ))
    if looks_edge:
        edge = _detect_edge_schema(filename, header)
        if edge:
            return edge
    vertex = _detect_vertex_schema(filename, header)
    if vertex:
        return vertex
    # Last resort: try edge detection even without filename token.
    return _detect_edge_schema(filename, header)


# Backward-compat shim: existing callers/manifests may reference the
# pre-refactor signature that returned just the vertex_type string.
def _detect_schema_legacy_vertex_only(header: list[str]) -> str | None:
    rec = _detect_vertex_schema("", header)
    return rec["vertex_type"] if rec else None


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

    detection = _detect_schema(file.filename, header) or {}
    detected_kind = detection.get("kind")  # "vertex" | "edge" | None
    detected_type = detection.get("vertex_type")  # legacy field; vertex only
    detection_issues: list[str] = []
    if not detection:
        detection_issues.append(
            "schema not recognized — filename did not match a known vertex type "
            "(persons/companies/accounts/addresses/devices/transactions/fraud_rings) "
            "and the header lacks an unambiguous from/to + relationship column pair."
        )
    elif detected_kind == "vertex" and not detection.get("id_col"):
        detection_issues.append(
            f"detected as {detected_type} but no ID column found — expected one of "
            f"{', '.join(_ID_ALIASES.get(detected_type or '', ('id',)))}"
        )

    manifest = {
        "upload_id":         upload_id,
        "filename":          file.filename,
        "size_bytes":        len(raw),
        "row_count":         row_count,
        "header":            header,
        "preview":           preview,
        "uploaded_at":       time.time(),
        # Legacy fields preserved so existing UI keeps working.
        "detected_type":     detected_type,
        # New richer detection record — UI uses `detected_kind` to render
        # vertex- vs edge-specific affordances. `detection` is the full
        # auto-detect result with the matched ID column / endpoint columns.
        "detected_kind":     detected_kind,
        "detection":         detection or None,
        "detection_issues":  detection_issues,
        "promoted":          False,
        "promotion":         None,
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


def _build_vertex_records(
    csv_text: str, vtype: str, id_col: str,
) -> tuple[list[dict], list[dict]]:
    """Parse CSV text into upsert-ready vertex records using the platform's
    canonical column-rename + coercion rules.

    Returns (records, skipped). `records` rows are FLAT dicts of the form
    `{"v_id": ..., <tg_attr>: <value>, ...}` ready for
    `GraphClient.upsert_batch_vertices(vtype, records)`. `skipped` rows
    carry `{"line": int, "reason": str}` for operator-readable feedback.
    """
    hints = _SCHEMA_HINTS.get(vtype)
    if not hints:
        return [], [{"line": 0, "reason": f"unknown vertex type {vtype}"}]
    csv_to_tg: dict[str, tuple[str, str | None]] = hints["csv_to_tg"]
    norm_id_col = _normalize(id_col)

    records: list[dict] = []
    skipped: list[dict] = []
    reader = csv.DictReader(io.StringIO(csv_text))
    for line_no, row in enumerate(reader, start=2):
        # ID column is identified case-insensitively against the actual
        # header — accommodates Person_ID, personId, etc.
        vid = ""
        for k, v in row.items():
            if k and _normalize(k) == norm_id_col:
                vid = (v or "").strip()
                break
        if not vid:
            skipped.append({"line": line_no, "reason": f"missing {id_col}"})
            continue
        rec: dict[str, Any] = {"v_id": vid}
        for k, v in row.items():
            if k is None or _normalize(k) == norm_id_col:
                continue
            mapping = csv_to_tg.get(k.lower())
            if not mapping:
                continue  # unknown columns dropped silently (TG would reject them)
            tg_attr, kind = mapping
            if v in (None, ""):
                continue
            rec[tg_attr] = _coerce(v, kind) if kind else v
        records.append(rec)
    return records, skipped


def _build_edge_records(
    csv_text: str, detection: dict,
) -> tuple[dict[tuple[str, str, str], list[dict]], list[dict]]:
    """Parse an edge CSV into upsert-ready edge records, grouped by the
    (edge_type, from_type, to_type) triple — matching the contract
    `GraphClient.upsert_batch_edges(edge_type, records)` expects.

    Returns (records_by_triple, skipped) where each record carries
    from_id / to_id / from_type / to_type + any extra attribute columns.
    """
    from_col = detection["from_col"]
    to_col   = detection["to_col"]
    rel_col  = detection.get("rel_col")
    default_edge_type = detection.get("default_edge_type")
    default_from_type = detection.get("default_from_type")
    default_to_type   = detection.get("default_to_type")

    grouped: dict[tuple[str, str, str], list[dict]] = {}
    skipped: list[dict] = []
    reader = csv.DictReader(io.StringIO(csv_text))
    for line_no, row in enumerate(reader, start=2):
        from_id = (row.get(from_col) or "").strip()
        to_id   = (row.get(to_col)   or "").strip()
        if not from_id or not to_id:
            skipped.append({"line": line_no, "reason": "missing from/to id"})
            continue
        # Edge type: filename-mapped default wins; else fall back to the
        # row's relationship column; else unknown (skip with reason).
        rel = default_edge_type or (
            (row.get(rel_col) or "").strip().upper() if rel_col else ""
        )
        if not rel:
            skipped.append({"line": line_no, "reason": "no edge type (filename or relationship col)"})
            continue
        # Endpoint types: filename-mapped default wins; else look in the
        # row (from_type / to_type columns, used by edges.csv).
        ft = default_from_type or (row.get("from_type") or "").strip() or "Person"
        tt = default_to_type   or (row.get("to_type")   or "").strip() or "FraudRing"
        # Attribute columns: any column other than the from/to/rel/type ones
        # gets passed along as a TG edge attribute. TG silently rejects
        # unknown attrs, so we don't try to enforce a schema here.
        skip_cols = {from_col, to_col, rel_col, "from_type", "to_type"}
        skip_norm = {_normalize(c) for c in skip_cols if c}
        attrs: dict[str, Any] = {}
        for k, v in row.items():
            if k is None or _normalize(k) in skip_norm:
                continue
            if v in (None, ""):
                continue
            attrs[k.lower()] = v
        rec = {
            "from_id": from_id, "to_id": to_id,
            "from_type": ft,    "to_type": tt,
            **attrs,
        }
        grouped.setdefault((rel, ft, tt), []).append(rec)
    return grouped, skipped


def _rehydrate_offline_fallback(client, records: list[dict], vtype: str) -> int:
    """Best-effort: register newly-promoted vertices into the in-process
    OfflineFallback so the upload survives a subsequent TG outage. Returns
    the number of records added. Failures are non-fatal — we never block
    the promote flow on offline-index updates."""
    try:
        fb = getattr(client, "_offline_fallback", None)
        if fb is None:
            return 0
        # OfflineFallback exposes `_entity_index`; add directly. (The class
        # has no public add API today — this is the minimal intrusion that
        # keeps offline-mode investigatability honest after a promote.)
        added = 0
        for rec in records:
            vid = rec.get("v_id")
            if not vid:
                continue
            data = {k: v for k, v in rec.items() if k != "v_id"}
            fb._entity_index[vid] = {"type": vtype, "data": data}
            added += 1
        return added
    except Exception:
        return 0


@router.post("/ingest/promote/{upload_id}")
def promote_upload(request: Request, upload_id: str) -> dict:
    """Load an upload into the LIVE TigerGraph instance.

    Handles both vertex and edge uploads — the detection result on the
    manifest determines which upsert path runs. Idempotent (TG upserts
    merge by primary id). When the orchestrator's OfflineFallback is
    initialized, promoted vertices are also indexed into it so the upload
    remains investigatable during a subsequent TG outage.
    """
    m = _read_manifest(upload_id)
    if not m:
        raise HTTPException(status_code=404, detail="upload not found")

    detection = m.get("detection") or {}
    kind = detection.get("kind") or ("vertex" if m.get("detected_type") else None)

    if not kind:
        raise HTTPException(
            status_code=400,
            detail=(
                "upload schema not recognized. Filename did not match a vertex "
                "type (persons/companies/accounts/addresses/devices/transactions/"
                "fraud_rings) and headers did not contain an edge-shaped "
                "(from/to + relationship) layout. Promotion blocked."
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
            detail=(
                "TigerGraph is in offline-fallback mode — promotion suspended. "
                "Use POST /orchestrator/reconnect to retry the TG connection, "
                "or run `python -m 3_graph_intelligence_core health` to diagnose."
            ),
        )

    csv_text = _csv_path(upload_id).read_text(encoding="utf-8-sig", errors="replace")

    # ── Vertex promotion ─────────────────────────────────────────────────
    if kind == "vertex":
        vtype = detection.get("vertex_type") or m.get("detected_type")
        id_col = detection.get("id_col") or _SCHEMA_HINTS[vtype]["id_col"]
        records, skipped = _build_vertex_records(csv_text, vtype, id_col)

        t0 = time.time()
        try:
            result = client.upsert_batch_vertices(vtype, records)
        except Exception as e:
            logger.exception("vertex upsert failure")
            raise HTTPException(status_code=502, detail=f"TigerGraph upsert failed: {e}")
        elapsed_s = round(time.time() - t0, 2)

        offline_added = _rehydrate_offline_fallback(client, records, vtype)

        promotion = {
            "kind":          "vertex",
            "vertex_type":   vtype,
            "id_col":        id_col,
            "records":       len(records),
            "skipped":       skipped,
            "tg_response":   result,
            "offline_index_added": offline_added,
            "elapsed_s":     elapsed_s,
            "promoted_at":   time.time(),
        }

    # ── Edge promotion ───────────────────────────────────────────────────
    else:
        grouped, skipped = _build_edge_records(csv_text, detection)
        total_records = sum(len(v) for v in grouped.values())

        t0 = time.time()
        batch_results: list[dict] = []
        total_upserted = 0
        for (etype, ft, tt), recs in grouped.items():
            try:
                r = client.upsert_batch_edges(etype, recs)
            except Exception as e:
                logger.exception("edge upsert failure for %s/%s/%s", etype, ft, tt)
                r = {"error": f"{type(e).__name__}: {e}"}
            batch_results.append({
                "edge_type": etype, "from_type": ft, "to_type": tt,
                "records":   len(recs),
                "result":    r,
            })
            if isinstance(r, dict):
                total_upserted += int(r.get("loadSuccess") or 0)
        elapsed_s = round(time.time() - t0, 2)

        promotion = {
            "kind":           "edge",
            "edge_type":      detection.get("default_edge_type"),
            "records":        total_records,
            "upserted":       total_upserted,
            "skipped":        skipped,
            "batch_results":  batch_results,
            "elapsed_s":      elapsed_s,
            "promoted_at":    time.time(),
        }
        result = {"loadSuccess": total_upserted,
                  "loadFailure": total_records - total_upserted,
                  "batches":     len(batch_results)}

    m["promoted"] = True
    m["promotion"] = promotion
    _write_manifest(upload_id, m)

    # Trigger a vertex-count refresh so downstream UIs reflect the new state.
    try:
        counts = client.get_vertex_counts()
    except Exception:
        counts = None

    # Auto-activate the uploaded ecosystem so the operator-facing
    # environment reflects the deliberate promote. If sample is already
    # active, this auto-promotes to "hybrid".
    if promotion["records"] > 0:
        try:
            get_activation().activate(
                "uploaded",
                by="auto_post_promote",
                details={"upload_id": upload_id, "kind": promotion["kind"],
                         "records": promotion["records"]},
            )
        except Exception as e:
            logger.warning("activation update after promote failed: %s", e)

    return {
        "upload_id":     upload_id,
        "kind":          promotion["kind"],
        "vertex_type":   promotion.get("vertex_type"),
        "edge_type":     promotion.get("edge_type"),
        "records":       promotion["records"],
        "skipped":       len(promotion.get("skipped") or []),
        "tg_response":   result,
        "elapsed_s":     promotion["elapsed_s"],
        "vertex_counts": counts,
        "activation":    get_activation().current().to_dict(),
    }


class _EcosystemRequest(BaseModel):
    upload_ids: list[str] = Field(
        ...,
        description="Upload IDs to promote as a single ecosystem. Vertices are "
                    "promoted before edges automatically — explicit ordering is "
                    "not required.",
    )


@router.post("/ingest/promote-ecosystem")
def promote_ecosystem(request: Request, body: _EcosystemRequest) -> dict:
    """Promote multiple uploads as one ingestion job.

    Vertices are upserted first, edges second — required ordering since
    edges referencing a from/to vertex assume the vertex exists. Partial
    failures don't roll back (TG upserts are not transactional across
    batches), but every per-upload result is surfaced so the operator can
    re-run a failed file.
    """
    if not body.upload_ids:
        raise HTTPException(status_code=400, detail="upload_ids is required")

    # Order: vertices first, edges second. Within each kind, preserve
    # caller order.
    vertex_ids: list[str] = []
    edge_ids:   list[str] = []
    unknown:    list[str] = []
    for uid in body.upload_ids:
        m = _read_manifest(uid)
        if not m:
            unknown.append(uid)
            continue
        kind = (m.get("detection") or {}).get("kind") or (
            "vertex" if m.get("detected_type") else None
        )
        if kind == "vertex":
            vertex_ids.append(uid)
        elif kind == "edge":
            edge_ids.append(uid)
        else:
            unknown.append(uid)

    t0 = time.time()
    stages: list[dict] = []
    for uid in vertex_ids + edge_ids:
        try:
            res = promote_upload(request, uid)
            res["upload_id"] = uid
            stages.append(res)
        except HTTPException as e:
            stages.append({"upload_id": uid, "error": e.detail, "status": e.status_code})
        except Exception as e:
            stages.append({"upload_id": uid, "error": f"{type(e).__name__}: {e}"})

    try:
        counts = request.app.state.orchestrator._client.get_vertex_counts()
    except Exception:
        counts = None

    return {
        "stages":         stages,
        "ordering":       {"vertices_first": vertex_ids, "edges_after": edge_ids,
                           "unrecognized":   unknown},
        "elapsed_s":      round(time.time() - t0, 2),
        "vertex_counts":  counts,
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

    total_records = sum(s["records"] for s in stages)

    # Auto-activate the sample environment so subsequent reads of
    # `/ingest/environment` reflect the operator's deliberate "Launch
    # Sample Ecosystem" choice. If uploads are already active, this
    # promotes the state to "hybrid".
    if total_records > 0:
        try:
            get_activation().activate(
                "sample",
                by="auto_post_ingest_sample",
                profile=profile,
                details={"total_records": total_records,
                         "vertex_counts": vertex_counts or {}},
            )
        except Exception as e:
            logger.warning("activation update after /ingest/sample failed: %s", e)

    return {
        "profile":         profile,
        "csv_dir":         str(csv_dir.relative_to(_PROJECT_ROOT)),
        "stages":          stages,
        "elapsed_s":       round(time.time() - t_global, 2),
        "vertex_counts":   vertex_counts,
        "total_records":   total_records,
        "total_skipped":   sum(s["skipped"] for s in stages),
        "activation":      get_activation().current().to_dict(),
    }


class _ActivationRequest(BaseModel):
    kind: str = Field(
        ...,
        description="One of 'empty' | 'sample' | 'uploaded' | 'hybrid'. "
                    "Use POST /ingest/sample to actually load sample data; "
                    "this endpoint only flips the operator-facing gate.",
    )
    profile: Optional[str] = Field(
        default=None,
        description="Profile name (relevant for sample/hybrid). Defaults to "
                    "the current profile or 'small'.",
    )
    by: Optional[str] = Field(
        default="operator",
        description="Short reason — surfaced on the activation record.",
    )


@router.get("/ingest/activation")
def get_environment_activation() -> dict:
    """Return the current operator-controlled activation record. Cheap."""
    return get_activation().current().to_dict()


@router.post("/ingest/activate")
def activate_environment(body: _ActivationRequest) -> dict:
    """Flip the operator-facing environment activation gate.

    This is intentionally separate from the data-loading endpoints. It
    only changes how `/ingest/environment` reports state — it does NOT
    move data in or out of TigerGraph. Use POST /ingest/sample to
    actually load sample CSVs into the live graph.

    Common flows:
      • clear an environment without dropping TG data → POST /ingest/clear
      • re-mark a prior sample run as active → activate kind=sample
      • acknowledge an externally-loaded upload → activate kind=uploaded
    """
    valid = ("empty", "sample", "uploaded", "hybrid")
    if body.kind not in valid:
        raise HTTPException(status_code=400,
                            detail=f"kind must be one of {valid}")
    rec = get_activation().activate(
        body.kind,  # type: ignore[arg-type]
        by=body.by or "operator",
        profile=body.profile,
    )
    return rec.to_dict()


@router.post("/ingest/clear")
def clear_environment() -> dict:
    """Operator-facing 'unload current environment'. Flips activation back
    to `empty`. Does NOT mutate TigerGraph — the underlying live graph
    retains sample + uploaded data; this only resets the UI gate so the
    next visitor sees the deliberate Launch landing.

    To physically drop data from TG, use the GSQL admin interface — the
    platform intentionally does not expose DROP via HTTP.
    """
    return get_activation().clear(by="operator").to_dict()


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
    activation = get_activation().current()

    return _shape_env(
        tg_online=not offline,
        vertex_counts=counts,
        uploads=uploads,
        reconnect_attempted=reconnect_attempted,
        probe_failed=probe_failed,
        fresh_probe=probe,
        activation=activation,
    )


def _shape_env(
    *,
    tg_online: bool,
    vertex_counts: dict,
    uploads: list,
    reconnect_attempted: bool,
    probe_failed: bool,
    fresh_probe: bool,
    activation=None,
) -> dict:
    """Compose the single source of truth for environment state + readiness.

    Activation gate: when `activation.kind == "empty"`, the report shows
    0 vertices + all readiness gates closed + mode="empty", regardless of
    what the underlying TG holds. This preserves the operator-facing
    "nothing activated until I launch" contract. The raw live counts are
    surfaced separately under `physical_state.tg_vertex_counts` so
    operators can verify the live graph hasn't been mutated by activation.
    """
    promoted = sum(1 for u in uploads if u.get("promoted"))
    # Live physical counts (what TG actually holds) — preserved separately
    # so a transparency reviewer can verify activation never mutates TG.
    physical_total = sum(v for v in vertex_counts.values() if isinstance(v, int))

    # Activation gate. When the operator hasn't activated anything we
    # honestly report a zero-state environment, even if TG holds data.
    activation_kind = (activation.kind if activation else "empty")
    if activation_kind == "empty":
        effective_counts: dict = {}
        total = 0
    else:
        effective_counts = vertex_counts
        total = physical_total

    hydrated = tg_online and total > 0
    # When TG is offline, the orchestrator's OfflineFallback can still
    # answer investigations against the local CSV dataset. We surface this
    # as a "degraded" state — not "blocked" — so the UI can show it
    # accurately. We only claim local availability when the profile dir
    # exists on disk; absent that, fallback would be empty.
    local_profiles = _list_available_profiles()
    local_dataset_available = bool(local_profiles)
    # Investigations require an activated environment AND either a hydrated
    # graph or a local fallback. If activation_kind is empty, the operator
    # must explicitly Launch first.
    activated = activation_kind != "empty"
    can_investigate = activated and (hydrated or local_dataset_available)

    # Reasons differ across four states: empty activation, hydrated TG,
    # offline-with-local-CSV, and fully unavailable. We never claim
    # hydration when only the fallback is available, and we never claim
    # readiness when the operator hasn't activated an environment — the
    # `mode`, `activation.kind`, and `ready` flags stay honest.
    if not activated:
        graph_reason = (
            "no environment activated · click Launch Sample Ecosystem "
            "or promote uploads to begin"
        )
    elif tg_online:
        graph_reason = "tigergraph reachable · schema accessible"
    elif local_dataset_available:
        graph_reason = (
            "tigergraph unreachable · OfflineFallback armed against local dataset "
            f"({', '.join(local_profiles)})"
        )
    else:
        graph_reason = "tigergraph unreachable · no local dataset · investigations blocked"

    if not activated:
        topology_reason = "no environment activated · 0 vertices in view"
    elif hydrated:
        topology_reason = f"{total:,} vertices · hydrated"
    elif tg_online:
        topology_reason = "graph empty · launch sample ecosystem or upload"
    elif local_dataset_available:
        topology_reason = "live topology unavailable · local CSV serving entity lookups"
    else:
        topology_reason = "tigergraph offline · no local dataset"

    if not activated:
        retrieval_reason = "no environment activated · retrieval idle"
    elif hydrated:
        retrieval_reason = "graphRAG retrieval operational"
    elif local_dataset_available:
        retrieval_reason = "degraded · entity ranking + dossier available against local CSV"
    else:
        retrieval_reason = "retrieval requires a hydrated graph or local dataset"

    if not activated:
        benchmark_reason = "no environment activated · benchmark idle (artifact inspection always available)"
    elif hydrated:
        benchmark_reason = "benchmark runner ready for live execution"
    elif local_dataset_available:
        # Benchmark runner uses its own AdaptiveDataLoader → still functional.
        benchmark_reason = "live runs degraded · artifact + cached run inspection available"
    else:
        benchmark_reason = "benchmark requires a hydrated graph or local dataset"

    if not activated:
        reasoning_reason = "no environment activated · reasoning idle"
    elif hydrated:
        reasoning_reason = "cognitive layer ready"
    elif local_dataset_available:
        reasoning_reason = "degraded · reasoning over offline-fallback retrieval"
    else:
        reasoning_reason = "reasoning requires retrieval"

    # When activation is empty, ALL readiness gates are closed regardless
    # of TG state — we don't claim the platform can investigate until the
    # operator has activated an environment.
    if not activated:
        readiness = {
            "graph":     {"ready": False, "reason": graph_reason},
            "topology":  {"ready": False, "reason": topology_reason},
            "retrieval": {"ready": False, "reason": retrieval_reason},
            "benchmark": {"ready": False, "reason": benchmark_reason},
            "reasoning": {"ready": False, "reason": reasoning_reason},
        }
    else:
        readiness = {
            "graph":     {"ready": tg_online,       "reason": graph_reason},
            # Topology is "ready" only on live TG hydration — we don't claim
            # the local CSV reconstructs the full live topology.
            "topology":  {"ready": hydrated,        "reason": topology_reason},
            # Retrieval / benchmark / reasoning flip "ready" when EITHER hydrated
            # or a local dataset is present. Reasons disclose which path.
            "retrieval": {"ready": can_investigate, "reason": retrieval_reason},
            "benchmark": {"ready": can_investigate, "reason": benchmark_reason},
            "reasoning": {"ready": can_investigate, "reason": reasoning_reason},
        }

    # Operational mode: 4 distinct states the UI renders differently.
    if not activated:
        mode = "empty"
    elif tg_online:
        mode = "live_tigergraph"
    elif local_dataset_available:
        mode = "offline_local_dataset"
    else:
        mode = "unavailable"

    # Activation summary surfaced at the top level so the UI doesn't
    # have to dig into a nested object for the most-load-bearing field.
    activation_dict = activation.to_dict() if activation else {
        "kind": "empty", "label": "no environment activated",
    }

    return {
        "tigergraph_online":   tg_online,
        # Effective counts — respects activation gate.
        "vertex_counts":       effective_counts,
        "total_vertices":      total,
        "uploads_total":       len(uploads),
        "uploads_promoted":    promoted,
        "supported_profiles":  local_profiles,
        "reconnect_attempted": reconnect_attempted,
        "fresh_probe":         fresh_probe,
        "probe_failed":        probe_failed,
        "environment_kind":    _classify_env(promoted, total),
        "mode":                mode,
        "local_dataset_available": local_dataset_available,
        # investigation_ready: requires explicit activation AND a working
        # retrieval substrate (live TG or local fallback).
        "investigation_ready": can_investigate,
        "readiness":           readiness,
        # Operator-facing activation record — the UI uses
        # `activation.kind`/`activation.label` to render the launch CTA
        # versus the active-environment header.
        "activation":          activation_dict,
        # Physical-state escape hatch: the raw live TG vertex counts even
        # when activation is empty. Transparency-only — confirms that
        # activation does not mutate TigerGraph (sample data + uploads
        # remain physically present; activation is purely a UX gate).
        "physical_state": {
            "tg_vertex_counts": vertex_counts,
            "tg_total_vertices": physical_total,
            "note": (
                "Activation is a UX gate, not a physical scope. The platform "
                "has a single live TigerGraph graph; activation controls "
                "whether the UI exposes its contents."
            ),
        },
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
    """Return the schema hints so the UI can document expected CSV layouts."""
    vertex_schemas = [
        {
            "vertex_type":   vtype,
            "id_aliases":    list(_ID_ALIASES.get(vtype, ("id",))),
            "filename_hints": sorted(
                k for k, v in _FILENAME_HINTS.items() if v == vtype
            ),
            "required":      sorted(hints["required"]),
            "optional":      sorted(hints["accept"] - hints["required"]),
        }
        for vtype, hints in _SCHEMA_HINTS.items()
    ]
    return {
        # Canonical field name.
        "vertex_schemas": vertex_schemas,
        # Backward-compat alias — older UI clients read `supported`. Both
        # fields point at the same list so future schema changes only need
        # one update.
        "supported":      vertex_schemas,
        "edge_schema": {
            "from_aliases":   list(_EDGE_FROM_ALIASES),
            "to_aliases":     list(_EDGE_TO_ALIASES),
            "type_aliases":   list(_EDGE_TYPE_ALIASES),
            "filename_tokens": list(_EDGE_FILENAME_TOKENS),
            "filename_typed_maps": [
                {"filename_substring": tok, "edge_type": etype,
                 "from_vertex_type":   ft,  "to_vertex_type": tt}
                for tok, etype, ft, tt in _EDGE_FILENAME_TYPE_MAP
            ],
        },
        "notes": [
            "Detection is filename-first, then header-validated. Both singular and plural filenames work (person.csv ≡ persons.csv ≡ people.csv).",
            "ID columns are matched case-insensitively across snake / camel / lowercase variants (person_id ≡ personId ≡ PERSON_ID).",
            "Edge files with from/to + relationship columns auto-detect — *_edges.csv, *_ring_memberships.csv, *_ring_connections.csv all supported out of the box.",
            "Unrecognized columns are dropped at promotion time — TG rejects unknown attrs.",
            "Promotion is idempotent (upsert by primary id). Re-running is safe.",
            "Use POST /ingest/promote-ecosystem to promote multiple uploads as a single job; vertices are upserted before edges automatically.",
            "Promoted vertices are also indexed into the orchestrator's OfflineFallback so the upload remains investigatable if TG later goes offline.",
            "Live promotion requires the orchestrator to be ONLINE with a reachable TigerGraph.",
        ],
    }
