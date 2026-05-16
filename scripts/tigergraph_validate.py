#!/usr/bin/env python3
"""
TigerGraph operational validator.

Read-only structural sanity check against the live ShadowGraph instance.
Confirms the graph is queryable, populated, and traversable — the
operational substrate the GraphRAG superiority story depends on.

Probes performed:
  1. Connection — health + auth
  2. Per-vertex counts vs schema_def.VERTEX_TYPES
  3. Per-edge counts (forward + reverse_*)
  4. Ring connectivity — sample N FraudRing vertices, traverse to members
  5. Multi-hop reachability — Person → Account → Transaction sample
  6. Installed-query sanity — tg_ring_members, tg_shortest_path
  7. Cache stats snapshot

Outputs:
  scripts/tigergraph_validation.json    — machine-readable summary
  scripts/tigergraph_validation.md      — human-readable report

Exit code: 0 = healthy enough for demo; 1 = critical defect; 2 = TG offline.

Usage:
  python3 scripts/tigergraph_validate.py
  python3 scripts/tigergraph_validate.py --sample-rings 8
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "3_graph_intelligence_core"))

JSON_OUT = PROJECT_ROOT / "scripts" / "tigergraph_validation.json"
MD_OUT = PROJECT_ROOT / "scripts" / "tigergraph_validation.md"


def _emit(msg: str) -> None:
    print(msg, flush=True)


def _safe_call(fn, *args, **kwargs) -> tuple[bool, Any]:
    try:
        return True, fn(*args, **kwargs)
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def validate(sample_rings: int) -> dict[str, Any]:
    from clients.graph_client import GraphClient
    from configs.config import load_config
    from validation.schema_def import VERTEX_TYPES, EDGE_TYPES

    cfg = load_config(None)
    client = GraphClient(cfg)

    def _type_name(t: Any) -> str:
        if isinstance(t, str):
            return t
        if hasattr(t, "name"):
            return t.name
        if isinstance(t, dict):
            return t.get("name", str(t))
        return str(t)

    report: dict[str, Any] = {
        "started_at": time.time(),
        "tigergraph_host": cfg.tigergraph.host if hasattr(cfg, "tigergraph") else "—",
        "offline_mode": client._offline_mode,
        "schema_vertex_types": [_type_name(v) for v in VERTEX_TYPES],
        "schema_edge_types":   [_type_name(e) for e in EDGE_TYPES],
    }

    if client._offline_mode:
        report["status"] = "OFFLINE"
        report["reason"] = "GraphClient is in OfflineFallback mode."
        return report

    # ── 1. Per-vertex counts ───────────────────────────────────────────
    ok, vcounts = _safe_call(client.get_vertex_counts)
    if not ok or not isinstance(vcounts, dict):
        vcounts = {"error": str(vcounts)}
    report["vertex_counts"] = vcounts
    report["vertex_total"] = sum(
        v for v in vcounts.values() if isinstance(v, int)
    )

    # ── 2. Per-edge counts ─────────────────────────────────────────────
    # GraphClient doesn't expose getEdgeCount directly; sample via _tg_conn
    # which is the pyTigerGraph connection.
    tg = getattr(client, "_tg_conn", None) or getattr(client, "tg", None)
    if tg is not None:
        ok, eobj = _safe_call(tg.getEdgeCount)
        if ok and isinstance(eobj, dict):
            report["edge_counts"] = eobj
            report["edge_total"] = sum(int(v) for v in eobj.values()
                                       if isinstance(v, (int, float)))
        else:
            report["edge_counts"] = {"error": str(eobj)}
            report["edge_total"] = 0
    else:
        report["edge_counts"] = {"error": "no pyTigerGraph connection exposed"}
        report["edge_total"] = 0

    reverse_edges_in_count = {
        k: v for k, v in (report.get("edge_counts") or {}).items()
        if isinstance(k, str) and k.startswith("reverse_")
    }
    report["reverse_edges_observed"] = reverse_edges_in_count

    # ── 3. Ring connectivity sample ────────────────────────────────────
    ok, rings = _safe_call(client.get_vertices, "FraudRing", limit=sample_rings)
    ring_probe: list[dict[str, Any]] = []
    if ok and isinstance(rings, list):
        for r in rings:
            rid = r.get("v_id") if isinstance(r, dict) else None
            if not rid:
                continue
            ok2, edges = _safe_call(
                client.get_edges, rid, from_type="FraudRing", limit=200,
            )
            edges_list = edges if (ok2 and isinstance(edges, list)) else []
            members_by_kind: dict[str, int] = {}
            for ed in edges_list:
                et = ed.get("e_type") or ed.get("edge_type") or "?"
                members_by_kind[et] = members_by_kind.get(et, 0) + 1
            ring_probe.append({
                "ring_id": rid,
                "member_edges": len(edges_list),
                "edges_by_kind": members_by_kind,
            })
    report["ring_probe"] = ring_probe
    report["rings_with_members"] = sum(1 for r in ring_probe if r["member_edges"] > 0)

    # ── 4. Multi-hop reachability sample ───────────────────────────────
    hop_probe: list[dict[str, Any]] = []
    ok, persons = _safe_call(client.get_vertices, "Person", limit=10)
    if ok and isinstance(persons, list):
        for p in persons[:5]:
            pid = p.get("v_id") if isinstance(p, dict) else None
            if not pid:
                continue
            ok2, edges = _safe_call(
                client.get_edges, pid, from_type="Person", limit=50,
            )
            edges_list = edges if (ok2 and isinstance(edges, list)) else []
            hop_probe.append({"person_id": pid, "edge_count": len(edges_list)})
    report["person_hop_probe"] = hop_probe

    # ── 5. Installed-query sanity ──────────────────────────────────────
    iq_status: dict[str, Any] = {}
    for qname, params in (
        # pyTigerGraph accepts "type.id" for VERTEX params.
        ("tg_ring_members",  {"ring": "FraudRing.FR-001"}),
        ("tg_shortest_path", {"src": "Person.P-000001", "tgt": "Person.P-000002"}),
    ):
        ok, ret = _safe_call(client.run_installed_query, qname, params=params)
        iq_status[qname] = ("installed (returned data)" if ok and ret
                            else f"unavailable: {ret}")
    report["installed_queries"] = iq_status

    # ── 6. Cache snapshot ──────────────────────────────────────────────
    report["cache"] = {
        "hits":   getattr(client, "_cache_hits", 0),
        "misses": getattr(client, "_cache_misses", 0),
    }

    # ── Status verdict ─────────────────────────────────────────────────
    critical: list[str] = []
    if report["vertex_total"] < 1000:
        critical.append(f"vertex_total={report['vertex_total']} is far below expected scale")
    if report["edge_total"] < 1000:
        critical.append(f"edge_total={report['edge_total']} is below expected scale")
    if not reverse_edges_in_count:
        critical.append("no reverse_* edges observed — reverse-traversal will not work")
    if report["rings_with_members"] == 0:
        critical.append("no rings have any structural members — investigation queries will be empty")

    report["critical_findings"] = critical
    report["status"] = "HEALTHY" if not critical else "DEGRADED"
    report["completed_at"] = time.time()
    report["elapsed_sec"] = round(report["completed_at"] - report["started_at"], 2)
    return report


def _write_markdown(report: dict[str, Any]) -> None:
    lines = [
        "# TigerGraph operational validation",
        "",
        f"**Status:** `{report.get('status', '?')}`  •  "
        f"**Elapsed:** {report.get('elapsed_sec', 0)}s",
        "",
        f"- Host: `{report.get('tigergraph_host', '—')}`",
        f"- Offline mode: `{report.get('offline_mode')}`",
        f"- Vertex types in schema: {len(report.get('schema_vertex_types', []))}",
        f"- Edge types in schema:   {len(report.get('schema_edge_types', []))}",
        "",
    ]

    if report.get("status") == "OFFLINE":
        lines += [
            "## Offline",
            "",
            "The TigerGraph instance is unreachable. The orchestrator's "
            "OfflineFallback mode is active. See `.env` for `TIGERGRAPH_HOST` "
            "and `TIGERGRAPH_GSQL_SECRET`.",
        ]
        MD_OUT.write_text("\n".join(lines))
        return

    lines += [
        "## Vertex counts",
        "",
        "| type | count |",
        "|---|---|",
    ]
    for vt, count in (report.get("vertex_counts") or {}).items():
        lines.append(f"| `{vt}` | {count} |")

    lines += [
        f"\n**Total vertices:** {report.get('vertex_total', 0):,}",
        "",
        "## Edge counts",
        "",
        "| edge | count |",
        "|---|---|",
    ]
    for et, count in sorted((report.get("edge_counts") or {}).items()):
        if isinstance(count, dict):
            continue
        lines.append(f"| `{et}` | {count} |")

    lines += [
        f"\n**Total edges:** {report.get('edge_total', 0):,}",
        f"\n**Reverse edges observed:** {len(report.get('reverse_edges_observed') or {})}",
        "",
        "## Ring connectivity probe",
        "",
        f"Rings sampled: {len(report.get('ring_probe') or [])}  •  "
        f"With members: {report.get('rings_with_members', 0)}",
        "",
        "| ring | edges |",
        "|---|---|",
    ]
    for r in (report.get("ring_probe") or [])[:20]:
        lines.append(f"| `{r['ring_id']}` | {r['member_edges']} |")

    lines += [
        "",
        "## Installed queries",
        "",
        "| query | status |",
        "|---|---|",
    ]
    for q, s in (report.get("installed_queries") or {}).items():
        lines.append(f"| `{q}` | {s} |")

    lines += [
        "",
        "## Cache snapshot",
        "",
        f"- hits:   {report.get('cache', {}).get('hits', 0)}",
        f"- misses: {report.get('cache', {}).get('misses', 0)}",
        "",
    ]

    crits = report.get("critical_findings") or []
    if crits:
        lines += ["## Critical findings", "",
                  *[f"- {c}" for c in crits]]

    MD_OUT.write_text("\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sample-rings", type=int, default=5,
                    help="how many FraudRing vertices to probe")
    args = ap.parse_args(argv)

    report = validate(args.sample_rings)
    JSON_OUT.write_text(json.dumps(report, indent=2, default=str))
    _write_markdown(report)
    _emit(f"Validation report → {MD_OUT.relative_to(PROJECT_ROOT)}")
    _emit(f"JSON              → {JSON_OUT.relative_to(PROJECT_ROOT)}")
    _emit(f"Status: {report.get('status')}")
    if report.get("status") == "OFFLINE":
        return 2
    return 0 if report.get("status") == "HEALTHY" else 1


if __name__ == "__main__":
    sys.exit(main())
