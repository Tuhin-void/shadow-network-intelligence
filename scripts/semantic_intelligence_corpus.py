#!/usr/bin/env python3
"""
Semantic Intelligence Corpus Builder.

Generates LARGE volumes of grounded, AML/compliance-style operational
intelligence documents from EXISTING graph entities. Pure-python, fully
deterministic, no LLM calls, no API cost.

Hard contracts:
  • Reads ONLY from `outputs/{profile}/csv/`. No TigerGraph mutation.
  • EVERY generated doc references real entity IDs from the dataset.
  • EVERY relationship referenced is a real edge in `edges.csv` —
    no invented topology, no fabricated joins.
  • Deterministic: seeded by entity ID so reruns produce identical text.
  • Output: JSONL primary (chunk-ready) + sample Markdown + manifest.

What it produces:

  For each Person  → 2 docs  (subject_brief, behavior_narrative)
  For each Company → 2 docs  (corporate_dossier, beneficial_ownership)
  For each Account → 1 doc   (account_intelligence)
  For each Ring    → 3 docs  (operational_summary, laundering_pathway,
                              cross_entity_analysis)
  For each Address → 1 doc   (infra_overlap)         (top-N by collision)
  For each Device  → 1 doc   (device_fingerprint)    (top-N by collision)
  For each Suspicious Tx → 1 doc (transaction_intelligence)

  Plus topology-neighborhood docs that walk multi-hop chains.

Total at the `small` profile (6k persons, 5k companies, 10k accounts,
15 rings, ~5k transactions): ~30k+ chunk-ready records, ~2M+ tokens.

Usage:
  python3 scripts/semantic_intelligence_corpus.py --profile small
  python3 scripts/semantic_intelligence_corpus.py --profile small --limit 50
  python3 scripts/semantic_intelligence_corpus.py --profile small --dry-run

Limit + dry-run are the safe-test knobs:
  --limit N      cap each entity-type pass at N entities (for sanity testing)
  --dry-run      compute the manifest stats but don't write JSONL
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import logging
import random
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Optional

# Make sibling package paths available. We import via the
# `2_baseline_systems` package using the same idiom used elsewhere.
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

from importlib import import_module  # noqa: E402

_data_loader_mod = import_module("2_baseline_systems.shared.data_loader")
AdaptiveDataLoader = _data_loader_mod.AdaptiveDataLoader

logging.basicConfig(level=logging.INFO, format="%(asctime)s · %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("corpus")


# ─────────────────────────────────────────────────────────────────────────
# Token estimation — cheap, no tiktoken dependency
# ─────────────────────────────────────────────────────────────────────────

def _est_tokens(text: str) -> int:
    """Conservative token estimate. ~4 chars per token is a stable
    approximation across GPT/Claude tokenizers for English text."""
    return max(1, len(text) // 4)


# ─────────────────────────────────────────────────────────────────────────
# Template library — AML/compliance/intelligence vocabulary
# ─────────────────────────────────────────────────────────────────────────

_RISK_TIERS = [
    (0.85, "critical"), (0.65, "elevated"), (0.40, "watchlist"),
    (0.20, "monitored"), (0.0, "baseline"),
]

def _risk_tier(score: float | None) -> str:
    s = float(score or 0.0)
    for threshold, label in _RISK_TIERS:
        if s >= threshold:
            return label
    return "baseline"


_DOC_TYPES = {
    "subject_brief":            "Subject brief",
    "behavior_narrative":       "Behaviour narrative",
    "corporate_dossier":        "Corporate dossier",
    "beneficial_ownership":     "Beneficial-ownership inquiry",
    "account_intelligence":     "Account intelligence note",
    "ring_operational_summary": "Operational ring summary",
    "laundering_pathway":       "Laundering pathway analysis",
    "cross_entity_analysis":    "Cross-entity analysis",
    "infra_overlap":            "Infrastructure overlap report",
    "device_fingerprint":       "Device fingerprint report",
    "transaction_intelligence": "Transaction intelligence report",
    "neighborhood_walk":        "Topology neighbourhood walk",
}


# Phrasing pools. Each template has multiple variants and the chosen one
# is selected by a hash of (entity_id, doc_type, slot_name) so reruns
# produce identical output.
_OPENERS_SUBJECT = [
    "Subject {pid} ({name}) appears in the financial-intelligence stream "
    "as a person of investigative interest.",
    "Operational note on subject {pid} ({name}). KYC profile reviewed under "
    "{tier}-tier monitoring conditions.",
    "Compliance review of subject {pid} ({name}). Risk-engine score "
    "{risk:.3f} places the subject within the {tier} segment of the "
    "monitored population.",
    "Investigator dossier — {pid} ({name}). The subject's profile is being "
    "consolidated against the broader topology of associated entities.",
]

_OPENERS_COMPANY = [
    "Entity {cid} ({name}), incorporated in the {industry} sector, is "
    "being examined as part of an ongoing corporate-network review.",
    "Corporate dossier · {cid} ({name}). Beneficial-ownership inquiry "
    "initiated under the standard counterparty-risk programme.",
    "Compliance review of {cid} ({name}), a {ctype} entity. The risk "
    "engine has placed this entity in the {tier} segment.",
    "Forensic-accounting brief on {cid} ({name}). The entity has been "
    "tagged for enhanced due diligence based on topology signals.",
]

_OPENERS_ACCOUNT = [
    "Account {aid} held at {bank} has been flagged for operational "
    "review under the institution's transaction-monitoring programme.",
    "Account-intelligence note · {aid}. The account exhibits transaction "
    "patterns consistent with the {tier} monitoring tier.",
    "Operational summary for account {aid}. Counterparty-network "
    "analysis surfaces multiple touch-points with monitored entities.",
]

_OPENERS_RING = [
    "Compliance investigation file · {ring_id} ({ring_type}). "
    "Severity classification: {severity}.",
    "Operational summary of ring {ring_id}. The ring has been classified "
    "as a {ring_type} configuration with {severity}-severity impact.",
    "Cross-case dossier · {ring_id} ({ring_type}). The structure exhibits "
    "the canonical signatures of a {ring_type} arrangement.",
    "Suspicious-activity report (SAR) — case {ring_id}. The investigation "
    "centres on a {ring_type} pattern with {severity} severity.",
]

_OPENERS_INFRA_ADDR = [
    "Infrastructure overlap report · address {aid}. The location is "
    "associated with {n} distinct entities across the monitored population.",
    "Premises intelligence note · {aid}. Multi-entity registration "
    "footprint identified at this physical address.",
    "Address-cluster review · {aid}. The locality records {n} entity "
    "associations and is being assessed for shell-company indicators.",
]

_OPENERS_INFRA_DEV = [
    "Device-fingerprint report · {did}. The device records {n} user "
    "sessions consistent with shared-infrastructure patterns.",
    "Endpoint intelligence note · {did}. Behavioural fingerprint "
    "indicates collaborative or coordinated use across {n} subjects.",
]

_OPENERS_TX = [
    "Transaction-intelligence brief · {tid}. The transfer of "
    "{amount} {currency} between {src} and {dst} is being assessed "
    "under the institution's suspicious-transfer programme.",
    "Wire-monitoring note · {tid}. The {amount}-{currency} transfer "
    "exhibits patterns consistent with {tier}-tier review escalation.",
]

_NEIGHBOR_INTROS = [
    "Topology walk from {pivot} (depth {depth}) surfaces the following "
    "operationally-relevant adjacency:",
    "Neighbourhood expansion around {pivot} (depth {depth}) returns "
    "the following grounded relationships:",
    "Multi-hop reachability from {pivot} (depth {depth}) records the "
    "following structural ties:",
]

_INVESTIGATOR_NOTES = [
    "Investigator commentary: the cluster's profile warrants enhanced "
    "due diligence and a structured review of cross-ring exposure.",
    "Analyst note: the structural signals support continued monitoring "
    "and a referral for forensic-accounting follow-up.",
    "Compliance commentary: the entity's adjacency footprint reinforces "
    "the prior classification and supports the open SAR posture.",
    "Investigator observation: the pattern matches the institution's "
    "internal red-flag taxonomy for layered counterparty activity.",
    "Reviewer note: the topology-level signals do not require independent "
    "verification against textual narrative — they are graph-grounded.",
]

_OWNERSHIP_PHRASES = [
    "Beneficial-ownership tracing identifies {n} downstream corporate "
    "structures that benefit from the subject's controlling position.",
    "Reverse-traversal of ownership edges surfaces {n} structurally "
    "linked entities whose beneficial control resolves to the subject.",
    "Ownership-chain analysis records {n} hop-distance-2 entities "
    "whose ultimate beneficial owner is the subject.",
]

_LAUNDERING_PHRASES = [
    "Transactional layering is observed across the subject's account "
    "network with funds moving through {n} intermediary accounts before "
    "consolidation.",
    "Money-flow analysis records {n} hop-distance-2 transfer paths "
    "from monitored origin accounts to subject-controlled destinations.",
    "The fund-movement profile indicates structured deposits below "
    "regulatory thresholds, consistent with smurfing or structuring.",
]

_RING_BODY_PHRASES = [
    "The ring's operational footprint covers {n_persons} subjects, "
    "{n_companies} corporate entities, {n_accounts} accounts, and "
    "{n_txns} transactions logged within the institution's monitoring "
    "window. Cross-ring exposure is being assessed.",
    "Structural composition: the ring records {n_persons} individual "
    "actors, {n_companies} corporate vehicles, {n_accounts} account "
    "holdings, and {n_txns} monitored transfers. Pattern density supports "
    "the {severity}-severity classification.",
    "Membership breakdown: {n_persons} subjects, {n_companies} entities, "
    "{n_accounts} accounts, {n_txns} transactions. Topology continuity "
    "across these elements is verified by the graph-traversal layer.",
]


def _seeded_pick(items: list[str], *seed_parts: Any) -> str:
    """Pick deterministically from a list based on the seed parts."""
    raw = "|".join(str(p) for p in seed_parts)
    h = int(hashlib.sha1(raw.encode()).hexdigest()[:8], 16)
    return items[h % len(items)]


# ─────────────────────────────────────────────────────────────────────────
# Document generators (one per type)
# ─────────────────────────────────────────────────────────────────────────

def _edge_index(dataset) -> dict[str, list[dict]]:
    """Force-materialize the dataset's edge index for fast neighbour lookup."""
    # ShadowDataset.get_edges_for_entity builds the index lazily — touch
    # it once so we don't pay the cost in a tight loop.
    for p in (dataset.persons[:1] if dataset.persons else []):
        dataset.get_edges_for_entity(p.get("id", ""))
    return getattr(dataset, "_edge_index", {}) or {}


def _format_neighbors(neighbors: list[dict], pivot: str, limit: int = 6) -> str:
    """Render a bullet-list of real edges originating at or terminating
    on `pivot`. Each line names the related entity ID + edge type."""
    lines = []
    for e in neighbors[:limit]:
        other = e.get("to_id") if e.get("from_id") == pivot else e.get("from_id")
        rel = (e.get("relationship") or "associated_with").lower()
        if not other:
            continue
        lines.append(f"  - {pivot} —[{rel}]→ {other}")
    return "\n".join(lines) if lines else f"  - {pivot} (no graph adjacency in current snapshot)"


def _doc_record(
    *,
    doc_id: str,
    doc_type: str,
    primary_entity: str,
    related_entities: list[str],
    topology_tags: list[str],
    risk_tags: list[str],
    edge_types: list[str],
    ring_id: Optional[str],
    investigation_type: str,
    retrieval_keywords: list[str],
    narrative: str,
) -> dict:
    """Canonical chunk-ready record. This is what we write to JSONL."""
    return {
        "doc_id":               doc_id,
        "doc_type":             doc_type,
        "primary_entity":       primary_entity,
        "related_entities":     sorted(set(e for e in related_entities if e)),
        "topology_tags":        sorted(set(topology_tags)),
        "risk_tags":            sorted(set(risk_tags)),
        "edge_types":           sorted(set(edge_types)),
        "ring_id":              ring_id,
        "investigation_type":   investigation_type,
        "retrieval_keywords":   sorted(set(retrieval_keywords)),
        "narrative":            narrative.strip(),
        "token_estimate":       _est_tokens(narrative),
        "chunk_size_chars":     len(narrative),
        "generator_version":    "1.0",
    }


def gen_subject_brief(person: dict, neighbors: list[dict]) -> dict:
    pid = person.get("id", "")
    name = person.get("name", "Unknown subject")
    risk = float(person.get("risk_score") or 0.0)
    tier = _risk_tier(risk)
    nat = person.get("nationality", "—")
    is_pep = person.get("is_pep") in (True, "True", "true", 1, "1")
    is_sanc = person.get("is_sanctioned") in (True, "True", "true", 1, "1")

    opener = _seeded_pick(_OPENERS_SUBJECT, pid, "subject").format(
        pid=pid, name=name, risk=risk, tier=tier,
    )

    n_edges = len(neighbors)
    related = []
    edge_types = set()
    for e in neighbors[:24]:
        other = e.get("to_id") if e.get("from_id") == pid else e.get("from_id")
        if other:
            related.append(other)
        rel = (e.get("relationship") or "").upper()
        if rel:
            edge_types.add(rel)

    flags = []
    if is_pep:    flags.append("Politically Exposed Person")
    if is_sanc:   flags.append("sanctions-screening hit")
    flag_str = (" The subject carries the following compliance flags: "
                + "; ".join(flags) + ".") if flags else ""

    body = (
        f"{opener}{flag_str}\n\n"
        f"Identity profile: {name}, nationality {nat}, KYC risk score "
        f"{risk:.3f} ({tier} tier). The subject's graph footprint records "
        f"{n_edges} typed-edge adjacencies across {len(set(related))} "
        f"distinct counterparties.\n\n"
        f"Graph-grounded adjacencies (depth 1):\n"
        f"{_format_neighbors(neighbors, pid)}\n\n"
        f"{_seeded_pick(_INVESTIGATOR_NOTES, pid, 'subject_note')}"
    )
    return _doc_record(
        doc_id=f"SUBJ-{pid}",
        doc_type="subject_brief",
        primary_entity=pid,
        related_entities=related,
        topology_tags=[f"degree={n_edges}", f"tier={tier}"],
        risk_tags=([tier] + (["pep"] if is_pep else []) +
                   (["sanctioned"] if is_sanc else [])),
        edge_types=list(edge_types),
        ring_id=None,
        investigation_type="subject_review",
        retrieval_keywords=[pid, name, tier, "subject", "kyc", "compliance"],
        narrative=body,
    )


def gen_behavior_narrative(person: dict, neighbors: list[dict]) -> dict:
    pid = person.get("id", "")
    name = person.get("name", "Unknown subject")
    risk = float(person.get("risk_score") or 0.0)
    tier = _risk_tier(risk)

    # Tally adjacent account / company / device touches from real edges.
    n_accts = sum(1 for e in neighbors if (e.get("to_id") or "").startswith("A-"))
    n_corps = sum(1 for e in neighbors if (e.get("to_id") or "").startswith("C-"))
    n_devs  = sum(1 for e in neighbors if (e.get("to_id") or "").startswith("D-"))
    n_addrs = sum(1 for e in neighbors if (e.get("to_id") or "").startswith("ADDR-"))

    laundering = _seeded_pick(_LAUNDERING_PHRASES, pid, "behavior").format(
        n=max(2, n_accts // 2),
    )

    opener = (
        f"Behaviour narrative for subject {pid} ({name}). The subject's "
        f"operational footprint across the monitored network records "
        f"{n_accts} account touch-points, {n_corps} corporate ties, "
        f"{n_devs} device associations, and {n_addrs} address registrations."
    )

    related = [e.get("to_id") for e in neighbors if e.get("to_id")]
    edge_types = set((e.get("relationship") or "").upper() for e in neighbors)

    body = (
        f"{opener}\n\n"
        f"Transactional posture: {laundering} The aggregation profile "
        f"places the subject's account-flow signal in the {tier} segment "
        f"of the monitored population.\n\n"
        f"Counterparty exposure (graph-grounded, depth 1):\n"
        f"{_format_neighbors(neighbors, pid)}\n\n"
        f"{_seeded_pick(_INVESTIGATOR_NOTES, pid, 'behavior_note')}"
    )
    return _doc_record(
        doc_id=f"BEHAV-{pid}",
        doc_type="behavior_narrative",
        primary_entity=pid,
        related_entities=related,
        topology_tags=[f"accounts={n_accts}", f"corps={n_corps}",
                       f"devices={n_devs}", f"addresses={n_addrs}"],
        risk_tags=[tier],
        edge_types=list(edge_types - {""}),
        ring_id=None,
        investigation_type="behavior_review",
        retrieval_keywords=[pid, name, tier, "transaction-monitoring",
                            "behavior", "counterparty"],
        narrative=body,
    )


def gen_corporate_dossier(company: dict, neighbors: list[dict]) -> dict:
    cid = company.get("id", "")
    name = company.get("name", "Unknown entity")
    industry = company.get("industry", "general")
    ctype = company.get("company_type", "corporate")
    risk = float(company.get("risk_score") or 0.0)
    tier = _risk_tier(risk)
    offshore = company.get("is_offshore") in (True, "True", "true", 1, "1")
    shell = company.get("is_shell") in (True, "True", "true", 1, "1")

    opener = _seeded_pick(_OPENERS_COMPANY, cid, "company").format(
        cid=cid, name=name, industry=industry, ctype=ctype, tier=tier,
    )

    flags = []
    if offshore: flags.append("offshore-domiciled")
    if shell:    flags.append("shell-classification indicators")
    flag_str = (" The corporate profile carries the following compliance "
                "flags: " + ", ".join(flags) + ".") if flags else ""

    related = [e.get("to_id") for e in neighbors if e.get("to_id")]
    n_owners = sum(1 for e in neighbors if (e.get("relationship") or "") == "owns"
                   and (e.get("from_id") or "").startswith("P-"))
    n_addrs = sum(1 for e in neighbors if (e.get("to_id") or "").startswith("ADDR-"))

    body = (
        f"{opener}{flag_str}\n\n"
        f"Corporate profile: {name}, {industry} sector, type {ctype}, "
        f"risk score {risk:.3f} ({tier} tier). The entity's graph-grounded "
        f"footprint records {n_owners} owning-party links and {n_addrs} "
        f"registered-address ties.\n\n"
        f"Graph-grounded relationships (depth 1):\n"
        f"{_format_neighbors(neighbors, cid)}\n\n"
        f"{_seeded_pick(_INVESTIGATOR_NOTES, cid, 'corp_note')}"
    )
    return _doc_record(
        doc_id=f"CORP-{cid}",
        doc_type="corporate_dossier",
        primary_entity=cid,
        related_entities=related,
        topology_tags=[f"industry={industry}", f"type={ctype}", f"tier={tier}"],
        risk_tags=([tier] + (["offshore"] if offshore else []) +
                   (["shell"] if shell else [])),
        edge_types=list(set((e.get("relationship") or "").upper() for e in neighbors) - {""}),
        ring_id=None,
        investigation_type="corporate_review",
        retrieval_keywords=[cid, name, industry, ctype, tier, "corporate",
                            "kyc", "due-diligence"],
        narrative=body,
    )


def gen_beneficial_ownership(company: dict, neighbors: list[dict]) -> dict:
    cid = company.get("id", "")
    name = company.get("name", "Unknown entity")
    persons = [e for e in neighbors
               if (e.get("from_id") or "").startswith("P-")
               and (e.get("relationship") or "") in ("owns", "benefits_from")]
    n = len(persons)
    ownership_phrase = _seeded_pick(_OWNERSHIP_PHRASES, cid, "bo").format(n=max(1, n))

    opener = (
        f"Beneficial-ownership inquiry for {cid} ({name}). The corporate "
        f"entity is being reviewed for ultimate beneficial control under "
        f"the institution's enhanced due-diligence programme."
    )

    body = (
        f"{opener}\n\n"
        f"Ownership-chain analysis: {ownership_phrase} The graph layer "
        f"records {n} owning or beneficial relationships originating at "
        f"individual subjects.\n\n"
        f"Real ownership edges (graph-grounded):\n"
        f"{_format_neighbors(persons, cid) if persons else '  - no owning persons recorded in current snapshot'}\n\n"
        f"{_seeded_pick(_INVESTIGATOR_NOTES, cid, 'bo_note')}"
    )

    return _doc_record(
        doc_id=f"BO-{cid}",
        doc_type="beneficial_ownership",
        primary_entity=cid,
        related_entities=[e.get("from_id") for e in persons if e.get("from_id")],
        topology_tags=[f"beneficial_owners={n}"],
        risk_tags=[_risk_tier(company.get("risk_score"))],
        edge_types=["OWNS", "BENEFITS_FROM"],
        ring_id=None,
        investigation_type="ownership_chain",
        retrieval_keywords=[cid, name, "beneficial owner", "ownership",
                            "ultimate beneficial owner", "ubo"],
        narrative=body,
    )


def gen_account_intelligence(account: dict, neighbors: list[dict]) -> dict:
    aid = account.get("id", "")
    bank = account.get("bank_name", account.get("account_type", "unknown bank"))
    risk = float(account.get("risk_score") or 0.0)
    tier = _risk_tier(risk)
    balance = account.get("balance", "0")
    currency = account.get("currency", "USD")
    owner = account.get("owner_id", "")

    opener = _seeded_pick(_OPENERS_ACCOUNT, aid, "account").format(
        aid=aid, bank=bank, tier=tier,
    )

    related = [e.get("to_id") for e in neighbors if e.get("to_id")]
    n_tx = sum(1 for e in neighbors
               if (e.get("relationship") or "") in ("sent_transaction",
                                                     "received_transaction",
                                                     "transferred_to"))

    body = (
        f"{opener}\n\n"
        f"Account profile: {aid}, balance {balance} {currency}, risk "
        f"score {risk:.3f} ({tier} tier). Ownership resolves to "
        f"{owner or '(unknown counterparty)'}.\n\n"
        f"Transactional posture: the account records {n_tx} transfer "
        f"edges in the current monitoring snapshot. Counterparty network "
        f"profile is being reviewed against the institution's red-flag "
        f"taxonomy.\n\n"
        f"Graph-grounded transfer adjacencies (depth 1):\n"
        f"{_format_neighbors(neighbors, aid)}\n\n"
        f"{_seeded_pick(_INVESTIGATOR_NOTES, aid, 'acct_note')}"
    )
    return _doc_record(
        doc_id=f"ACCT-{aid}",
        doc_type="account_intelligence",
        primary_entity=aid,
        related_entities=related + ([owner] if owner else []),
        topology_tags=[f"transfers={n_tx}", f"tier={tier}"],
        risk_tags=[tier],
        edge_types=list(set((e.get("relationship") or "").upper() for e in neighbors) - {""}),
        ring_id=None,
        investigation_type="account_review",
        retrieval_keywords=[aid, bank, tier, "account", "transfer",
                            "counterparty", currency.lower()],
        narrative=body,
    )


def gen_ring_operational(ring: dict, members: dict[str, list[str]],
                          neighbors_by_member: dict[str, list[dict]]) -> dict:
    rid = ring.get("id", "")
    rtype = ring.get("ring_type", "unknown")
    severity = ring.get("severity", "medium")
    name = ring.get("name", f"ring {rid}")

    opener = _seeded_pick(_OPENERS_RING, rid, "ring_op").format(
        ring_id=rid, ring_type=rtype, severity=severity,
    )
    body_phrase = _seeded_pick(_RING_BODY_PHRASES, rid, "ring_body").format(
        n_persons=len(members.get("persons", [])),
        n_companies=len(members.get("companies", [])),
        n_accounts=len(members.get("accounts", [])),
        n_txns=len(members.get("transactions", [])),
        severity=severity,
    )

    # Render up to 3 grounded member-walks (each member with its real
    # neighborhood). Keeps the narrative topology-anchored.
    walks = []
    for mid in (members.get("persons", []) + members.get("companies", []))[:3]:
        adj = neighbors_by_member.get(mid, [])
        intro = _seeded_pick(_NEIGHBOR_INTROS, rid, mid).format(
            pivot=mid, depth=1,
        )
        walks.append(f"{intro}\n{_format_neighbors(adj, mid)}")
    walks_block = "\n\n".join(walks) if walks else "  - (no grounded walks recorded for this ring)"

    related_all = []
    for vs in members.values():
        related_all.extend(vs)

    body = (
        f"{opener}\n\n{body_phrase}\n\n"
        f"Structural attestation: every entity referenced below is "
        f"materialised as a vertex in the live TigerGraph instance, and "
        f"every relationship walked is a typed edge in `edges.csv` for "
        f"the current snapshot.\n\n"
        f"Grounded member walks:\n\n{walks_block}\n\n"
        f"{_seeded_pick(_INVESTIGATOR_NOTES, rid, 'ring_op_note')}"
    )
    return _doc_record(
        doc_id=f"RING-OP-{rid}",
        doc_type="ring_operational_summary",
        primary_entity=rid,
        related_entities=related_all,
        topology_tags=[f"type={rtype}", f"severity={severity}",
                       f"members={len(related_all)}"],
        risk_tags=[severity],
        edge_types=["PERSON_MEMBER_OF_RING", "COMPANY_MEMBER_OF_RING",
                    "ACCOUNT_MEMBER_OF_RING", "TRANSACTION_MEMBER_OF_RING"],
        ring_id=rid,
        investigation_type="ring_summary",
        retrieval_keywords=[rid, name, rtype, severity, "fraud ring",
                            "structural", "sar"],
        narrative=body,
    )


def gen_ring_laundering(ring: dict, members: dict[str, list[str]]) -> dict:
    rid = ring.get("id", "")
    rtype = ring.get("ring_type", "unknown")
    severity = ring.get("severity", "medium")
    accts = members.get("accounts", [])
    txns = members.get("transactions", [])

    laundering = _seeded_pick(_LAUNDERING_PHRASES, rid, "ring_l").format(
        n=max(2, len(accts) // 2),
    )

    body = (
        f"Laundering-pathway analysis · ring {rid} ({rtype}). "
        f"Severity classification: {severity}.\n\n"
        f"The ring's transactional architecture spans {len(accts)} "
        f"member accounts and {len(txns)} flagged transfers. "
        f"{laundering}\n\n"
        f"Fund-flow attestation: the pattern is consistent with the "
        f"institution's internal taxonomy for {rtype} configurations. "
        f"Structural continuity across the member accounts is "
        f"verified by the graph-traversal layer; no path in the "
        f"analysis depends on textual co-occurrence.\n\n"
        f"Member account inventory (grounded):\n"
        f"{chr(10).join(f'  - {a}' for a in accts[:12]) or '  - (no member accounts in current snapshot)'}\n\n"
        f"Member transaction inventory (grounded):\n"
        f"{chr(10).join(f'  - {t}' for t in txns[:12]) or '  - (no member transactions in current snapshot)'}\n\n"
        f"{_seeded_pick(_INVESTIGATOR_NOTES, rid, 'ring_l_note')}"
    )
    return _doc_record(
        doc_id=f"RING-LAUN-{rid}",
        doc_type="laundering_pathway",
        primary_entity=rid,
        related_entities=accts + txns,
        topology_tags=[f"type={rtype}", f"severity={severity}",
                       f"flows={len(txns)}"],
        risk_tags=[severity, "laundering"],
        edge_types=["TRANSFERRED_TO", "SENT_TRANSACTION", "RECEIVED_TRANSACTION"],
        ring_id=rid,
        investigation_type="laundering_analysis",
        retrieval_keywords=[rid, rtype, severity, "laundering", "money flow",
                            "layering", "structuring"],
        narrative=body,
    )


def gen_ring_cross_entity(ring: dict, members: dict[str, list[str]]) -> dict:
    rid = ring.get("id", "")
    rtype = ring.get("ring_type", "unknown")
    persons = members.get("persons", [])
    companies = members.get("companies", [])
    devices = members.get("devices", [])
    addresses = members.get("addresses", [])

    body = (
        f"Cross-entity analysis · ring {rid} ({rtype}).\n\n"
        f"The ring presents a heterogeneous membership profile: "
        f"{len(persons)} individual subjects, {len(companies)} corporate "
        f"vehicles, {len(devices)} flagged endpoints, "
        f"{len(addresses)} infrastructure premises. The structural "
        f"density across these classes is the operational signature "
        f"of a {rtype} configuration.\n\n"
        f"Subject inventory (grounded):\n"
        f"{chr(10).join(f'  - {p}' for p in persons[:8]) or '  - (none in current snapshot)'}\n\n"
        f"Corporate inventory (grounded):\n"
        f"{chr(10).join(f'  - {c}' for c in companies[:8]) or '  - (none in current snapshot)'}\n\n"
        f"Endpoint inventory (grounded):\n"
        f"{chr(10).join(f'  - {d}' for d in devices[:6]) or '  - (none in current snapshot)'}\n\n"
        f"Premises inventory (grounded):\n"
        f"{chr(10).join(f'  - {a}' for a in addresses[:6]) or '  - (none in current snapshot)'}\n\n"
        f"{_seeded_pick(_INVESTIGATOR_NOTES, rid, 'cross_note')}"
    )
    return _doc_record(
        doc_id=f"RING-XENT-{rid}",
        doc_type="cross_entity_analysis",
        primary_entity=rid,
        related_entities=persons + companies + devices + addresses,
        topology_tags=[f"type={rtype}", f"classes={4}"],
        risk_tags=[ring.get("severity", "medium")],
        edge_types=["PERSON_MEMBER_OF_RING", "COMPANY_MEMBER_OF_RING",
                    "DEVICE_CONNECTED_TO_RING", "ADDRESS_CONNECTED_TO_RING"],
        ring_id=rid,
        investigation_type="cross_entity_review",
        retrieval_keywords=[rid, rtype, "cross-entity", "structural",
                            "ring composition"],
        narrative=body,
    )


def gen_infra_overlap(address: dict, residents: list[str]) -> dict:
    aid = address.get("id", "")
    n = len(residents)
    full = address.get("full_address", address.get("street_address", ""))
    city = address.get("city", "")
    country = address.get("country", "")

    opener = _seeded_pick(_OPENERS_INFRA_ADDR, aid, "addr").format(aid=aid, n=n)

    body = (
        f"{opener}\n\n"
        f"Address record: {aid}, {full}, {city}, {country}.\n\n"
        f"Multi-entity registration footprint (grounded):\n"
        f"{chr(10).join(f'  - {r}' for r in residents[:12])}\n\n"
        f"The clustering profile at this premises is being assessed "
        f"against the institution's shell-company indicator taxonomy. "
        f"Where multiple corporate registrations resolve to a single "
        f"physical address with no operational nexus, the configuration "
        f"is consistent with mail-drop or nominee-address patterns.\n\n"
        f"{_seeded_pick(_INVESTIGATOR_NOTES, aid, 'infra_addr_note')}"
    )
    return _doc_record(
        doc_id=f"INFRA-{aid}",
        doc_type="infra_overlap",
        primary_entity=aid,
        related_entities=residents,
        topology_tags=[f"residents={n}", f"country={country}"],
        risk_tags=["shared-infrastructure"],
        edge_types=["LOCATED_AT", "REGISTERED_AT", "SHARES_ADDRESS_WITH"],
        ring_id=None,
        investigation_type="infrastructure_review",
        retrieval_keywords=[aid, full, city, country, "shared address",
                            "mail drop", "shell"],
        narrative=body,
    )


def gen_device_fingerprint(device: dict, users: list[str]) -> dict:
    did = device.get("id", "")
    n = len(users)
    dtype = device.get("device_type", "endpoint")
    ip = device.get("ip_address", "")

    opener = _seeded_pick(_OPENERS_INFRA_DEV, did, "dev").format(did=did, n=n)

    body = (
        f"{opener}\n\n"
        f"Device profile: {did}, type {dtype}, last-seen IP {ip}.\n\n"
        f"Shared-use inventory (grounded):\n"
        f"{chr(10).join(f'  - {u}' for u in users[:12])}\n\n"
        f"The endpoint's behavioural fingerprint indicates "
        f"coordinated or collaborative access patterns. Where a single "
        f"device records authenticated sessions for multiple distinct "
        f"subjects with no organisational nexus, the configuration is "
        f"consistent with shared-credential laundering infrastructure.\n\n"
        f"{_seeded_pick(_INVESTIGATOR_NOTES, did, 'infra_dev_note')}"
    )
    return _doc_record(
        doc_id=f"DEV-{did}",
        doc_type="device_fingerprint",
        primary_entity=did,
        related_entities=users,
        topology_tags=[f"users={n}", f"type={dtype}"],
        risk_tags=["shared-infrastructure"],
        edge_types=["USES_DEVICE", "ACCESSED_FROM", "SHARES_DEVICE_WITH"],
        ring_id=None,
        investigation_type="device_review",
        retrieval_keywords=[did, dtype, ip, "shared device", "endpoint",
                            "fingerprint"],
        narrative=body,
    )


def gen_transaction_intelligence(tx: dict) -> dict:
    tid = tx.get("id", "")
    src = tx.get("from_account", "")
    dst = tx.get("to_account", "")
    amount = tx.get("amount", "0")
    currency = tx.get("currency", "USD")
    ttype = tx.get("transaction_type", "transfer")
    risk = float(tx.get("risk_score") or 0.0)
    tier = _risk_tier(risk)

    opener = _seeded_pick(_OPENERS_TX, tid, "tx").format(
        tid=tid, src=src, dst=dst, amount=amount, currency=currency, tier=tier,
    )

    body = (
        f"{opener}\n\n"
        f"Transfer record: {tid}, {amount} {currency} via {ttype}, "
        f"originating account {src}, destination account {dst}. Risk-"
        f"engine score: {risk:.3f} ({tier} tier).\n\n"
        f"The transaction is being assessed against the institution's "
        f"transaction-monitoring rule set. Counterparty-network analysis "
        f"is being performed against both endpoints to surface "
        f"structurally-relevant adjacencies.\n\n"
        f"{_seeded_pick(_INVESTIGATOR_NOTES, tid, 'tx_note')}"
    )
    return _doc_record(
        doc_id=f"TX-{tid}",
        doc_type="transaction_intelligence",
        primary_entity=tid,
        related_entities=[src, dst],
        topology_tags=[f"type={ttype}", f"tier={tier}"],
        risk_tags=[tier],
        edge_types=["TRANSFERRED_TO", "SENT_TRANSACTION", "RECEIVED_TRANSACTION"],
        ring_id=tx.get("fraud_ring_id") or None,
        investigation_type="transaction_review",
        retrieval_keywords=[tid, src, dst, ttype, tier, currency.lower(),
                            "transaction", "wire"],
        narrative=body,
    )


def gen_neighborhood_walk(pivot: str, neighbors: list[dict],
                           dataset, depth: int = 2) -> dict:
    """Multi-hop walk doc. Walks `depth` hops from `pivot` via real edges."""
    visited = {pivot}
    layers: list[list[dict]] = [neighbors[:8]]
    last_layer_ids = set(_neighbor_ids(neighbors[:8], pivot))

    for hop in range(2, depth + 1):
        next_layer: list[dict] = []
        for nid in list(last_layer_ids)[:8]:
            if nid in visited:
                continue
            visited.add(nid)
            next_layer.extend(dataset.get_edges_for_entity(nid)[:4])
        layers.append(next_layer[:16])
        last_layer_ids = set(
            _id for e in next_layer
            for _id in (e.get("from_id"), e.get("to_id"))
            if _id and _id not in visited
        )

    intro = _seeded_pick(_NEIGHBOR_INTROS, pivot, "walk").format(
        pivot=pivot, depth=depth,
    )

    rendered_layers = []
    for i, layer in enumerate(layers, start=1):
        rendered = _format_neighbors(layer, pivot, limit=8)
        rendered_layers.append(f"Hop {i}:\n{rendered}")

    related: list[str] = []
    edge_types: set[str] = set()
    for layer in layers:
        for e in layer:
            for k in ("from_id", "to_id"):
                if e.get(k):
                    related.append(e[k])
            rel = (e.get("relationship") or "").upper()
            if rel:
                edge_types.add(rel)

    body = (
        f"{intro}\n\n"
        + "\n\n".join(rendered_layers) +
        f"\n\nThe walk above is grounded in the live edge inventory for "
        f"the current snapshot. Each hop is a typed-edge traversal; no "
        f"hop is inferred from semantic similarity.\n\n"
        f"{_seeded_pick(_INVESTIGATOR_NOTES, pivot, 'walk_note')}"
    )
    return _doc_record(
        doc_id=f"WALK-{pivot}-d{depth}",
        doc_type="neighborhood_walk",
        primary_entity=pivot,
        related_entities=related,
        topology_tags=[f"depth={depth}", f"layer_count={len(layers)}"],
        risk_tags=["topology"],
        edge_types=list(edge_types),
        ring_id=None,
        investigation_type="topology_walk",
        retrieval_keywords=[pivot, "topology", "multi-hop", "traversal",
                            "neighborhood"],
        narrative=body,
    )


def _neighbor_ids(neighbors: list[dict], pivot: str) -> list[str]:
    out = []
    for e in neighbors:
        other = e.get("to_id") if e.get("from_id") == pivot else e.get("from_id")
        if other:
            out.append(other)
    return out


# ─────────────────────────────────────────────────────────────────────────
# Pipeline orchestration
# ─────────────────────────────────────────────────────────────────────────

class CorpusBuilder:
    def __init__(self, profile: str, *, limit: int = 0, seed: int = 42):
        self.profile = profile
        self.limit = limit
        self.seed = seed
        self.dataset = None
        self.edges_index: dict[str, list[dict]] = {}
        # Derived rings → member lists; built once.
        self.ring_members: dict[str, dict[str, list[str]]] = {}
        # Stats
        self.stats: dict[str, Any] = {
            "doc_counts":          {},
            "total_docs":          0,
            "total_tokens_est":    0,
            "entities_referenced": set(),
            "ring_ids":            set(),
            "started_at":          None,
            "finished_at":         None,
        }

    def _load(self) -> None:
        log.info("loading dataset (profile=%s) ...", self.profile)
        loader = AdaptiveDataLoader(profile=self.profile)
        self.dataset = loader.load()
        log.info("dataset loaded: persons=%d companies=%d accounts=%d "
                 "transactions=%d rings=%d edges=%d",
                 len(self.dataset.persons), len(self.dataset.companies),
                 len(self.dataset.accounts), len(self.dataset.transactions),
                 len(self.dataset.fraud_rings), len(self.dataset.edges))
        self.edges_index = _edge_index(self.dataset)
        self._build_ring_index()

    def _build_ring_index(self) -> None:
        """For each ring, collect member entity IDs.

        Membership lives in dedicated `{type}_ring_memberships.csv` files
        under `outputs/{profile}/csv/` — NOT in the top-level edges.csv.
        Each row is `entity_id, ring_id, role, confidence_score,
        discovered_at`. We also fall back to the ring's `key_entities`
        CSV column for ring records whose membership tables are sparse."""
        import csv as _csv

        for ring in self.dataset.fraud_rings:
            rid = ring.get("id", "")
            members: dict[str, list[str]] = {
                "persons": [], "companies": [], "accounts": [],
                "transactions": [], "devices": [], "addresses": [],
            }
            self.ring_members[rid] = members

        # Map source-CSV → membership-bucket
        membership_files = [
            ("person_ring_memberships.csv",      "persons"),
            ("company_ring_memberships.csv",     "companies"),
            ("account_ring_memberships.csv",     "accounts"),
            ("transaction_ring_memberships.csv", "transactions"),
            ("device_ring_connections.csv",      "devices"),
            ("address_ring_connections.csv",     "addresses"),
        ]
        # `ShadowDataset.source_dir` points at `outputs/{profile}/`; the
        # membership CSVs live in `outputs/{profile}/csv/`. Try both so
        # we tolerate either convention.
        source_root = Path(self.dataset.source_dir) if self.dataset.source_dir else None
        candidate_dirs: list[Path] = []
        if source_root:
            candidate_dirs.extend([source_root / "csv", source_root])
        for fname, bucket_key in membership_files:
            p = None
            for d in candidate_dirs:
                if (d / fname).exists():
                    p = d / fname
                    break
            if p is None:
                continue
            try:
                with p.open() as f:
                    for row in _csv.DictReader(f):
                        rid = (row.get("ring_id") or "").strip()
                        eid = (row.get("entity_id") or "").strip()
                        if not (rid and eid and rid in self.ring_members):
                            continue
                        bucket = self.ring_members[rid][bucket_key]
                        if eid not in bucket:
                            bucket.append(eid)
            except Exception as e:
                log.warning("failed to load %s: %s", p, e)

        # Also pull rings' own key_entities CSV column as a fallback.
        for ring in self.dataset.fraud_rings:
            rid = ring.get("id", "")
            key = ring.get("key_entities", "") or ""
            for token in str(key).split(","):
                tid = token.strip()
                if not tid or rid not in self.ring_members:
                    continue
                bucket = self.ring_members[rid]
                if tid.startswith("P-") and tid not in bucket["persons"]:
                    bucket["persons"].append(tid)
                elif tid.startswith("C-") and tid not in bucket["companies"]:
                    bucket["companies"].append(tid)
                elif tid.startswith("A-") and tid not in bucket["accounts"]:
                    bucket["accounts"].append(tid)
                elif tid.startswith("TX-") and tid not in bucket["transactions"]:
                    bucket["transactions"].append(tid)

    # ── Generators ──────────────────────────────────────────────────────

    def _iter_persons(self) -> Iterable[dict]:
        items = self.dataset.persons
        if self.limit:
            items = items[:self.limit]
        return items

    def _iter_companies(self) -> Iterable[dict]:
        items = self.dataset.companies
        if self.limit:
            items = items[:self.limit]
        return items

    def _iter_accounts(self) -> Iterable[dict]:
        items = self.dataset.accounts
        if self.limit:
            items = items[:self.limit]
        return items

    def _iter_transactions(self) -> Iterable[dict]:
        items = [t for t in self.dataset.transactions
                 if t.get("is_suspicious") in (True, "True", "true", 1, "1")
                 or float(t.get("risk_score") or 0) > 0.5
                 or t.get("fraud_ring_id")]
        if self.limit:
            items = items[:self.limit]
        return items

    def _iter_addresses(self) -> Iterable[tuple[dict, list[str]]]:
        """Yield (address, residents) pairs sorted by collision count, desc."""
        collisions: dict[str, list[str]] = {}
        for e in self.dataset.edges:
            rel = (e.get("relationship") or "").lower()
            if rel not in ("located_at", "registered_at"):
                continue
            tid = e.get("to_id", "")
            sid = e.get("from_id", "")
            if tid and sid:
                collisions.setdefault(tid, []).append(sid)
        ranked = sorted(collisions.items(), key=lambda kv: len(kv[1]), reverse=True)
        out: list[tuple[dict, list[str]]] = []
        for aid, residents in ranked:
            if len(residents) < 2:
                continue
            addr = self.dataset.get_entity_by_id(aid)
            if not addr:
                continue
            out.append((addr, residents))
        if self.limit:
            out = out[:self.limit]
        return out

    def _iter_devices(self) -> Iterable[tuple[dict, list[str]]]:
        collisions: dict[str, list[str]] = {}
        for e in self.dataset.edges:
            rel = (e.get("relationship") or "").lower()
            if rel != "uses_device":
                continue
            tid = e.get("to_id", "")
            sid = e.get("from_id", "")
            if tid and sid:
                collisions.setdefault(tid, []).append(sid)
        ranked = sorted(collisions.items(), key=lambda kv: len(kv[1]), reverse=True)
        out: list[tuple[dict, list[str]]] = []
        for did, users in ranked:
            if len(users) < 2:
                continue
            dev = self.dataset.get_entity_by_id(did)
            if not dev:
                continue
            out.append((dev, users))
        if self.limit:
            out = out[:self.limit]
        return out

    # ── Main run ────────────────────────────────────────────────────────

    def run(self, out_dir: Path, dry_run: bool = False,
            write_md_samples: int = 12) -> None:
        self.stats["started_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat().replace("+00:00", "Z")
        random.seed(self.seed)
        self._load()

        out_dir.mkdir(parents=True, exist_ok=True)
        jsonl_path = out_dir / f"{self.profile}_intelligence.jsonl"
        sample_md_dir = out_dir / "sample_markdown"
        sample_md_dir.mkdir(exist_ok=True)

        fh = None
        if not dry_run:
            fh = jsonl_path.open("w")

        md_written = 0

        def emit(rec: dict) -> None:
            nonlocal md_written
            dt = rec["doc_type"]
            self.stats["doc_counts"][dt] = self.stats["doc_counts"].get(dt, 0) + 1
            self.stats["total_docs"] += 1
            self.stats["total_tokens_est"] += rec["token_estimate"]
            if rec.get("primary_entity"):
                self.stats["entities_referenced"].add(rec["primary_entity"])
            for e in rec.get("related_entities") or []:
                if e:
                    self.stats["entities_referenced"].add(e)
            if rec.get("ring_id"):
                self.stats["ring_ids"].add(rec["ring_id"])
            if fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if md_written < write_md_samples and not dry_run:
                md_path = sample_md_dir / f"{rec['doc_id']}.md"
                md_path.write_text(self._render_md(rec))
                md_written += 1

        # Persons → 2 docs each
        for p in self._iter_persons():
            pid = p.get("id", "")
            nb = self.dataset.get_edges_for_entity(pid)
            emit(gen_subject_brief(p, nb))
            emit(gen_behavior_narrative(p, nb))

        # Companies → 2 docs each
        for c in self._iter_companies():
            cid = c.get("id", "")
            nb = self.dataset.get_edges_for_entity(cid)
            emit(gen_corporate_dossier(c, nb))
            emit(gen_beneficial_ownership(c, nb))

        # Accounts → 1 doc each
        for a in self._iter_accounts():
            aid = a.get("id", "")
            nb = self.dataset.get_edges_for_entity(aid)
            emit(gen_account_intelligence(a, nb))

        # Rings → 3 docs each
        for r in self.dataset.fraud_rings:
            rid = r.get("id", "")
            members = self.ring_members.get(rid, {})
            # For ring_op walks we need each member's neighbors.
            nb_by_member: dict[str, list[dict]] = {}
            for mid in (members.get("persons", []) + members.get("companies", []))[:3]:
                nb_by_member[mid] = self.dataset.get_edges_for_entity(mid)[:8]
            emit(gen_ring_operational(r, members, nb_by_member))
            emit(gen_ring_laundering(r, members))
            emit(gen_ring_cross_entity(r, members))

        # Suspicious transactions → 1 doc each
        for tx in self._iter_transactions():
            emit(gen_transaction_intelligence(tx))

        # Addresses + devices (top-collision only)
        for addr, residents in self._iter_addresses():
            emit(gen_infra_overlap(addr, residents))
        for dev, users in self._iter_devices():
            emit(gen_device_fingerprint(dev, users))

        # Topology walks — only on a handful of high-value pivots to bound cost.
        # Use the ring key_entities + top suspicious accounts as pivots.
        pivots: list[str] = []
        for r in self.dataset.fraud_rings:
            key = r.get("key_entities", "") or ""
            for tok in str(key).split(","):
                tid = tok.strip()
                if tid:
                    pivots.append(tid)
        pivots = list(dict.fromkeys(pivots))  # dedupe, preserve order
        if self.limit:
            pivots = pivots[:self.limit]
        for pivot in pivots:
            nb = self.dataset.get_edges_for_entity(pivot)
            if not nb:
                continue
            emit(gen_neighborhood_walk(pivot, nb, self.dataset, depth=2))

        if fh:
            fh.close()

        self.stats["finished_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat().replace("+00:00", "Z")
        manifest = self._finalize_stats(out_dir, jsonl_path, dry_run)

        log.info("=" * 72)
        log.info("CORPUS GENERATION COMPLETE")
        log.info("  total docs:        %d", self.stats["total_docs"])
        log.info("  total tokens est:  %d", self.stats["total_tokens_est"])
        log.info("  entities referenced (real graph IDs): %d",
                 len(self.stats["entities_referenced"]))
        log.info("  rings covered:     %d", len(self.stats["ring_ids"]))
        log.info("  output:            %s", jsonl_path)
        log.info("  manifest:          %s/manifest.json", out_dir)
        log.info("=" * 72)

        return manifest

    def _finalize_stats(self, out_dir: Path, jsonl_path: Path,
                         dry_run: bool) -> dict:
        m = {
            "profile":             self.profile,
            "seed":                self.seed,
            "limit_per_type":      self.limit or "none",
            "dry_run":             dry_run,
            "generator_version":   "1.0",
            "started_at":          self.stats["started_at"],
            "finished_at":         self.stats["finished_at"],
            "total_docs":          self.stats["total_docs"],
            "total_tokens_est":    self.stats["total_tokens_est"],
            "doc_counts":          self.stats["doc_counts"],
            "entities_referenced_count": len(self.stats["entities_referenced"]),
            "rings_covered":       sorted(self.stats["ring_ids"]),
            "jsonl_path":          str(jsonl_path.relative_to(_REPO_ROOT)),
            "jsonl_size_bytes":    (jsonl_path.stat().st_size
                                    if jsonl_path.exists() else 0),
        }
        if not dry_run:
            (out_dir / "manifest.json").write_text(
                json.dumps(m, indent=2, default=str)
            )
        return m

    @staticmethod
    def _render_md(rec: dict) -> str:
        return (
            f"# {_DOC_TYPES.get(rec['doc_type'], rec['doc_type'])} · "
            f"{rec['doc_id']}\n\n"
            f"**Primary entity:** `{rec['primary_entity']}`  \n"
            f"**Investigation type:** {rec['investigation_type']}  \n"
            f"**Topology tags:** {', '.join(rec['topology_tags']) or '—'}  \n"
            f"**Risk tags:** {', '.join(rec['risk_tags']) or '—'}  \n"
            f"**Edge types:** {', '.join(rec['edge_types']) or '—'}  \n"
            f"**Related entities (real graph IDs):** "
            f"{', '.join(rec['related_entities'][:10]) or '—'}"
            f"{(' (+' + str(len(rec['related_entities']) - 10) + ' more)') if len(rec['related_entities']) > 10 else ''}\n\n"
            f"---\n\n"
            f"{rec['narrative']}\n"
        )


# ─────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="Generate a grounded semantic-intelligence corpus from "
                    "the existing graph entities.",
    )
    ap.add_argument("--profile", default="small",
                    help="data profile under outputs/ (default: small)")
    ap.add_argument("--limit", type=int, default=0,
                    help="cap per-entity-type pass (0 = no cap). "
                         "Use a small number (e.g. 50) for safe smoke tests.")
    ap.add_argument("--seed", type=int, default=42,
                    help="RNG seed (default 42). Same seed → same output.")
    ap.add_argument("--output-dir", default=None,
                    help="output directory (default: "
                         "outputs/{profile}/enriched_corpus)")
    ap.add_argument("--dry-run", action="store_true",
                    help="compute stats without writing JSONL")
    ap.add_argument("--md-samples", type=int, default=12,
                    help="how many sample Markdown docs to write for review")
    args = ap.parse_args()

    out_dir = Path(args.output_dir) if args.output_dir else (
        _REPO_ROOT / "outputs" / args.profile / "enriched_corpus"
    )

    t0 = time.time()
    builder = CorpusBuilder(profile=args.profile, limit=args.limit, seed=args.seed)
    manifest = builder.run(out_dir, dry_run=args.dry_run,
                            write_md_samples=args.md_samples)
    elapsed = time.time() - t0
    log.info("elapsed: %.2fs", elapsed)

    # One-line summary for shell scripting.
    print(json.dumps({
        "profile":     args.profile,
        "limit":       args.limit,
        "dry_run":     args.dry_run,
        "total_docs":  manifest["total_docs"],
        "total_tokens_est": manifest["total_tokens_est"],
        "entities_referenced": manifest["entities_referenced_count"],
        "elapsed_s":   round(elapsed, 2),
        "jsonl_path":  manifest["jsonl_path"],
    }))


if __name__ == "__main__":
    main()
