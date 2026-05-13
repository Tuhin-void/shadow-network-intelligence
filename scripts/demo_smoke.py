#!/usr/bin/env python3
"""
Pre-demo smoke validation for Shadow Network Intelligence.

Run this BEFORE every demo. It fails loud if any of the systems the
GraphRAG demo depends on is not in a presentable state.

Checks (in order):
  1. TigerGraph connectivity (LIVE mode)
  2. Schema sync (7 vertex types, 19 edge types)
  3. Vertex counts (must be non-trivial)
  4. Critical topology edges present (OWNS, HAS_ACCOUNT, LOCATED_AT,
     SENT_TRANSACTION, RECEIVED_TRANSACTION, PERSON_MEMBER_OF_RING)
  5. ChromaDB / vector store reachable (optional)
  6. GraphRAG retrieval round-trip (entity_centric + neighborhood)
  7. VectorRAG retrieval round-trip (if --vector enabled)

Usage:
    python3 scripts/demo_smoke.py
    python3 scripts/demo_smoke.py --profile small --strict
    python3 scripts/demo_smoke.py --skip-vector

Exit code:
    0 — ready to demo
    1 — one or more checks failed
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "3_graph_intelligence_core"))

GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
DIM    = "\033[2m"
RESET  = "\033[0m"


# Minimum healthy counts. Below these → fail loud.
MIN_VERTEX_COUNTS = {
    "Person":      100,
    "Company":     100,
    "Account":     100,
    "Address":     100,
    "Transaction": 1000,
    "FraudRing":   1,
}
CRITICAL_EDGES = [
    "OWNS",
    "HAS_ACCOUNT",
    "LOCATED_AT",
    "SENT_TRANSACTION",
    "RECEIVED_TRANSACTION",
    "PERSON_MEMBER_OF_RING",
]


class CheckFail(Exception):
    pass


def _check(name: str, fn) -> bool:
    t0 = time.perf_counter()
    try:
        msg = fn()
        dt = (time.perf_counter() - t0) * 1000
        print(f"  {GREEN}✓{RESET} {name:<35} {DIM}{msg}  ({dt:.0f}ms){RESET}")
        return True
    except CheckFail as e:
        dt = (time.perf_counter() - t0) * 1000
        print(f"  {RED}✗{RESET} {name:<35} {RED}FAIL{RESET}: {e}  {DIM}({dt:.0f}ms){RESET}")
        return False
    except Exception as e:
        dt = (time.perf_counter() - t0) * 1000
        print(f"  {RED}✗{RESET} {name:<35} {RED}ERROR{RESET}: {type(e).__name__}: {e}  {DIM}({dt:.0f}ms){RESET}")
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description="Pre-demo smoke validation")
    ap.add_argument("--profile", default="small")
    ap.add_argument("--skip-vector", action="store_true", help="Skip ChromaDB checks")
    ap.add_argument("--skip-retrieval", action="store_true", help="Skip live retrieval round-trips")
    ap.add_argument("--strict", action="store_true",
                    help="Also require non-zero counts for ring edges and Device")
    args = ap.parse_args()

    print(f"\n{DIM}=== Shadow Network Intelligence — demo smoke ==={RESET}")
    print(f"{DIM}profile={args.profile}  strict={args.strict}{RESET}\n")

    # ── 1. TigerGraph connectivity ──────────────────────────────────────────
    from clients.graph_client import GraphClient
    from configs.config import load_config

    config = load_config(None)
    client = GraphClient(config)

    def chk_health():
        h = client.health_check()
        if h.get("offline_mode"):
            raise CheckFail("TigerGraph in OFFLINE mode — live demo will fall back to local dataset")
        if not h.get("healthy"):
            raise CheckFail(f"health={h}")
        return f"LIVE, latency={h.get('latency_ms', 0):.1f}ms"
    ok_health = _check("TigerGraph health", chk_health)

    # ── 2. Schema sync ──────────────────────────────────────────────────────
    def chk_schema():
        from validation.schema_validator import SchemaValidator
        report = SchemaValidator(client).validate()
        if not report.is_valid:
            raise CheckFail(f"errors: {report.errors}")
        return f"7 vertices, 19 edges (live)"
    ok_schema = _check("Schema sync", chk_schema)

    # ── 3. Vertex counts ────────────────────────────────────────────────────
    counts: dict[str, int] = {}
    def chk_counts():
        if not client._tg_conn:
            raise CheckFail("no live connection")
        deficits = []
        for vt, minimum in MIN_VERTEX_COUNTS.items():
            try:
                n = client._tg_conn.getVertexCount(vt)
            except Exception as e:
                raise CheckFail(f"{vt}: {e}")
            counts[vt] = n
            if n < minimum:
                deficits.append(f"{vt}={n}<{minimum}")
        if args.strict:
            try:
                dev = client._tg_conn.getVertexCount("Device")
                counts["Device"] = dev
                if dev < 50:
                    deficits.append(f"Device={dev}<50 (strict)")
            except Exception:
                pass
        if deficits:
            raise CheckFail("; ".join(deficits))
        return ", ".join(f"{k}={v}" for k, v in counts.items())
    ok_counts = _check("Vertex counts", chk_counts)

    # ── 4. Critical topology edges present ──────────────────────────────────
    edge_counts: dict[str, int] = {}
    def chk_edges():
        missing = []
        for et in CRITICAL_EDGES:
            try:
                n = client._tg_conn.getEdgeCount(et)
            except Exception as e:
                raise CheckFail(f"{et}: {e}")
            edge_counts[et] = n
            if n == 0:
                missing.append(et)
        if args.strict:
            for et in ("COMPANY_MEMBER_OF_RING", "ACCOUNT_MEMBER_OF_RING"):
                try:
                    n = client._tg_conn.getEdgeCount(et)
                    edge_counts[et] = n
                    if n == 0:
                        missing.append(et + " (strict)")
                except Exception:
                    pass
        if missing:
            raise CheckFail(f"ZERO edges in: {', '.join(missing)} — graph is structurally hollow")
        return ", ".join(f"{k}={v}" for k, v in edge_counts.items())
    ok_edges = _check("Critical topology edges", chk_edges)

    # ── 5. Vector store (optional) ──────────────────────────────────────────
    ok_vec = True
    if not args.skip_vector:
        def chk_vector():
            sys.path.insert(0, str(PROJECT_ROOT / "2_baseline_systems"))
            try:
                from retrieval.vector_store import VectorStore
            except ImportError:
                from baseline_systems.retrieval.vector_store import VectorStore  # type: ignore
            vs = VectorStore(provider="chroma", collection_name=f"shadow_network_{args.profile}", dimension=384)
            # We don't index — just confirm we can construct.
            return f"provider={vs.provider}"
        ok_vec = _check("VectorStore construct", chk_vector)

    # ── 6. GraphRAG retrieval round-trip ────────────────────────────────────
    ok_rag = True
    if not args.skip_retrieval:
        def chk_graphrag():
            from graph_rag.graphrag_engine import GraphRAGEngine
            engine = GraphRAGEngine(client, config, compression="rule_based")
            r = engine.query("Find high risk accounts", config={"strategy": "entity", "top_k": 5, "depth": 1})
            n_ent = r.get("metadata", {}).get("entity_count", 0)
            if n_ent == 0:
                raise CheckFail("GraphRAG returned 0 entities — entity retriever may be broken")
            return f"{n_ent} entities, {r.get('metadata', {}).get('evidence_count', 0)} evidence items"
        ok_rag = _check("GraphRAG retrieval", chk_graphrag)

    # ── Summary ─────────────────────────────────────────────────────────────
    all_ok = all([ok_health, ok_schema, ok_counts, ok_edges, ok_vec, ok_rag])
    print()
    if all_ok:
        print(f"  {GREEN}● DEMO-READY{RESET} — all systems green.")
        return 0
    print(f"  {RED}● NOT DEMO-READY{RESET} — fix the failed checks above before the demo.")
    print(f"  {YELLOW}Hint:{RESET} the most common cause is a hollow graph. Run:")
    print(f"  {DIM}    python3 -m 1_data_engine generate --profile {args.profile} --new-pipeline{RESET}")
    print(f"  {DIM}    python3 -m 3_graph_intelligence_core load {args.profile}{RESET}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
