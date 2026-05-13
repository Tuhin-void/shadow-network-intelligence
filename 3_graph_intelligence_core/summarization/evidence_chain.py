"""Evidence chain builder — constructs structured evidence from graph retrieval."""
from typing import Optional


class EvidenceChainBuilder:
    """
    Builds structured evidence chains from graph retrieval results.
    - Entity evidence extraction
    - Relationship chain construction
    - Supporting/proving/conflicting evidence classification
    - Confidence scoring
    """

    def __init__(self):
        self.evidence_id = 0

    def build_chain(
        self,
        retrieval_result: dict,
        query: str = "",
    ) -> list[dict]:
        """
        Build evidence chain from retrieval results.
        Returns list of evidence items with type, content, strength.
        """
        chain = []

        entities = retrieval_result.get("entities", [])
        for e in entities:
            self.evidence_id += 1
            evidence = {
                "id": f"E{self.evidence_id:04d}",
                "type": "entity",
                "source": "graph",
                "content": self._entity_evidence_text(e),
                "strength": self._compute_strength(e),
                "provenance": {
                    "v_id": e.get("v_id", ""),
                    "type": e.get("type", ""),
                    "score": e.get("score", 0),
                },
            }
            chain.append(evidence)

        context = retrieval_result.get("context", [])
        for n in context[:20]:
            self.evidence_id += 1
            evidence = {
                "id": f"E{self.evidence_id:04d}",
                "type": "relationship",
                "source": "graph",
                "content": f"{n.get('type', '?')}: {n.get('name', n.get('v_id', '?'))} via {n.get('edge', '?')}",
                "strength": 0.6 if n.get("depth", 0) <= 2 else 0.4,
                "provenance": {
                    "v_id": n.get("v_id", ""),
                    "edge_type": n.get("edge", ""),
                    "depth": n.get("depth", 0),
                },
            }
            chain.append(evidence)

        return chain

    def _entity_evidence_text(self, entity: dict) -> str:
        vtype = entity.get("type", "Entity")
        name = entity.get("name", entity.get("v_id", "?"))
        risk = entity.get("risk_score") or entity.get("risk", None)
        risk_str = f" (risk={risk:.2f})" if risk else ""
        return f"{vtype}: {name}{risk_str}"

    def _compute_strength(self, entity: dict) -> float:
        base = entity.get("score", 0.5)
        risk = entity.get("risk_score") or entity.get("risk", 0)
        if risk > 0.8:
            return min(base * 1.2, 1.0)
        return base

    def classify_chain(
        self,
        chain: list[dict],
    ) -> dict:
        """
        Classify evidence chain by strength and type.
        Returns {supporting: [], proving: [], conflicting: [], summary: str}.
        """
        supporting = [e for e in chain if e["strength"] >= 0.7]
        proving = [e for e in chain if e["strength"] >= 0.9]
        weak = [e for e in chain if e["strength"] < 0.5]
        conflicting = [e for e in weak if e["type"] == "entity"]

        return {
            "supporting": supporting,
            "proving": proving,
            "conflicting": conflicting,
            "weak": weak,
            "total_evidence": len(chain),
            "summary": self._chain_summary(chain),
        }

    def _chain_summary(self, chain: list[dict]) -> str:
        entity_count = sum(1 for e in chain if e["type"] == "entity")
        rel_count = sum(1 for e in chain if e["type"] == "relationship")
        strong = sum(1 for e in chain if e["strength"] >= 0.7)
        return (f"Evidence chain: {len(chain)} items "
                f"(entity={entity_count}, relationship={rel_count}, "
                f"strong={strong})")

    def to_context_string(self, chain: list[dict], max_items: int = 15) -> str:
        """Convert evidence chain to a compact context string."""
        lines = ["Evidence Chain:"]
        for e in chain[:max_items]:
            strength_bar = "█" * int(e["strength"] * 10) + "░" * (10 - int(e["strength"] * 10))
            lines.append(f"[{e['id']}] [{strength_bar}] {e['content']}")
        return "\n".join(lines)