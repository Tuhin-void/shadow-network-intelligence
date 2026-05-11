"""
Shadow Network Intelligence - Detective Agent
Investigates suspicious financial activities
"""
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

class DetectiveAgent:
    """
    Detective Agent - Investigates fraud patterns
    
    Responsibilities:
    - Analyze transaction patterns
    - Identify suspicious behaviors
    - Gather evidence
    - Recommend further investigation
    """
    
    def __init__(self, llm_provider, graph_connection):
        self.llm = llm_provider
        self.conn = graph_connection
        self.system_prompt = """You are a fraud detective specializing in financial crime investigation.
        
Your role is to:
1. Analyze transaction data for anomalies
2. Identify potential fraud patterns
3. Trace money flows
4. Build evidence chains
5. Recommend investigation actions

When investigating:
- Look for patterns in timing, amount, and frequency
- Check for known fraud typologies
- Cross-reference with compliance databases
- Document all findings

Provide structured findings with:
- Summary of suspicious activity
- Specific red flags identified
- Evidence collected
- Recommended actions
"""
    
    def investigate(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Conduct an investigation based on user query.
        """
        logger.info(f"Detective investigating: {query}")
        
        evidence = self._collect_evidence(query, context)
        pattern_analysis = self._analyze_patterns(evidence)
        findings = self._generate_findings(pattern_analysis)
        
        return {
            "investigation_id": context.get("investigation_id"),
            "query": query,
            "summary": findings["summary"],
            "red_flags": findings["red_flags"],
            "evidence": evidence,
            "confidence": findings["confidence"],
            "recommended_actions": findings["actions"]
        }
    
    def _collect_evidence(self, query: str, context: Dict) -> List[Dict[str, Any]]:
        """Collect relevant evidence from the graph"""
        evidence = []
        
        if "transaction" in query.lower():
            transactions = self._search_transactions(context.get("entity_id"))
            evidence.extend(transactions)
        
        if "entity" in query.lower() or "company" in query.lower():
            entities = self._search_entities(context.get("entity_id"))
            evidence.extend(entities)
        
        if "relationship" in query.lower() or "connected" in query.lower():
            relationships = self._get_relationships(context.get("entity_id"))
            evidence.extend(relationships)
        
        return evidence
    
    def _analyze_patterns(self, evidence: List[Dict]) -> Dict:
        """Analyze evidence for fraud patterns"""
        patterns = {
            "rapid_transfers": False,
            "circular_payments": False,
            "offshore_connection": False,
            "structuring": False,
            "shell_company": False
        }
        
        amounts = [e.get("amount", 0) for e in evidence if e.get("type") == "transaction"]
        if amounts:
            if max(amounts) > 10000:
                patterns["structuring"] = True
        
        return {"detected_patterns": patterns, "evidence_summary": evidence[:5]}
    
    def _generate_findings(self, analysis: Dict) -> Dict:
        """Generate investigation findings"""
        patterns = analysis["detected_patterns"]
        
        red_flags = []
        if patterns["rapid_transfers"]:
            red_flags.append("Multiple rapid transfers detected")
        if patterns["circular_payments"]:
            red_flags.append("Circular payment pattern identified")
        if patterns["offshore_connection"]:
            red_flags.append("Connection to offshore jurisdiction")
        if patterns["structuring"]:
            red_flags.append("Potential structuring (transactions just under CTR threshold)")
        if patterns["shell_company"]:
            red_flags.append("Shell company indicators present")
        
        actions = []
        if red_flags:
            actions.append("Enhanced monitoring")
        if patterns["structuring"]:
            actions.append("Consider SAR filing")
        if patterns["offshore_connection"]:
            actions.append("Request offshore account documentation")
        
        return {
            "summary": f"Found {len(red_flags)} red flags requiring attention",
            "red_flags": red_flags,
            "confidence": 0.85 if red_flags else 0.50,
            "actions": actions
        }
    
    def _search_transactions(self, entity_id: str) -> List[Dict]:
        """Search for related transactions"""
        if not entity_id:
            return []
        return [{"type": "transaction", "id": "TXN_sample", "amount": 50000}]
    
    def _search_entities(self, entity_id: str) -> List[Dict]:
        """Search for related entities"""
        if not entity_id:
            return []
        return [{"type": "entity", "id": entity_id, "name": "Sample Entity"}]
    
    def _get_relationships(self, entity_id: str) -> List[Dict]:
        """Get entity relationships"""
        if not entity_id:
            return []
        return [{"type": "relationship", "from": entity_id, "to": "RELATED_ENTITY"}]
