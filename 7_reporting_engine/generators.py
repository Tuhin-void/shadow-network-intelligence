"""
Production-grade investigation report generators.

Each generator takes structured inputs (engine_result + swarm_report +
synthesis) and produces a markdown report + parallel JSON. Outputs are
written to `7_reporting_engine/outputs/<timestamp>__<kind>__<query_id>.{md,json}`.

Four generators:
  • InvestigationBriefGenerator       — narrative investigation dossier
  • FraudRingSummaryGenerator         — ring-centric structural summary
  • SanctionsExposureReportGenerator  — sanctioned-entity exposure tracing
  • BenchmarkSummaryGenerator         — adversarial + reliability + TG validation
                                        consolidated in one report

Generators are pure — no graph or LLM calls. They project structured input
into operational deliverables.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _safe_slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "-", s.strip().lower())[:48].strip("-")


@dataclass
class GeneratedReport:
    kind: str
    markdown_path: Path
    json_path: Path
    title: str

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "title": self.title,
            "markdown_path": str(self.markdown_path),
            "json_path": str(self.json_path),
        }


def _write_pair(kind: str, title: str, slug: str,
                body: str, data: dict) -> GeneratedReport:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    base = f"{_ts()}__{kind}__{_safe_slug(slug)}"
    md_path = OUTPUT_DIR / f"{base}.md"
    json_path = OUTPUT_DIR / f"{base}.json"
    md_path.write_text(body)
    json_path.write_text(json.dumps(data, indent=2, default=str))
    return GeneratedReport(kind=kind, markdown_path=md_path,
                           json_path=json_path, title=title)


# ── Investigation brief ────────────────────────────────────────────────────


class InvestigationBriefGenerator:
    """The general-purpose narrative dossier for any investigation."""

    kind = "investigation_brief"

    def generate(self, *, query: str, engine_result: dict, swarm_report: Any,
                 synthesis: Any) -> GeneratedReport:
        md = engine_result.get("metadata", {}) or {}
        suspects = engine_result.get("entities", []) or []
        ctx = engine_result.get("context", []) or []

        title = f"Investigation brief — {query[:60]}"
        lines = [
            f"# {title}",
            "",
            f"_Generated {_ts()}_",
            "",
            "## Headline",
            "",
            synthesis.headline,
            "",
            "## Coordinator summary",
            "",
            swarm_report.coordinator_summary,
            "",
            "## Operational metadata",
            "",
            f"- Query: `{query}`",
            f"- Investigation ID: `{swarm_report.investigation_id}`",
            f"- Engine strategy: `{md.get('strategy', '—')}`",
            f"- Elapsed: **{swarm_report.elapsed_ms:.0f} ms**",
            f"- Cache hit: `{md.get('cache_hit', False)}`",
            f"- Overall structural confidence: **{synthesis.overall_confidence:.2f}**",
            f"- Average agent confidence: **{swarm_report.consolidated_metrics.get('avg_agent_confidence', 0):.2f}**",
            "",
            "## Suspects",
            "",
            "| # | id | type | name | rerank reason | ring_touch | fraud_degree |",
            "|---|---|---|---|---|---:|---:|",
        ]
        for i, s in enumerate(suspects[:10], 1):
            lines.append(
                f"| {i} | `{s.get('v_id','')}` | {s.get('type','')} | "
                f"{s.get('name','')} | {s.get('rerank_reason','')} | "
                f"{s.get('ring_touch_count', 0)} | {s.get('fraud_degree', 0)} |"
            )

        lines += ["", "## Key claims (structural evidence)", ""]
        for c in synthesis.key_claims[:14]:
            lines.append(f"- **[{c.basis}]** {c.statement}  _(conf {c.confidence:.2f})_")

        if synthesis.contradictions:
            lines += ["", "## Contradictions flagged", ""]
            for x in synthesis.contradictions[:6]:
                lines.append(f"- {x.reason}")

        lines += ["", "## Agent findings", ""]
        for a in swarm_report.agents:
            lines.append(f"### {a.agent.replace('_',' ').title()} — confidence {a.confidence:.2f}")
            lines.append("")
            lines.append(a.summary)
            lines.append("")
            for k, v in a.metrics.items():
                lines.append(f"- {k}: **{v}**")
            for n in a.notes:
                lines.append(f"- ⚠ {n}")
            lines.append("")

        lines += ["", "## Per-suspect explanations", ""]
        for vid, reason in list(synthesis.explanations.items())[:10]:
            lines.append(f"- `{vid}` — {reason}")

        body = "\n".join(lines)
        data = {
            "kind": self.kind,
            "title": title,
            "query": query,
            "investigation_id": swarm_report.investigation_id,
            "elapsed_ms": swarm_report.elapsed_ms,
            "metadata": md,
            "suspects": suspects[:20],
            "synthesis": synthesis.to_dict(),
            "swarm_summary": swarm_report.coordinator_summary,
            "consolidated_metrics": swarm_report.consolidated_metrics,
        }
        return _write_pair(self.kind, title, query, body, data)


# ── Fraud ring summary ─────────────────────────────────────────────────────


class FraudRingSummaryGenerator:
    """Ring-centric summary: members, severity, structural density."""

    kind = "fraud_ring_summary"

    def generate(self, *, ring_id: str, engine_result: dict, swarm_report: Any,
                 synthesis: Any) -> GeneratedReport:
        ctx = engine_result.get("context", []) or []
        suspects = engine_result.get("entities", []) or []

        # Members are: (a) suspects whose rerank reason mentions this ring,
        # (b) endpoints of ring-membership edges touching this ring.
        members: dict[str, dict[str, Any]] = {}
        for s in suspects:
            rr = (s.get("rerank_reason") or "")
            if ring_id in rr:
                members[s.get("v_id", "")] = {
                    "v_id": s.get("v_id"),
                    "type": s.get("type"),
                    "name": s.get("name"),
                    "source": "suspect_set",
                }
        for n in ctx:
            edge = (n.get("edge") or "")
            if ring_id not in (n.get("via", ""), n.get("v_id", "")):
                continue
            # the non-FR side of the edge is the member
            mid = n.get("v_id") if n.get("via", "").startswith("FR-") else n.get("via")
            if mid and not (isinstance(mid, str) and mid.startswith("FR-")):
                members.setdefault(mid, {
                    "v_id": mid,
                    "type": n.get("type", ""),
                    "name": n.get("name", mid),
                    "source": f"via {edge}",
                })

        title = f"Fraud ring summary — {ring_id}"
        lines = [
            f"# {title}",
            "",
            f"_Generated {_ts()}_",
            "",
            "## Overview",
            "",
            f"- Ring ID: `{ring_id}`",
            f"- Members surfaced: **{len(members)}**",
            f"- Investigation: `{swarm_report.investigation_id}`",
            f"- Overall confidence: **{synthesis.overall_confidence:.2f}**",
            "",
            "## Member entities",
            "",
            "| v_id | type | name | source |",
            "|---|---|---|---|",
        ]
        for m in list(members.values())[:50]:
            lines.append(f"| `{m['v_id']}` | {m['type']} | "
                         f"{m['name']} | {m['source']} |")

        # Pull ring-relevant claims
        ring_claims = [c for c in synthesis.key_claims if c.basis == "ring"]
        if ring_claims:
            lines += ["", "## Ring-edge structural claims", ""]
            for c in ring_claims[:12]:
                lines.append(f"- {c.statement}  _(conf {c.confidence:.2f})_")

        # Pull ring analyst finding if present
        ring_finding = next((a for a in swarm_report.agents
                             if a.agent == "fraud_ring_analyst"), None)
        if ring_finding:
            lines += ["", "## Ring analyst metrics", ""]
            for k, v in ring_finding.metrics.items():
                lines.append(f"- {k}: **{v}**")

        body = "\n".join(lines)
        data = {
            "kind": self.kind,
            "title": title,
            "ring_id": ring_id,
            "members": list(members.values()),
            "ring_claims": [{"statement": c.statement, "confidence": c.confidence}
                            for c in ring_claims],
            "consolidated_metrics": swarm_report.consolidated_metrics,
        }
        return _write_pair(self.kind, title, ring_id, body, data)


# ── Sanctions exposure report ──────────────────────────────────────────────


class SanctionsExposureReportGenerator:
    """Sanctioned-entity exposure report — flagged + downstream flows."""

    kind = "sanctions_exposure"

    def generate(self, *, query: str, swarm_report: Any,
                 synthesis: Any) -> GeneratedReport:
        title = f"Sanctions exposure — {query[:48]}"
        # Pull the sanctions tracer finding.
        tracer = next((a for a in swarm_report.agents
                       if a.agent == "sanctions_exposure_tracer"), None)
        if not tracer or not tracer.findings:
            findings_block = "_no sanctions tracer findings_"
            flagged: list = []
            flow_paths: list = []
        else:
            f = tracer.findings[0]
            flagged = f.get("flagged_entities", [])
            flow_paths = f.get("flow_paths", [])
            findings_block = (f"Flagged entities: {len(flagged)} · "
                              f"flow paths traced: {len(flow_paths)}")

        lines = [
            f"# {title}",
            "",
            f"_Generated {_ts()}_",
            "",
            f"- Query: `{query}`",
            f"- Investigation: `{swarm_report.investigation_id}`",
            f"- Overall confidence: **{synthesis.overall_confidence:.2f}**",
            "",
            "## Tracer summary",
            "",
            findings_block,
            "",
            "## Flagged entities",
            "",
        ]
        if not flagged:
            lines.append("_None surfaced in this retrieval._")
        else:
            lines += ["| v_id | name |", "|---|---|"]
            for f in flagged[:30]:
                lines.append(f"| `{f.get('v_id','')}` | {f.get('name','')} |")

        lines += ["", "## Downstream flow exposure", ""]
        if not flow_paths:
            lines.append("_No fund flows traced from flagged entities._")
        else:
            lines += ["| from | to | edge | depth |", "|---|---|---|---|"]
            for p in flow_paths[:30]:
                lines.append(f"| `{p.get('from','')}` | `{p.get('to','')}` | "
                             f"`{p.get('edge','')}` | {p.get('depth', 1)} |")

        body = "\n".join(lines)
        data = {
            "kind": self.kind,
            "title": title,
            "query": query,
            "flagged_entities": flagged,
            "flow_paths": flow_paths,
            "metrics": (tracer.metrics if tracer else {}),
        }
        return _write_pair(self.kind, title, query, body, data)


# ── Benchmark summary ──────────────────────────────────────────────────────


class BenchmarkSummaryGenerator:
    """
    Reads the adversarial + reliability + TG-validation artifacts produced
    by scripts/ and emits a clean executive-grade benchmark summary.
    """

    kind = "benchmark_summary"

    def generate(self, *, project_root: Path) -> GeneratedReport:
        scripts_dir = project_root / "scripts"
        adv_md = (scripts_dir / "adversarial_results.md").read_text() \
                 if (scripts_dir / "adversarial_results.md").exists() else None
        rel_json = (scripts_dir / "benchmark_reliability.json")
        tg_json = (scripts_dir / "tigergraph_validation.json")
        rel = json.loads(rel_json.read_text()) if rel_json.exists() else None
        tg = json.loads(tg_json.read_text()) if tg_json.exists() else None

        title = "Benchmark summary — adversarial + reliability + TigerGraph validation"
        lines = [
            f"# {title}",
            "",
            f"_Generated {_ts()}_",
            "",
            "## TigerGraph operational state",
            "",
        ]
        if not tg:
            lines.append("_No `tigergraph_validation.json` found._")
        else:
            lines += [
                f"- Status: **{tg.get('status')}**",
                f"- Vertex total: **{tg.get('vertex_total', 0):,}**",
                f"- Edge total:   **{tg.get('edge_total', 0):,}**",
                f"- Reverse edges observed: **{len(tg.get('reverse_edges_observed') or {})}**",
                f"- Rings with members: **{tg.get('rings_with_members', 0)}** / "
                f"{len(tg.get('ring_probe') or [])} sampled",
            ]

        lines += ["", "## Reliability", ""]
        if not rel:
            lines.append("_No `benchmark_reliability.json` found._")
        else:
            lines += [
                f"- Verdict: **{rel.get('status')}**",
                f"- Queries × trials: {rel.get('queries_run', 0)} × "
                f"{rel.get('trials_per_query', 0)}",
                f"- Structural drift: **{rel.get('structural_drift_count', 0)}** (target: 0)",
                f"- Empty answers:    **{rel.get('empty_answer_count', 0)}** (target: 0)",
            ]

        lines += ["", "## Adversarial benchmark (excerpt)", ""]
        if adv_md is None:
            lines.append("_No `adversarial_results.md` found._")
        else:
            captured: list[str] = []
            in_table = False
            for raw in adv_md.splitlines():
                if raw.startswith("## Summary Table"):
                    in_table = True
                    continue
                if in_table:
                    if raw.startswith("## "):
                        break
                    captured.append(raw)
            lines += captured

        lines += [
            "",
            "## Thesis",
            "",
            "GraphRAG superiority emerges from **relationship topology** — the answer",
            "is an edge, not a sentence. VectorRAG-style chunked retrieval cannot",
            "reconstruct ring memberships, hidden ownership, or laundering chains",
            "from text alone; only graph traversal recovers the structural answer.",
            "",
        ]
        body = "\n".join(lines)
        data = {
            "kind": self.kind,
            "title": title,
            "tigergraph": tg,
            "reliability": rel,
            "adversarial_present": adv_md is not None,
        }
        return _write_pair(self.kind, title, "benchmark", body, data)
