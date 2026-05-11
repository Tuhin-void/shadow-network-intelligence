"""
Shadow Network Intelligence - Risk Scorer
Calculates quantitative risk scores for entities and transactions
"""
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class RiskScore:
    """Risk score result"""
    entity_id: str
    score: float
    category: str
    factors: Dict[str, float]
    timestamp: str

class RiskScorer:
    """
    Risk scoring engine for fraud detection.
    
    Combines multiple risk factors into a composite score:
    - Transaction factors (amount, frequency, timing)
    - Network factors (centrality, connectivity)
    - Behavioral factors (deviation from patterns)
    - Geographic factors (jurisdiction risk)
    """
    
    CATEGORIES = {
        (0.0, 0.25): "LOW",
        (0.25, 0.50): "MEDIUM",
        (0.50, 0.75): "HIGH",
        (0.75, 1.0): "CRITICAL"
    }
    
    WEIGHTS = {
        "transaction_amount": 0.30,
        "transaction_frequency": 0.15,
        "network_centrality": 0.20,
        "behavioral_anomaly": 0.15,
        "geographic_risk": 0.10,
        "entity_type": 0.10
    }
    
    def __init__(self, graph_connection=None):
        self.conn = graph_connection
    
    def score_entity(self, entity_id: str, entity_type: str, 
                     transactions: Optional[List[Dict]] = None) -> RiskScore:
        """
        Calculate composite risk score for an entity.
        """
        logger.info(f"Scoring entity: {entity_id}")
        
        factors = {
            "transaction_amount": self._score_amount(transactions or []),
            "transaction_frequency": self._score_frequency(transactions or []),
            "network_centrality": self._score_centrality(entity_id),
            "behavioral_anomaly": self._score_anomaly(transactions or []),
            "geographic_risk": self._score_geography(entity_id),
            "entity_type": self._score_entity_type(entity_type)
        }
        
        composite = self._calculate_composite(factors)
        category = self._categorize(composite)
        
        return RiskScore(
            entity_id=entity_id,
            score=composite,
            category=category,
            factors=factors,
            timestamp=self._get_timestamp()
        )
    
    def score_transaction(self, transaction: Dict) -> float:
        """
        Calculate risk score for a single transaction.
        """
        amount = transaction.get("amount", 0)
        
        if amount >= 100000:
            return 0.9
        elif amount >= 50000:
            return 0.7
        elif amount >= 10000:
            return 0.5
        elif amount >= 5000:
            return 0.3
        else:
            return 0.1
    
    def _score_amount(self, transactions: List[Dict]) -> float:
        """Score based on transaction amounts"""
        if not transactions:
            return 0.0
        
        amounts = [t.get("amount", 0) for t in transactions]
        max_amount = max(amounts) if amounts else 0
        avg_amount = sum(amounts) / len(amounts) if amounts else 0
        
        score = 0.0
        
        if max_amount >= 50000:
            score += 0.4
        elif max_amount >= 10000:
            score += 0.3
        elif max_amount >= 5000:
            score += 0.2
        else:
            score += 0.1
        
        if avg_amount >= 10000:
            score += 0.2
        
        return min(score, 1.0)
    
    def _score_frequency(self, transactions: List[Dict]) -> float:
        """Score based on transaction frequency"""
        if not transactions:
            return 0.0
        
        count = len(transactions)
        
        if count >= 50:
            return 0.8
        elif count >= 20:
            return 0.5
        elif count >= 10:
            return 0.3
        else:
            return 0.1
    
    def _score_centrality(self, entity_id: str) -> float:
        """Score based on network centrality"""
        return 0.3
    
    def _score_anomaly(self, transactions: List[Dict]) -> float:
        """Score based on behavioral anomalies"""
        suspicious = [t for t in transactions if t.get("is_suspicious", False)]
        
        if len(suspicious) >= 3:
            return 0.9
        elif len(suspicious) >= 1:
            return 0.6
        else:
            return 0.2
    
    def _score_geography(self, entity_id: str) -> float:
        """Score based on geographic risk"""
        return 0.2
    
    def _score_entity_type(self, entity_type: str) -> float:
        """Score based on entity type risk"""
        type_scores = {
            "Transaction": 0.3,
            "BankAccount": 0.25,
            "Company": 0.35,
            "Person": 0.2
        }
        return type_scores.get(entity_type, 0.3)
    
    def _calculate_composite(self, factors: Dict[str, float]) -> float:
        """Calculate weighted composite score"""
        composite = 0.0
        
        for factor_name, weight in self.WEIGHTS.items():
            factor_value = factors.get(factor_name, 0.0)
            composite += factor_value * weight
        
        return round(min(max(composite, 0.0), 1.0), 3)
    
    def _categorize(self, score: float) -> str:
        """Categorize score into risk level"""
        for (low, high), category in self.CATEGORIES.items():
            if low <= score < high:
                return category
        return "CRITICAL" if score >= 0.75 else "LOW"
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
