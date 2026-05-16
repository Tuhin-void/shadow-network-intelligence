#!/usr/bin/env python3
"""
Cross-reference corpus enricher.

Reads the already-generated dataset from `outputs/{profile}/csv/` and writes
narrative dossier documents that DELIBERATELY reference multiple entities
across rings, addresses, and devices — boosting cross-document entity
recurrence and total token volume WITHOUT touching the existing generators,
CSV outputs, or graph topology.

Why this exists:
  • Strengthens VectorRAG so the benchmark comparison is fair (no straw-man).
  • Increases corpus token count toward the 1M–2M target.
  • Produces documents whose ANSWER still requires a graph join — each
    dossier only narrates ONE angle; the full picture needs multi-doc
    correlation that semantic retrieval cannot natively reconstruct.

Output layout (additive — does not touch existing files):
  outputs/{profile}/documents/cross_refs/
    ├── case_dossier_FR-XXX.md         (one per ring)
    ├── infra_brief_ADDR-XXXX.md       (one per high-collision address)
    ├── infra_brief_D-XXXXX.md         (one per high-collision device)
    └── enricher_manifest.json         (summary of what was emitted)

Determinism: seeded with --seed (default 42). Same input → same output.

Usage:
  python3 scripts/data_corpus_enricher.py --profile small
  python3 scripts/data_corpus_enricher.py --profile benchmark_dense --max-rings 40
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── Reading the existing dataset (CSV only — never mutated) ────────────────


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open() as f:
        return list(csv.DictReader(f))


def _load_dataset(profile: str) -> dict[str, Any]:
    base = PROJECT_ROOT / "outputs" / profile / "csv"
    if not base.exists():
        raise SystemExit(
            f"No dataset at {base}. Run the data generator first: "
            f"python -m 1_data_engine generate --profile {profile} --new-pipeline"
        )
    return {
        "persons":      _read_csv(base / "persons.csv"),
        "companies":    _read_csv(base / "companies.csv"),
        "accounts":     _read_csv(base / "accounts.csv"),
        "addresses":    _read_csv(base / "addresses.csv"),
        "devices":      _read_csv(base / "devices.csv"),
        "transactions": _read_csv(base / "transactions.csv"),
        "fraud_rings":  _read_csv(base / "fraud_rings.csv"),
        "edges":        _read_csv(base / "edges.csv"),
        "person_ring":  _read_csv(base / "person_ring_memberships.csv"),
        "company_ring": _read_csv(base / "company_ring_memberships.csv"),
        "account_ring": _read_csv(base / "account_ring_memberships.csv"),
        "tx_ring":      _read_csv(base / "transaction_ring_memberships.csv"),
        "addr_ring":    _read_csv(base / "address_ring_connections.csv"),
        "device_ring":  _read_csv(base / "device_ring_connections.csv"),
    }


# ── Narrative templates (deterministic, no LLM) ────────────────────────────

_RING_INTRO_TEMPLATES = [
    "Compliance dossier — ring {ring_id} ({ring_type}, severity {severity})",
    "Investigation case file: {ring_id}",
    "Suspicious-activity report: ring {ring_id}",
    "AML inquiry · case {ring_id}",
]

_PERSON_PHRASES = [
    "Subject {pid} ({name}) is referenced in the financial intelligence "
    "stream as a member of the laundering network. The subject's KYC file "
    "shows nationality {nat} and risk-tier {tier}. Account activity links "
    "to {n_accts} accounts under the subject's control or beneficial interest.",
    "{name} (entity {pid}) appears in the case under review. The subject's "
    "structural footprint includes {n_devs} device fingerprints and {n_addrs} "
    "physical addresses on record, several of which are shared with other "
    "parties of interest.",
    "Person {pid} — {name}. Risk score on file: {risk}. The subject is "
    "connected to ring {ring_id} via direct membership; supplementary edges "
    "indicate ongoing operational ties to companies in the same cluster.",
]

_COMPANY_PHRASES = [
    "Entity {cid} ({name}, {industry}) is incorporated as a {ctype}. "
    "Beneficial-ownership inquiry surfaces {n_beneficiaries} parties with "
    "non-equity benefit. Registered address overlaps with {n_co_address} "
    "other corporate entities, several of which are flagged in adjacent rings.",
    "Company {cid} — {name}. The shell-status flag is {shell}; offshore "
    "jurisdiction flag is {offshore}. Filings list director/owner overlap "
    "with {n_owners} natural persons currently under review.",
    "{name} (entity {cid}) functions within the {industry} sector. "
    "Structural intelligence shows the company sitting at the intersection "
    "of ring {ring_id} and a wider cluster of {n_cluster} related entities.",
]

_ACCOUNT_PHRASES = [
    "Account {aid} ({atype}) holds a current balance of approximately "
    "{balance:,.0f} {ccy}. Owner of record: {owner_id}. Account is implicated "
    "in {n_tx} ring-tagged transactions and has receivership patterns "
    "consistent with a layering layer.",
    "Account {aid}: status {status}, risk {risk}. The account participates "
    "in fund-flow chains alongside {n_peers} other accounts under common "
    "structural control, suggesting coordinated movement.",
]

_INFRA_PHRASES = [
    "Address {addr_id} appears on the registration of {n_persons} persons "
    "and {n_companies} companies in the dataset. The clustering at this "
    "address exceeds expected baseline by a factor of {factor:.1f}× and is "
    "consistent with co-location of fronts.",
    "Device fingerprint {dev_id} has been observed in {n_persons} distinct "
    "person sessions. Cross-account reuse of a single device is a high-fidelity "
    "coordination signal — the cluster is flagged for traversal review.",
]


def _phrase(rng: random.Random, options: list[str], **kwargs: Any) -> str:
    template = rng.choice(options)
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):
        return template


# ── Document generation ────────────────────────────────────────────────────


def _build_ring_dossier(
    rng: random.Random,
    ring: dict[str, str],
    members_by_kind: dict[str, list[dict[str, str]]],
    by_id: dict[str, dict[str, str]],
) -> tuple[str, str]:
    """Return (filename, markdown body) for one ring's narrative dossier."""
    ring_id = ring["id"]
    ring_type = ring.get("ring_type", "unknown")
    severity = ring.get("severity", "medium")
    desc = ring.get("description", "")
    title = _phrase(
        rng, _RING_INTRO_TEMPLATES,
        ring_id=ring_id, ring_type=ring_type, severity=severity,
    )

    lines = [
        f"# {title}",
        "",
        f"**Ring:** `{ring_id}`  •  **Type:** {ring_type}  •  "
        f"**Severity:** {severity}",
        "",
        f"_{desc}_",
        "",
        "## Subjects of interest",
        "",
    ]

    for person in members_by_kind.get("person", [])[:8]:
        pid = person.get("id", "P-?")
        full = by_id.get(pid, {})
        name = full.get("name") or pid
        nat = full.get("nationality") or "—"
        tier = "high" if float(full.get("risk_score") or 0) > 0.6 else "moderate"
        lines.append("- " + _phrase(
            rng, _PERSON_PHRASES,
            pid=pid, name=name, nat=nat, tier=tier,
            n_accts=rng.randint(1, 4),
            n_devs=rng.randint(1, 3),
            n_addrs=rng.randint(1, 3),
            risk=full.get("risk_score", "0.5")[:5],
            ring_id=ring_id,
        ))

    lines.append("")
    lines.append("## Corporate entities")
    lines.append("")

    for comp in members_by_kind.get("company", [])[:8]:
        cid = comp.get("id", "C-?")
        full = by_id.get(cid, {})
        name = full.get("name") or cid
        industry = full.get("industry") or "—"
        ctype = full.get("company_type") or "domestic"
        shell = "true" if full.get("is_shell") == "True" else "false"
        offshore = "true" if full.get("is_offshore") == "True" else "false"
        lines.append("- " + _phrase(
            rng, _COMPANY_PHRASES,
            cid=cid, name=name, industry=industry, ctype=ctype,
            shell=shell, offshore=offshore,
            n_beneficiaries=rng.randint(1, 5),
            n_co_address=rng.randint(0, 4),
            n_owners=rng.randint(1, 6),
            ring_id=ring_id,
            n_cluster=rng.randint(6, 22),
        ))

    accounts = members_by_kind.get("account", [])
    if accounts:
        lines.append("")
        lines.append("## Account flow")
        lines.append("")
        for acct in accounts[:6]:
            aid = acct.get("id", "A-?")
            full = by_id.get(aid, {})
            atype = full.get("account_type") or "checking"
            ccy = full.get("currency") or "USD"
            try:
                balance = float(full.get("balance") or 0)
            except ValueError:
                balance = 0.0
            owner = full.get("owner_id") or "—"
            status = full.get("status") or "active"
            risk = full.get("risk_score", "0.5")[:5]
            lines.append("- " + _phrase(
                rng, _ACCOUNT_PHRASES,
                aid=aid, atype=atype, ccy=ccy, balance=balance,
                owner_id=owner, status=status, risk=risk,
                n_tx=rng.randint(3, 18),
                n_peers=rng.randint(2, 9),
            ))

    # Cross-ring cue — encourages cross-document referenceability.
    lines.append("")
    lines.append("## Cross-case observations")
    lines.append("")
    lines.append(
        f"Adjacent investigations involving rings near `{ring_id}` indicate "
        f"recurring structural patterns: shared device fingerprints, "
        f"co-located address clusters, and overlapping beneficiary chains. "
        f"Further graph traversal recommended."
    )
    lines.append("")
    lines.append(
        f"_Generated by `data_corpus_enricher` · ring `{ring_id}` · "
        f"{datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','')}Z_"
    )

    fname = f"case_dossier_{ring_id}.md"
    return fname, "\n".join(lines)


def _build_infra_brief(
    rng: random.Random,
    kind: str,  # "address" | "device"
    infra_id: str,
    co_persons: list[str],
    co_companies: list[str],
) -> tuple[str, str]:
    if kind == "address":
        n_p = len(co_persons)
        n_c = len(co_companies)
        if n_p + n_c < 3:
            return "", ""
        title = f"# Infrastructure brief — address {infra_id}"
        body = _phrase(
            rng, _INFRA_PHRASES[:1],
            addr_id=infra_id,
            n_persons=n_p, n_companies=n_c,
            factor=1 + (n_p + n_c) / 4,
        )
        people_str = ", ".join(co_persons[:8]) or "—"
        co_str = ", ".join(co_companies[:8]) or "—"
        md = [
            title, "",
            f"**Address:** `{infra_id}`", "",
            body, "",
            f"**Persons co-registered:** {people_str}",
            f"**Companies co-registered:** {co_str}",
            "",
            "_Co-location alone is not dispositive; topology traversal across "
            "the cluster surfaces the operational relationships._",
        ]
        return f"infra_brief_{infra_id}.md", "\n".join(md)
    else:  # device
        n_p = len(co_persons)
        if n_p < 2:
            return "", ""
        title = f"# Infrastructure brief — device {infra_id}"
        body = _phrase(
            rng, _INFRA_PHRASES[1:],
            dev_id=infra_id, n_persons=n_p,
        )
        people_str = ", ".join(co_persons[:10]) or "—"
        md = [
            title, "",
            f"**Device fingerprint:** `{infra_id}`", "",
            body, "",
            f"**Persons observed using this device:** {people_str}",
            "",
            "_Device sharing is a coordination signal — traversal across "
            "SHARES_DEVICE_WITH edges reveals the full cluster._",
        ]
        return f"infra_brief_{infra_id}.md", "\n".join(md)


# ── Top-level enrichment ───────────────────────────────────────────────────


def enrich(profile: str, seed: int, max_rings: int) -> dict[str, Any]:
    rng = random.Random(seed)
    data = _load_dataset(profile)
    out_dir = PROJECT_ROOT / "outputs" / profile / "documents" / "cross_refs"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Build by-id lookup for fast field resolution.
    by_id: dict[str, dict[str, str]] = {}
    for kind in ("persons", "companies", "accounts", "addresses", "devices", "transactions"):
        for row in data[kind]:
            by_id[row.get("id", "")] = row

    # Group ring members by kind.
    members_by_ring: dict[str, dict[str, list[dict[str, str]]]] = defaultdict(
        lambda: defaultdict(list))
    # Column in *_ring_memberships.csv is `entity_id` (not <kind>_id).
    for r in data["person_ring"]:
        members_by_ring[r.get("ring_id", "")]["person"].append(
            {"id": r.get("entity_id") or r.get("person_id", "")})
    for r in data["company_ring"]:
        members_by_ring[r.get("ring_id", "")]["company"].append(
            {"id": r.get("entity_id") or r.get("company_id", "")})
    for r in data["account_ring"]:
        members_by_ring[r.get("ring_id", "")]["account"].append(
            {"id": r.get("entity_id") or r.get("account_id", "")})

    # Address & device collision detection from the edges file.
    person_at_addr: dict[str, list[str]] = defaultdict(list)
    company_at_addr: dict[str, list[str]] = defaultdict(list)
    person_uses_device: dict[str, list[str]] = defaultdict(list)
    for e in data["edges"]:
        rel = e.get("relationship", "").lower()
        src = e.get("from_id", "")
        dst = e.get("to_id", "")
        src_type = (e.get("from_type") or "").upper()
        dst_type = (e.get("to_type") or "").upper()
        if rel == "located_at" and dst_type == "ADDRESS":
            if src_type == "PERSON":
                person_at_addr[dst].append(src)
            elif src_type == "COMPANY":
                company_at_addr[dst].append(src)
        elif rel == "uses_device" and dst_type == "DEVICE":
            person_uses_device[dst].append(src)

    rings = data["fraud_rings"][:max_rings] if max_rings else data["fraud_rings"]

    emitted: dict[str, str] = {}
    total_tokens = 0
    for ring in rings:
        rid = ring.get("id", "")
        if not rid:
            continue
        fname, body = _build_ring_dossier(rng, ring, members_by_ring[rid], by_id)
        (out_dir / fname).write_text(body)
        emitted[fname] = "ring_dossier"
        total_tokens += _estimate_tokens(body)

    # Top-N highest-collision addresses (>= 3 entities at the same address).
    addr_candidates = sorted(
        [(a, person_at_addr[a], company_at_addr.get(a, []))
         for a in person_at_addr
         if len(person_at_addr[a]) + len(company_at_addr.get(a, [])) >= 3],
        key=lambda t: -(len(t[1]) + len(t[2])),
    )[:60]
    for addr, persons, companies in addr_candidates:
        fname, body = _build_infra_brief(rng, "address", addr, persons, companies)
        if not fname:
            continue
        (out_dir / fname).write_text(body)
        emitted[fname] = "address_brief"
        total_tokens += _estimate_tokens(body)

    # Top-N highest-collision devices (>= 2 distinct persons).
    dev_candidates = sorted(
        [(d, person_uses_device[d]) for d in person_uses_device
         if len(person_uses_device[d]) >= 2],
        key=lambda t: -len(t[1]),
    )[:60]
    for dev, persons in dev_candidates:
        fname, body = _build_infra_brief(rng, "device", dev, persons, [])
        if not fname:
            continue
        (out_dir / fname).write_text(body)
        emitted[fname] = "device_brief"
        total_tokens += _estimate_tokens(body)

    manifest = {
        "profile": profile,
        "seed": seed,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z"),
        "documents_emitted": len(emitted),
        "estimated_tokens": total_tokens,
        "by_kind": _by_kind_counts(emitted),
        "output_dir": str(out_dir.relative_to(PROJECT_ROOT)),
    }
    (out_dir / "enricher_manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def _estimate_tokens(text: str) -> int:
    # Cheap heuristic: ~4 chars/token on English text.
    return max(1, len(text) // 4)


def _by_kind_counts(emitted: dict[str, str]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for kind in emitted.values():
        counts[kind] += 1
    return dict(counts)


# ── CLI ────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile", default="small")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-rings", type=int, default=0,
                    help="cap ring dossiers (0 = all)")
    args = ap.parse_args(argv)

    manifest = enrich(args.profile, args.seed, args.max_rings)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
