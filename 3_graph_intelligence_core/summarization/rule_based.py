"""Rule-based summarizer — deterministic compression of graph retrieval results."""
from typing import Optional


class GraphAwareSummarizer:
    """
    Compresses graph retrieval results into compact output (max 250 tokens).
    - Entity prioritization by risk score (>= 0.5 high risk)
    - Relationship pattern extraction (OWNS, SENT_TRANSACTION, etc.)
    - Strict single paragraph or bulleted list format
    """

    PRIORITY_EDGES = {
        "OWNS", "SENT_TRANSACTION", "RECEIVED_TRANSACTION",
        "TRANSFERRED_TO", "REGISTERED_AT", "BENEFITS_FROM",
        "PERSON_MEMBER_OF_RING", "COMPANY_MEMBER_OF_RING",
        "ACCOUNT_MEMBER_OF_RING", "TRANSACTION_MEMBER_OF_RING",
    }

    def __init__(self, max_tokens: int = 8000):
        self.max_tokens = max_tokens
        self.avg_chars_per_token = 4

    def summarize(
        self,
        retrieval_result: dict,
        query: str = "",
        max_output_tokens: int = 250,
    ) -> str:
        """
        Summarize graph retrieval results into compact context (max 250 tokens).
        """
        if not retrieval_result:
            return "No graph data available."

        entities = retrieval_result.get("entities", [])
        context = retrieval_result.get("context", [])

        seen_entity_names = set()
        unique_entities = []
        for e in entities:
            name = e.get("name", e.get("v_id", ""))
            if name not in seen_entity_names:
                seen_entity_names.add(name)
                unique_entities.append(e)

        # Prefer high-risk entities; if none reach the bar, surface the
        # top-reranked entities anyway (post-topology-rerank `score` already
        # encodes structural relevance, so the report is still meaningful).
        high_risk_entities = [e for e in unique_entities if (e.get("risk_score") or 0) >= 0.5]
        high_risk_entities.sort(key=lambda x: x.get("risk_score") or 0, reverse=True)
        if high_risk_entities:
            top_entities = high_risk_entities[:6]
        else:
            top_entities = sorted(
                unique_entities,
                key=lambda x: (x.get("score") or 0, x.get("ring_touch_count", 0)),
                reverse=True,
            )[:6]

        seen_connection_keys = set()
        unique_context = []
        for n in context:
            key = (n.get("name") or n.get("v_id", ""), n.get("edge", ""))
            if key not in seen_connection_keys:
                seen_connection_keys.add(key)
                unique_context.append(n)

        priority_edges = sorted(
            [n for n in unique_context if n.get("edge", "") in self.PRIORITY_EDGES],
            key=lambda x: x.get("risk_score") or 0,
            reverse=True,
        )
        other_edges = sorted(
            [n for n in unique_context if n.get("edge", "") not in self.PRIORITY_EDGES],
            key=lambda x: x.get("risk_score") or 0,
            reverse=True,
        )
        top_connections = (priority_edges + other_edges)[:6]

        entity_type_counts = {}
        for e in entities:
            t = e.get("type", "unknown")
            entity_type_counts[t] = entity_type_counts.get(t, 0) + 1

        total_risk = 0
        if entities:
            total_risk = sum(e.get("risk_score", 0) or 0 for e in entities) / len(entities)

        risk_flags = set()
        for e in entities:
            attrs = e.get("attributes", {})
            if attrs.get("is_suspicious"):
                risk_flags.add("suspicious")
            if attrs.get("is_enhanced"):
                risk_flags.add("enhanced")
            if attrs.get("high_volume"):
                risk_flags.add("high_volume")
            if attrs.get("offshore"):
                risk_flags.add("offshore")
            if attrs.get("shell_company"):
                risk_flags.add("shell_company")

        # Build an investigative report that visibly leverages graph structure.
        # Sections are produced in priority order; later sections may be
        # truncated by the token budget but earlier ones always survive.
        sections: list[str] = []

        # ── Section 1: Suspects (entities with topology evidence) ─────────
        if top_entities:
            suspect_lines: list[str] = []
            for e in top_entities[:4]:
                eid = e.get("v_id", "?")
                etype = e.get("type", "Entity")
                ename = e.get("name") or eid
                risk = e.get("risk_score") or 0
                ring_touch = e.get("ring_touch_count", 0)
                degree = e.get("fraud_degree", 0)
                badges: list[str] = []
                if ring_touch:
                    badges.append(f"in {ring_touch} ring(s)")
                if degree >= 3:
                    badges.append(f"{degree} fraud-edges")
                try:
                    rfmt = f"{float(risk):.2f}" if float(risk) <= 1 else f"{int(risk)}"
                except (TypeError, ValueError):
                    rfmt = "?"
                badge_str = f" [{', '.join(badges)}]" if badges else ""
                suspect_lines.append(f"  • {etype} {ename} ({eid}) — risk {rfmt}{badge_str}")
            sections.append("SUSPECTS:\n" + "\n".join(suspect_lines))

        # ── Section 2: Ring connections (the highest-value structural signal) ──
        ring_edges = [n for n in unique_context if "_MEMBER_OF_RING" in n.get("edge", "")
                      or "_CONNECTED_TO_RING" in n.get("edge", "")
                      or n.get("edge", "").startswith("co-")]
        if ring_edges:
            ring_lines: list[str] = []
            for n in ring_edges[:5]:
                via = n.get("via", "")
                via_part = f" (via {via})" if via else ""
                ring_lines.append(
                    f"  • {n.get('type', '?')} {n.get('name') or n.get('v_id', '?')} "
                    f"— {n.get('edge', '?')}{via_part}"
                )
            sections.append("RING CONNECTIONS:\n" + "\n".join(ring_lines))

        # ── Section 3: Beneficial-owner / control / ownership chains ──────
        ownership_edges = [n for n in unique_context
                           if n.get("edge", "") in ("OWNS", "BENEFITS_FROM",
                                                     "TRANSFERRED_TO", "HAS_ACCOUNT")]
        if ownership_edges:
            own_lines: list[str] = []
            for n in ownership_edges[:4]:
                via = n.get("via", "")
                via_part = f" (from {via})" if via else ""
                own_lines.append(
                    f"  • {n.get('edge', '?')}: {n.get('type', '?')} "
                    f"{n.get('name') or n.get('v_id', '?')}{via_part}"
                )
            sections.append("OWNERSHIP / FLOW:\n" + "\n".join(own_lines))

        # ── Section 4: Shared-infrastructure (hidden collusion signal) ────
        shared_edges = [n for n in unique_context if n.get("edge", "")
                        in ("SHARES_DEVICE_WITH", "SHARES_ADDRESS_WITH",
                            "USES_DEVICE", "LOCATED_AT", "ACCESSED_FROM",
                            "ASSOCIATED_WITH")]
        if shared_edges:
            shared_lines: list[str] = []
            for n in shared_edges[:4]:
                shared_lines.append(
                    f"  • {n.get('edge', '?')}: {n.get('type', '?')} "
                    f"{n.get('name') or n.get('v_id', '?')}"
                )
            sections.append("SHARED INFRASTRUCTURE:\n" + "\n".join(shared_lines))

        # ── Section 5: Traversal paths (if path retriever found any) ──────
        paths = retrieval_result.get("paths", [])
        if paths:
            path_lines: list[str] = []
            for p in paths[:3]:
                frm = p.get("from", "?")
                to  = p.get("to", "?")
                length = p.get("length") or p.get("path_length") or 0
                path_lines.append(f"  • {frm} → ... → {to}  (length {length})")
            sections.append("TRAVERSAL PATHS:\n" + "\n".join(path_lines))

        # ── Section 6: Aggregate signals ──────────────────────────────────
        agg_bits: list[str] = []
        if entity_type_counts:
            agg_bits.append("Entity mix: " + ", ".join(
                f"{k}={v}" for k, v in sorted(entity_type_counts.items())
            ))
        if risk_flags:
            agg_bits.append("Risk flags: " + ", ".join(sorted(risk_flags)))
        if total_risk > 0:
            agg_bits.append(f"Avg risk: {total_risk:.2f}")
        if agg_bits:
            sections.append("SIGNALS:\n  • " + "\n  • ".join(agg_bits))

        if not sections:
            return "No graph evidence retrieved."

        report = "\n".join(sections)
        return self._truncate(report, max_output_tokens)

    def _truncate(self, text: str, max_chars: int) -> str:
        max_chars = max_chars * self.avg_chars_per_token
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "... [truncated]"

    def compress_retrieval(self, raw_results: dict, budget_tokens: int = 250) -> dict:
        """
        Compress retrieval results to fit within a token budget.
        Returns compressed dict with entity and context summaries.
        """
        max_chars = budget_tokens * self.avg_chars_per_token
        total = self.summarize(raw_results, max_output_tokens=budget_tokens)
        return {"summary": total, "budget_tokens": budget_tokens, "source": "rule_based"}

    def distill_key_facts(self, retrieval_result: dict, max_facts: int = 10) -> list[str]:
        """Extract only the most important facts from retrieval results."""
        facts = []

        entities = retrieval_result.get("entities", [])
        for e in entities:
            risk = e.get("risk_score") or e.get("risk", 0)
            if risk and risk > 0.7:
                name = e.get("name", e.get("v_id", "?"))
                facts.append(f"HIGH RISK: {e.get('type', 'Entity')} {name} (score={risk:.2f})")

        context = retrieval_result.get("context", [])
        edge_types = set(n.get("edge", "") for n in context)
        if "SENT_TRANSACTION" in edge_types or "RECEIVED_TRANSACTION" in edge_types:
            facts.append("Entity has transaction activity")

        if len(entities) > 5:
            facts.append(f"Found {len(entities)} relevant entities")

        return facts[:max_facts]


class RuleBasedSummarizer(GraphAwareSummarizer):
    """Backward compatibility wrapper."""
    pass