"""Explainability module — generates explanations for graph retrieval decisions."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class ExplanationItem:
    component: str
    decision: str
    evidence: str
    confidence: float


class GraphExplainer:
    """
    Generates human-readable explanations for graph retrieval decisions.
    - Entity selection rationale
    - Path/relationship significance
    - Risk factor attribution
    """

    def __init__(self):
        pass

    def explain_retrieval(self, retrieval_result: dict) -> str:
        """Explain why certain entities were retrieved."""
        entities = retrieval_result.get("entities", [])
        if not entities:
            return "No graph entities were retrieved for this query."

        lines = [f"Retrieved {len(entities)} entities from the graph:"]

        top_entities = sorted(entities, key=lambda e: e.get("score", 0), reverse=True)[:5]
        for e in top_entities:
            vtype = e.get("type", "Entity")
            name = e.get("name", e.get("v_id", "?"))
            score = e.get("score", 0)
            risk = e.get("risk_score") or e.get("risk", 0)
            lines.append(f"  - {vtype}: {name} (relevance={score:.2f}" +
                         (f", risk={risk:.2f}" if risk else "") + ")")

        context = retrieval_result.get("context", [])
        if context:
            lines.append(f"  Found {len(context)} connected entities in the neighborhood.")

        return "\n".join(lines)

    def explain_path(self, path_result: dict) -> str:
        """Explain path discovery."""
        paths = path_result.get("paths", [])
        if not paths:
            return "No paths found between specified entities."

        lines = [f"Found {len(paths)} connection path(s):"]
        for p in paths[:3]:
            path = p.get("path", [])
            if path:
                lines.append(f"  Path ({p.get('length', len(path)-1)} hops): {' → '.join(path)}")
        return "\n".join(lines)

    def explain_risk(self, entity: dict) -> str:
        """Explain risk factors for an entity."""
        risk = entity.get("risk_score", 0) or entity.get("risk", 0)
        name = entity.get("name", entity.get("v_id", "?"))

        if risk > 0.8:
            verdict = "HIGH risk — multiple indicators present"
        elif risk > 0.5:
            verdict = "MEDIUM risk — some suspicious patterns"
        elif risk > 0.2:
            verdict = "LOW risk — minimal indicators"
        else:
            verdict = "MINIMAL risk — clean profile"

        lines = [f"Risk assessment for {name}: {verdict} (score={risk:.2f})"]

        tags = entity.get("attributes", {}).get("tags", [])
        if tags:
            lines.append(f"  Tags: {', '.join(tags)}")

        return "\n".join(lines)

    def full_explanation(self, query: str, retrieval_result: dict) -> str:
        """Generate full explanation combining all components."""
        parts = [
            f"Query: {query}",
            "",
            self.explain_retrieval(retrieval_result),
        ]

        if retrieval_result.get("paths"):
            parts.append("")
            parts.append(self.explain_path(retrieval_result))

        if retrieval_result.get("communities"):
            parts.append("")
            parts.append(f"Found {len(retrieval_result['communities'])} high-risk community members")

        return "\n".join(parts)