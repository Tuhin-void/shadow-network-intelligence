"""
Graph narrator - converts traversal paths to human-readable narratives.
"""
from typing import List
from ..shared.schemas import TraversalPath
from ..shared.data_loader import AdaptiveDataLoader


class GraphNarrator:
    def __init__(self, data_loader: AdaptiveDataLoader):
        self.data_loader = data_loader

    def narrate(self, traversal_path: TraversalPath) -> str:
        if traversal_path.narrative:
            return traversal_path.narrative

        path = traversal_path.path
        if len(path) < 2:
            return f"Singleton entity: {path[0] if path else 'unknown'}"

        dataset = self.data_loader.load()
        parts = []
        for i, entity_id in enumerate(path):
            entity = dataset.get_entity_by_id(entity_id)
            if entity:
                label = self._entity_label(entity)
                parts.append(label)
            else:
                parts.append(entity_id)

        connections = []
        for i in range(len(parts) - 1):
            connections.append(f" --[{traversal_path.path_type}]--> ")

        segments = []
        for i, part in enumerate(parts):
            if i < len(connections):
                segments.append(part)
                segments.append(connections[i])
            else:
                segments.append(part)

        narrative = "".join(segments)
        if traversal_path.hops > 0:
            narrative += f" ({traversal_path.hops} hop{'s' if traversal_path.hops > 1 else ''}, weight: {traversal_path.weight:.2f})"
        return narrative

    def build_evidence_chain(self, paths: List[TraversalPath], max_paths: int = 5) -> str:
        if not paths:
            return "No traversal paths found."

        chain_parts = ["=== EVIDENCE CHAIN ==="]
        for i, path in enumerate(paths[:max_paths]):
            narrative = self.narrate(path)
            chain_parts.append(f"\n{i+1}. {path.path_type.upper()} PATH ({path.hops} hops):")
            chain_parts.append(f"   {narrative}")
            if path.weight:
                chain_parts.append(f"   Confidence: {path.weight:.2f}")

        if len(paths) > max_paths:
            chain_parts.append(f"\n... and {len(paths) - max_paths} more paths")

        chain_parts.append("\n=== END EVIDENCE CHAIN ===")
        return "\n".join(chain_parts)

    def _entity_label(self, entity: dict) -> str:
        eid = entity.get("id", "")
        etype = eid.split("-")[0] if "-" in eid else ""

        if etype == "P-":
            name = f"{entity.get('first_name', '')} {entity.get('last_name', '')}".strip()
            risk = entity.get("risk_score", 0)
            return f"{name} ({eid}, risk: {risk:.2f})"
        elif etype == "C-":
            name = entity.get("name", eid)
            risk = entity.get("risk_score", 0)
            flags = []
            if entity.get("is_offshore"):
                flags.append("offshore")
            if entity.get("is_shell"):
                flags.append("shell")
            flag_str = f" [{', '.join(flags)}]" if flags else ""
            return f"{name} ({eid}, risk: {risk:.2f}){flag_str}"
        elif etype == "A-":
            atype = entity.get("account_type", "account")
            owner = entity.get("owner_id", "unknown")
            return f"{atype} account {eid} (owner: {owner})"
        elif etype == "TX-" or etype == "T-":
            amount = entity.get("amount", 0)
            frm = entity.get("from_account", "?")
            to = entity.get("to_account", "?")
            return f"${amount:,.2f} transfer from {frm} to {to} ({eid})"
        elif etype == "ADDR-":
            city = entity.get("city", "unknown")
            country = entity.get("country", "")
            return f"address {eid} ({city}, {country})"
        return f"{eid}"

    def explain_advantage(self, graphrag_result: dict, vectorrag_result: dict, pure_llm_result: dict) -> str:
        gr_tokens = graphrag_result.get("tokens", {}).get("total", 0)
        vr_tokens = vectorrag_result.get("tokens", {}).get("total", 0)
        pl_tokens = pure_llm_result.get("tokens", {}).get("total", 0)

        lines = ["=== GRAPHRAG ADVANTAGE EXPLANATION ==="]
        if pl_tokens > 0 and gr_tokens > 0:
            gr_vs_pl = ((pl_tokens - gr_tokens) / pl_tokens) * 100
            lines.append(f"GraphRAG reduced tokens vs Pure LLM: {gr_vs_pl:.1f}%")
        if vr_tokens > 0 and gr_tokens > 0:
            gr_vs_vr = ((vr_tokens - gr_tokens) / vr_tokens) * 100
            lines.append(f"GraphRAG reduced tokens vs Vector RAG: {gr_vs_vr:.1f}%")

        lines.append("\nWhy GraphRAG succeeded:")
        if graphrag_result.get("retrieval", {}).get("nodes_visited", 0) > 0:
            lines.append(f"- Traversed {graphrag_result['retrieval']['nodes_visited']} graph nodes")
        if graphrag_result.get("retrieval", {}).get("traversal_paths"):
            lines.append(f"- Found {len(graphrag_result['retrieval']['traversal_paths'])} explicit relationship paths")
        lines.append("- Graph topology captures ownership chains, shared addresses, transaction flows")
        lines.append("- Neighborhood expansion reveals hidden connections vector search misses")
        lines.append("=== END ===")
        return "\n".join(lines)