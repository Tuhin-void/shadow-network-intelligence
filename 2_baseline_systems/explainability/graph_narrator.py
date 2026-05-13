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
        """
        Build a one-line label for either:
          - CSV-shape dicts (legacy: first_name, last_name, is_offshore, ...)
          - TG-shape dicts  (live schema: name, pep_flag, offshore_flag,
            shell_company_flag, suspicious_flag, account_status, ...)
        """
        # TG vertices are returned as {v_id, type, attributes: {...}}; flatten if so.
        if "attributes" in entity and isinstance(entity["attributes"], dict):
            attrs = entity["attributes"]
            eid = entity.get("v_id") or entity.get("id") or attrs.get("v_id") or ""
            etype_full = entity.get("type", "")
        else:
            attrs = entity
            eid = entity.get("v_id") or entity.get("id") or ""
            etype_full = entity.get("type", "")

        prefix = eid.split("-")[0] + "-" if "-" in eid else ""
        # Resolve canonical entity type from either explicit `type` or ID prefix.
        canonical = etype_full or {
            "P-": "Person", "C-": "Company", "A-": "Account",
            "ADDR-": "Address", "D-": "Device", "TX-": "Transaction",
            "T-": "Transaction", "FR-": "FraudRing",
        }.get(prefix, "")

        risk = attrs.get("risk_score", 0) or 0
        try:
            risk_fmt = f"{float(risk):.2f}"
        except (TypeError, ValueError):
            risk_fmt = str(risk)

        if canonical == "Person":
            # Live: `name`. Legacy CSV: first_name/last_name.
            name = attrs.get("name") or " ".join(
                filter(None, [attrs.get("first_name"), attrs.get("last_name")])
            ).strip() or eid
            flags = []
            if attrs.get("pep_flag")       or attrs.get("is_pep"):       flags.append("PEP")
            if attrs.get("sanctions_flag") or attrs.get("is_sanctioned"): flags.append("sanctioned")
            flag_str = f" [{', '.join(flags)}]" if flags else ""
            return f"{name} ({eid}, risk: {risk_fmt}){flag_str}"

        if canonical == "Company":
            name = attrs.get("name", eid)
            flags = []
            if attrs.get("offshore_flag")      or attrs.get("is_offshore"): flags.append("offshore")
            if attrs.get("shell_company_flag") or attrs.get("is_shell"):    flags.append("shell")
            flag_str = f" [{', '.join(flags)}]" if flags else ""
            return f"{name} ({eid}, risk: {risk_fmt}){flag_str}"

        if canonical == "Account":
            atype = attrs.get("account_type", "account")
            status = attrs.get("account_status") or attrs.get("status", "")
            bank = attrs.get("bank_name", "")
            extra = ", ".join(filter(None, [bank, status]))
            tail = f" ({extra})" if extra else ""
            return f"{atype} account {eid}{tail}"

        if canonical == "Transaction":
            amount = attrs.get("amount", 0)
            try:
                amt_fmt = f"${float(amount):,.2f}"
            except (TypeError, ValueError):
                amt_fmt = str(amount)
            ttype = attrs.get("transaction_type") or attrs.get("tx_type", "")
            suspicious = attrs.get("suspicious_flag") or attrs.get("is_suspicious")
            tag = " [suspicious]" if suspicious else ""
            tail = f" ({ttype})" if ttype else ""
            return f"{amt_fmt} transaction {eid}{tail}{tag}"

        if canonical == "Address":
            city = attrs.get("city", "")
            country = attrs.get("country", "")
            full = attrs.get("full_address") or attrs.get("street_address", "")
            loc = ", ".join(filter(None, [city, country]))
            return f"address {eid} ({loc})" if loc else f"address {eid} ({full})"

        if canonical == "Device":
            dtype = attrs.get("device_type", "device")
            ip = attrs.get("ip_address", "")
            tail = f" ({ip})" if ip else ""
            return f"{dtype} {eid}{tail}"

        if canonical == "FraudRing":
            name = attrs.get("name", eid)
            severity = attrs.get("severity", "")
            ring_type = attrs.get("ring_type", "")
            tag = f" [{severity}/{ring_type}]" if (severity or ring_type) else ""
            return f"fraud ring {name} ({eid}){tag}"

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