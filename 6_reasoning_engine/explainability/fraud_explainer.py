"""
Shadow Network Intelligence - Fraud Explainer
Generates human-readable explanations for fraud detections
"""
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

class FraudExplainer:
    """
    Generates explainable fraud detection reports.
    
    Transforms technical risk scores and pattern matches into
    human-readable explanations for compliance officers.
    """
    
    def __init__(self, llm_provider=None):
        self.llm = llm_provider
    
    def explain_detection(
        self,
        entity_id: str,
        detection_type: str,
        risk_score: float,
        evidence: List[Dict],
        patterns_matched: List[str]
    ) -> Dict[str, Any]:
        """
        Generate explanation for a fraud detection.
        """
        logger.info(f"Explaining {detection_type} for {entity_id}")
        
        explanation = {
            "detection_type": detection_type,
            "entity_id": entity_id,
            "risk_level": self._get_risk_level(risk_score),
            "summary": self._generate_summary(entity_id, detection_type, risk_score),
            "key_findings": self._extract_key_findings(evidence, patterns_matched),
            "evidence_chain": self._build_evidence_chain(evidence),
            "risk_factors": self._identify_risk_factors(evidence),
            "compliance_notes": self._get_compliance_notes(patterns_matched),
            "recommended_review": self._get_review_recommendation(risk_score, patterns_matched)
        }
        
        return explanation
    
    def _get_risk_level(self, score: float) -> str:
        """Convert numeric score to risk level"""
        if score >= 0.8:
            return "CRITICAL"
        elif score >= 0.6:
            return "HIGH"
        elif score >= 0.4:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _generate_summary(self, entity_id: str, detection_type: str, score: float) -> str:
        """Generate brief summary"""
        level = self._get_risk_level(score)
        return f"""
Detection Alert: {detection_type}
Entity: {entity_id}
Risk Level: {level} ({score:.2f})

{self._get_detection_description(detection_type)}
"""
    
    def _get_detection_description(self, detection_type: str) -> str:
        """Get description for detection type"""
        descriptions = {
            "shell_company_ring": "Circular ownership structure detected among multiple companies. This pattern is commonly used to layer illicit funds through multiple shell entities.",
            "laundering_chain": "Layered fund transfer pattern detected across multiple accounts. This suggests potential money laundering activity.",
            "rapid_transfer_loop": "High-frequency transfer activity detected between accounts. This may indicate structuring or rapid movement of funds.",
            "offshore_hop": "Connection to offshore jurisdiction detected. Offshore accounts may be used to evade oversight.",
            "address_collision": "Multiple entities sharing the same address detected. This is a common indicator of shell company operations."
        }
        return descriptions.get(detection_type, "Suspicious pattern detected requiring review.")
    
    def _extract_key_findings(self, evidence: List[Dict], patterns: List[str]) -> List[str]:
        """Extract key findings from evidence"""
        findings = []
        
        amounts = [e.get("amount", 0) for e in evidence if "amount" in e]
        if amounts:
            findings.append(f"Transaction amounts range from ${min(amounts):.0f} to ${max(amounts):.0f}")
        
        if len(evidence) > 10:
            findings.append(f"Large volume of related activity: {len(evidence)} connected entities")
        
        for pattern in patterns:
            findings.append(f"Matched pattern: {pattern}")
        
        return findings
    
    def _build_evidence_chain(self, evidence: List[Dict]) -> List[Dict]:
        """Build evidence chain for review"""
        chain = []
        
        for i, item in enumerate(evidence[:10]):
            chain.append({
                "step": i + 1,
                "type": item.get("type", "unknown"),
                "description": item.get("description", item.get("name", "Evidence item")),
                "significance": item.get("significance", "normal")
            })
        
        return chain
    
    def _identify_risk_factors(self, evidence: List[Dict]) -> List[Dict]:
        """Identify specific risk factors"""
        factors = []
        
        amounts = [e.get("amount", 0) for e in evidence if "amount" in e]
        if amounts and max(amounts) > 10000:
            factors.append({
                "factor": "LARGE_TRANSACTION",
                "severity": "HIGH",
                "detail": f"Transaction of ${max(amounts):.2f} exceeds $10,000 threshold"
            })
        
        suspicious = [e for e in evidence if e.get("is_suspicious")]
        if suspicious:
            factors.append({
                "factor": "SUSPICIOUS_ACTIVITY",
                "severity": "HIGH",
                "detail": f"{len(suspicious)} transactions flagged as suspicious"
            })
        
        offshore = [e for e in evidence if e.get("country") in ["KY", "BS", "CH"]]
        if offshore:
            factors.append({
                "factor": "OFFSHORE_CONNECTION",
                "severity": "MEDIUM",
                "detail": f"Connection to offshore jurisdiction detected"
            })
        
        return factors
    
    def _get_compliance_notes(self, patterns: List[str]) -> List[str]:
        """Get compliance-relevant notes"""
        notes = []
        
        if "laundering_chain" in patterns:
            notes.append("Consider SAR filing under Bank Secrecy Act")
            notes.append("Document complete transaction chain for regulatory review")
        
        if "rapid_transfer_loop" in patterns:
            notes.append("Potential structuring - multiple transactions below CTR threshold")
            notes.append("Review timing patterns for structuring indicators")
        
        if "offshore_hop" in patterns:
            notes.append("Enhanced due diligence required for cross-border transactions")
            notes.append("Consider FBAR filing if offshore account balances > $10,000")
        
        return notes
    
    def _get_review_recommendation(self, score: float, patterns: List[str]) -> Dict[str, Any]:
        """Get recommendation for review process"""
        level = self._get_risk_level(score)
        
        recommendations = {
            "CRITICAL": {
                "priority": "IMMEDIATE",
                "review_timeline": "Within 24 hours",
                "escalation": "Compliance Officer and Legal",
                "actions": [
                    "Temporarily restrict account pending review",
                    "Gather additional documentation",
                    "Prepare SAR if investigation confirms suspicious activity"
                ]
            },
            "HIGH": {
                "priority": "URGENT",
                "review_timeline": "Within 72 hours",
                "escalation": "Compliance Officer",
                "actions": [
                    "Enhanced monitoring",
                    "Request transaction purpose documentation",
                    "Review for potential SAR filing"
                ]
            },
            "MEDIUM": {
                "priority": "STANDARD",
                "review_timeline": "Within 1 week",
                "escalation": "Compliance Team",
                "actions": [
                    "Standard monitoring",
                    "Document review findings",
                    "Update risk profile if warranted"
                ]
            },
            "LOW": {
                "priority": "ROUTINE",
                "review_timeline": "Within 30 days",
                "escalation": "Automated flag only",
                "actions": [
                    "Log for periodic review",
                    "No immediate action required"
                ]
            }
        }
        
        return recommendations.get(level, recommendations["MEDIUM"])
