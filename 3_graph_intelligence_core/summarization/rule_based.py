"""Rule-based summarizer — deterministic compression of graph retrieval results."""
from typing import Optional


class RuleBasedSummarizer:
    """
    Compresses graph retrieval results using deterministic rules.
    - Entity prioritization by risk score and relevance
    - Relationship extraction and categorization
    - Key fact distillation
    - Context window budget management
    """

    def __init__(self, max_tokens: int = 8000):
        self.max_tokens = max_tokens
        self.avg_chars_per_token = 4

    def summarize(
        self,
        retrieval_result: dict,
        query: str = "",
        max_output_tokens: int = 2000,
    ) -> str:
        """
        Summarize graph retrieval results into a compact context.
        """
        if not retrieval_result:
            return "No graph data available."

        chunks = []

        entities = retrieval_result.get("entities", [])
        if entities:
            chunk = self._summarize_entities(entities, query)
            chunks.append(chunk)

        context = retrieval_result.get("context", [])
        if context:
            chunk = self._summarize_neighborhood(context)
            chunks.append(chunk)

        paths = retrieval_result.get("paths", [])
        if paths:
            chunk = self._summarize_paths(paths)
            chunks.append(chunk)

        communities = retrieval_result.get("communities", [])
        if communities:
            chunk = self._summarize_communities(communities)
            chunks.append(chunk)

        combined = "\n\n".join(chunks)
        return self._truncate(combined, max_output_tokens)

    def _summarize_entities(self, entities: list[dict], query: str) -> str:
        if not entities:
            return ""
        lines = ["### Relevant Entities"]
        for e in entities[:10]:
            vtype = e.get("type", "unknown")
            name = e.get("name", e.get("v_id", ""))
            score = e.get("score", 0)
            risk = e.get("risk_score") or e.get("risk", "")
            risk_str = f" [RISK: {risk:.2f}]" if risk else ""

            lines.append(f"- {vtype}: {name} (relevance={score:.2f}){risk_str}")

            attrs = e.get("attributes", {})
            if attrs:
                notable = []
                for key in ("industry", "jurisdiction", "country", "currency", "account_type"):
                    if key in attrs and attrs[key]:
                        notable.append(f"{key}={attrs[key]}")
                if notable:
                    lines.append(f"  Attributes: {', '.join(notable)}")
        return "\n".join(lines)

    def _summarize_neighborhood(self, context: list[dict]) -> str:
        if not context:
            return ""
        lines = ["### Graph Neighborhood"]
        edge_counts = {}
        type_counts = {}

        for n in context:
            et = n.get("edge", "unknown")
            edge_counts[et] = edge_counts.get(et, 0) + 1
            vt = n.get("type", "unknown")
            type_counts[vt] = type_counts.get(vt, 0) + 1

        lines.append(f"Connected entities: {len(context)}")
        lines.append(f"Entity types: {', '.join(f'{k}({v})' for k, v in type_counts.items())}")
        lines.append(f"Edge types: {', '.join(f'{k}({v})' for k, v in edge_counts.items())}")

        for n in context[:5]:
            lines.append(f"- {n.get('type', '?')}: {n.get('name', n.get('v_id', '?'))} via {n.get('edge', '?')}")

        return "\n".join(lines)

    def _summarize_paths(self, paths: list[dict]) -> str:
        if not paths:
            return ""
        lines = ["### Connection Paths"]
        for p in paths[:5]:
            path = p.get("path", [])
            if path:
                lines.append(f"Path ({p.get('length', len(path) - 1)} hops): {' -> '.join(path)}")
        return "\n".join(lines)

    def _summarize_communities(self, communities: list[dict]) -> str:
        if not communities:
            return ""
        lines = ["### Risk Communities"]
        for c in communities[:5]:
            rid = c.get("v_id", c.get("id", "?"))
            rtype = c.get("type", c.get("cluster_type", "?"))
            risk = c.get("risk_score", 0)
            lines.append(f"- {rtype}: {rid} [risk={risk:.2f}]")
        return "\n".join(lines)

    def _truncate(self, text: str, max_chars: int) -> str:
        max_chars = max_chars * self.avg_chars_per_token
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "... [truncated]"

    def compress_retrieval(self, raw_results: dict, budget_tokens: int = 2000) -> dict:
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