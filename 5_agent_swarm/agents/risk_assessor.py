"""
Shadow Network Intelligence - Risk Assessor Agent
Calculates and explains risk scores
"""
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class RiskAssessorAgent:
    """
    Risk Assessor Agent - Calculates risk scores
    
    Responsibilities:
    - Calculate transaction risk scores
    - Assess entity risk levels
    - Identify risk factors
    - Explain risk assessments
    """
    
    def __init__(self, llm_provider, scoring_engine):
        self.llm = llm_provider
        self.scoring = scoring_engine
        self.system_prompt = """You are a financial risk assessor.
        
Your role is to:
1. Calculate quantitative risk scores
2. Identify contributing risk factors
3. Explain risk assessments in plain language
4. Recommend risk-based actions

Risk dimensions:
- Transaction risk (amount, frequency, timing)
- Entity risk (reputation, compliance history)
- Network risk (connected entities, patterns)
- Geographic risk (jurisdiction, destination)

Always provide:
- Overall risk score (0-1)
- Risk category (LOW, MEDIUM, HIGH, CRITICAL)
- Key contributing factors
- Recommended mitigation actions
"""
    
    def assess_risk(self, entity_id: str, entity_type: str, transactions: List[Dict]) -> Dict[str, Any]:
        """
        Assess risk for an entity based on transactions.
        """
        logger.info(f"Assessing risk for {entity_type}: {entity_id}")
        
        transaction_risk = self._assess_transactions(transactions)
        network_risk = self._assess_network(entity_id)
        behavioral_risk = self._assess_behavior(transactions)
        
        overall_score = self._calculate_composite_score(
            transaction_risk, network_risk, behavioral_risk
        )
        
        risk_category = self._categorize_risk(overall_score)
        
        return {
            "entity_id": entity_id,
            "entity_type": entity_type,
            "overall_risk_score": overall_score,
            "risk_category": risk_category,
            "risk_factors": {
                "transaction_risk": transaction_risk,
                "network_risk": network_risk,
                "behavioral_risk": behavioral_risk
            },
            "explanation": self._explain_risk(overall_score, transaction_risk, network_risk, behavioral_risk),
            "recommended_actions": self._get_recommended_actions(risk_category)
        }
    
    def _assess_transactions(self, transactions: List[Dict]) -> float:
        """Assess transaction-based risk"""
        if not transactions:
            return 0.3
        
        amounts = [t.get("amount", 0) for t in transactions]
        avg_amount = sum(amounts) / len(amounts) if amounts else 0
        max_amount = max(amounts) if amounts else 0
        total_amount = sum(amounts) if amounts else 0
        
        risk_score = 0.0
        
        if max_amount > 50000:
            risk_score += 0.3
        elif max_amount > 10000:
            risk_score += 0.2
        else:
            risk_score += 0.1
        
        if len(transactions) > 20:
            risk_score += 0.2
        elif len(transactions) > 5:
            risk_score += 0.1
        
        if avg_amount > 10000:
            risk_score += 0.2
        
        return min(risk_score, 1.0)
    
    def _assess_network(self, entity_id: str) -> float:
        """Assess network-based risk"""
        return 0.4
    
    def _assess_behavior(self, transactions: List[Dict]) -> float:
        """Assess behavioral anomaly risk"""
        return 0.3
    
    def _calculate_composite_score(self, tx_risk: float, net_risk: float, beh_risk: float) -> float:
        """Calculate weighted composite score"""
        weights = {
            "transaction": 0.30,
            "network": 0.25,
            "behavioral": 0.20
        }
        return (tx_risk * 0.30 + net_risk * 0.25 + beh_risk * 0.20)
    
    def _categorize_risk(self, score: float) -> str:
        """Categorize risk score"""
        if score >= 0.8:
            return "CRITICAL"
        elif score >= 0.6:
            return "HIGH"
        elif score >= 0.4:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _explain_risk(self, overall: float, tx: float, net: float, beh: float) -> str:
        """Generate human-readable risk explanation"""
        return f"""Risk Assessment Summary:
- Overall Risk Score: {overall:.2f}
- Transaction Risk: {tx:.2f} ({'High' if tx > 0.5 else 'Moderate' if tx > 0.3 else 'Low'})
- Network Risk: {net:.2f} ({'High' if net > 0.5 else 'Moderate' if net > 0.3 else 'Low'})
- Behavioral Risk: {beh:.2f} ({'High' if beh > 0.5 else 'Moderate' if beh > 0.3 else 'Low'})
"""
    
    def _get_recommended_actions(self, category: str) -> List[str]:
        """Get recommended actions based on risk category"""
        actions = {
            "CRITICAL": ["Immediate account review", "Consider temporary freeze", "File SAR", "Escalate to compliance"],
            "HIGH": ["Enhanced monitoring", "Request additional documentation", "Compliance team notification"],
            "MEDIUM": ["Standard monitoring", "Periodic review"],
            "LOW": ["Routine monitoring", "Annual review"]
        }
        return actions.get(category, ["Standard procedures"])
