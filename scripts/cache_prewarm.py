#!/usr/bin/env python3
"""
Cache prewarm — drives first-query latency from 15-25s down to <5s.

Strategy:
  1. Pull the top-N highest-risk Persons, Companies, Accounts.
  2. Pull all FraudRing vertices (small set, e.g. 15-50).
  3. For each, do ONE `get_neighbors` call. This populates:
       - GraphClient._neighbor_cache  (per-vertex edges)
       - GraphClient._vertex_cache    (the vertex itself via getVerticesById)
  4. For each of the top-K candidates, compute topology features once via
     `EntityCentricRetriever._compute_topology_features`. This populates
     the topology cache so the rerank step doesn't pay for it on the first
     adversarial query.

Should be run BEFORE a demo or benchmark. Idempotent. No mutation of TG state.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "3_graph_intelligence_core"))


def _emit(msg: str) -> None:
    print(msg, flush=True)


def run(top_n: int) -> int:
    from clients.graph_client import GraphClient
    from configs.config import load_config
    from retrievers.entity_centric import EntityCentricRetriever

    config = load_config(None)
    client = GraphClient(config)

    if client._offline_mode:
        _emit("Cannot prewarm in OFFLINE mode")
        return 1

    conn = client._tg_conn
    retriever = EntityCentricRetriever(client)

    t_total = time.perf_counter()

    # ── Stage 1: pull candidates ─────────────────────────────────────────
    t0 = time.perf_counter()
    candidates: list[tuple[str, str]] = []   # (v_id, vertex_type)
    for vtype in ["Person", "Company", "Account"]:
        try:
            vs = conn.getVertices(vtype, limit=top_n)
        except Exception as e:
            _emit(f"  WARN: getVertices({vtype}) failed: {e}")
            continue
        # Sort by risk descending so high-risk warms first.
        vs_sorted = sorted(
            vs,
            key=lambda v: float((v.get("attributes") or {}).get("risk_score") or 0),
            reverse=True,
        )
        for v in vs_sorted:
            v_id = v.get("v_id", "")
            if v_id:
                candidates.append((v_id, vtype))
    # Always include FraudRing vertices — small set, critical for ring queries.
    try:
        rings = conn.getVertices("FraudRing", limit=50)
        for r in rings:
            v_id = r.get("v_id", "")
            if v_id:
                candidates.append((v_id, "FraudRing"))
    except Exception as e:
        _emit(f"  WARN: getVertices(FraudRing) failed: {e}")
    _emit(f"[1/3] candidates: {len(candidates)} entities ({time.perf_counter()-t0:.2f}s)")

    # ── Stage 2: warm get_neighbors cache ────────────────────────────────
    t0 = time.perf_counter()
    n_warmed = 0
    for v_id, vtype in candidates:
        try:
            client.get_neighbors(v_id, vertex_type=vtype, limit=50)
            n_warmed += 1
        except Exception:
            pass
    _emit(f"[2/3] get_neighbors warmed: {n_warmed} entries "
          f"({time.perf_counter()-t0:.2f}s)")

    # ── Stage 3: warm topology features cache ────────────────────────────
    t0 = time.perf_counter()
    n_topo = 0
    # Only warm non-FraudRing entities — topology rerank doesn't touch rings.
    for v_id, vtype in candidates:
        if vtype == "FraudRing":
            continue
        try:
            retriever._compute_topology_features(v_id, vtype)
            n_topo += 1
        except Exception:
            pass
    _emit(f"[3/3] topology features warmed: {n_topo} entries "
          f"({time.perf_counter()-t0:.2f}s)")

    hits = client._cache_hits
    misses = client._cache_misses
    _emit(f"\n  cache stats after prewarm: hits={hits} misses={misses}")
    _emit(f"  total prewarm time: {time.perf_counter()-t_total:.2f}s")
    _emit("\nReady for fast first-query response.")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--top-n", type=int, default=30,
                    help="Top-N highest-risk entities per type to warm")
    args = ap.parse_args()
    sys.exit(run(args.top_n))
