"""Evidence chain builder — constructs structured evidence from graph retrieval."""
from typing import Optional


class EvidenceChainBuilder:
    """
    Builds structured evidence chains from graph retrieval results.
    - Max 5 evidence items (2 high-risk entities, 3 key relationships)
    - Entity evidence extraction
    - Relationship chain construction
    - Confidence scoring
    """

    PRIORITY_EDGES = {
        "OWNS", "SENT_TRANSACTION", "RECEIVED_TRANSACTION",
        "TRANSFERRED_TO", "REGISTERED_AT", "BENEFITS_FROM",
        "PERSON_MEMBER_OF_RING", "COMPANY_MEMBER_OF_RING",
        "ACCOUNT_MEMBER_OF_RING", "TRANSACTION_MEMBER_OF_RING",
    }

    def __init__(self):
        self.evidence_id = 0

    def build_chain(
        self,
        retrieval_result: dict,
        query: str = "",
    ) -> list[dict]:
        """
        Build compressed evidence chain — max 5 items.
        Priority 1: High-risk entities (max 2, risk >= 0.5)
        Priority 2: Key relationships (max 3)
        """
        chain = []

        entities = retrieval_result.get("entities", [])
        seen_entity_names = set()
        unique_entities = []
        for e in entities:
            name = e.get("name", e.get("v_id", ""))
            if name not in seen_entity_names:
                seen_entity_names.add(name)
                unique_entities.append(e)

        # Pick the 2 most relevant entities as evidence:
        #   - prefer high-risk (>= 0.5), since they're the smoking-gun candidates
        #   - if none reach that bar, fall back to top-score (so an explanation
        #     is always produced — the chain never silently goes empty)
        high_risk_entities = [e for e in unique_entities if (e.get("risk_score") or 0) >= 0.5]
        high_risk_entities.sort(key=lambda x: x.get("risk_score") or 0, reverse=True)
        if not high_risk_entities and unique_entities:
            high_risk_entities = sorted(
                unique_entities,
                key=lambda x: (x.get("score") or 0, x.get("risk_score") or 0),
                reverse=True,
            )

        for e in high_risk_entities[:2]:
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

        seen_conn_keys = set()
        unique_context = []
        for n in context:
            key = (n.get("name") or n.get("v_id", ""), n.get("edge", ""))
            if key not in seen_conn_keys:
                seen_conn_keys.add(key)
                unique_context.append(n)

        priority_edges = [n for n in unique_context if n.get("edge", "") in self.PRIORITY_EDGES]
        priority_edges.sort(key=lambda x: x.get("risk_score") or 0, reverse=True)
        other_edges = [n for n in unique_context if n.get("edge", "") not in self.PRIORITY_EDGES]
        other_edges.sort(key=lambda x: x.get("risk_score") or 0, reverse=True)

        key_relationships = priority_edges[:3]
        if len(key_relationships) < 3:
            key_relationships.extend(other_edges[:3 - len(key_relationships)])

        for n in key_relationships[:3]:
            self.evidence_id += 1
            evidence = {
                "id": f"E{self.evidence_id:04d}",
                "type": "relationship",
                "source": "graph",
                "content": f"{n.get('type', '?')}: {n.get('name') or n.get('v_id', '?')} via {n.get('edge', '?')}",
                "strength": 0.6 if n.get("depth", 0) <= 2 else 0.4,
                "provenance": {
                    "v_id": n.get("v_id", ""),
                    "edge_type": n.get("edge", ""),
                    "depth": n.get("depth", 0),
                },
            }
            chain.append(evidence)

        return chain[:5]

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

    def to_context_string(self, chain: list[dict], max_items: int = 5) -> str:
        """Convert evidence chain to a compact context string."""
        lines = ["Evidence Chain:"]
        for e in chain[:max_items]:
            strength_bar = "█" * int(e["strength"] * 10) + "░" * (10 - int(e["strength"] * 10))
            lines.append(f"[{e['id']}] [{strength_bar}] {e['content']}")
        return "\n".join(lines)