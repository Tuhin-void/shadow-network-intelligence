"""Rule-based summarizer — deterministic compression of graph retrieval results."""
from typing import Optional


class GraphAwareSummarizer:
    """
    Compresses graph retrieval results into compact output (max 250 tokens).
    - Entity prioritization by risk score (>= 0.5 high risk)
    - Relationship pattern extraction (OWNS, SENT_TRANSACTION, etc.)
    - Strict single paragraph or bulleted list format
    """

    PRIORITY_EDGES = {"OWNS", "SENT_TRANSACTION", "RECEIVED_TRANSACTION", "PART_OF", "REGISTERED_AT"}

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

        high_risk_entities = [e for e in unique_entities if (e.get("risk_score") or 0) >= 0.5]
        high_risk_entities.sort(key=lambda x: x.get("risk_score", 0), reverse=True)
        top_entities = high_risk_entities[:6]

        seen_connection_keys = set()
        unique_context = []
        for n in context:
            key = (n.get("name", n.get("v_id", "")), n.get("edge", ""))
            if key not in seen_connection_keys:
                seen_connection_keys.add(key)
                unique_context.append(n)

        priority_edges = sorted(
            [n for n in unique_context if n.get("edge", "") in self.PRIORITY_EDGES],
            key=lambda x: x.get("risk_score", 0),
            reverse=True,
        )
        other_edges = sorted(
            [n for n in unique_context if n.get("edge", "") not in self.PRIORITY_EDGES],
            key=lambda x: x.get("risk_score", 0),
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

        lines = ["GRAPH SUMMARY:"]
        if top_entities:
            entity_strs = [f"[{e.get('type', 'Entity')}:{e.get('name', e.get('v_id', '?'))}]" for e in top_entities]
            lines.append(f"Entities: {', '.join(entity_strs)} ({len(entities)} total)")
        else:
            lines.append("Entities: None")

        if risk_flags:
            lines.append(f"Risk Flags: [{', '.join(sorted(risk_flags))}]")

        if top_connections:
            conn_strs = []
            for n in top_connections:
                src = n.get("type", "?")
                edge = n.get("edge", "?")
                tgt = n.get("name", n.get("v_id", "?"))
                conn_strs.append(f"[{src}]--[{edge}]-->[{tgt}]")
            lines.append(f"Connections: {', '.join(conn_strs)}")

        if entity_type_counts:
            type_summary = ", ".join(f"{k}({v})" for k, v in sorted(entity_type_counts.items()))
            lines.append(f"Type Distribution: {type_summary}")

        if total_risk > 0:
            lines.append(f"Total Risk: {total_risk:.2f}")

        combined = " ".join(lines)
        return self._truncate(combined, max_output_tokens)

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