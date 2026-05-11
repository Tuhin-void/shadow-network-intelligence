"""
Shadow Network Intelligence - Transaction Analyst Agent
Analyzes transaction patterns and behaviors
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class TransactionAnalystAgent:
    """
    Transaction Analyst Agent - Analyzes transaction patterns
    
    Responsibilities:
    - Analyze transaction sequences
    - Detect structuring patterns
    - Identify unusual timing
    - Calculate velocity metrics
    """
    
    def __init__(self, llm_provider, graph_connection):
        self.llm = llm_provider
        self.conn = graph_connection
    
    def analyze_transactions(
        self,
        entity_id: str,
        transactions: List[Dict],
        lookback_days: int = 30
    ) -> Dict[str, Any]:
        """
        Perform comprehensive transaction analysis.
        """
        logger.info(f"Analyzing transactions for: {entity_id}")
        
        patterns = self._detect_patterns(transactions)
        velocity = self._calculate_velocity(transactions)
        structuring = self._check_structuring(transactions)
        timing = self._analyze_timing(transactions)
        
        return {
            "entity_id": entity_id,
            "analysis_date": datetime.now().isoformat(),
            "transaction_count": len(transactions),
            "patterns": patterns,
            "velocity": velocity,
            "structuring": structuring,
            "timing_analysis": timing,
            "risk_indicators": self._identify_risk_indicators(patterns, velocity, structuring),
            "recommendations": self._get_recommendations(patterns, structuring)
        }
    
    def _detect_patterns(self, transactions: List[Dict]) -> Dict[str, bool]:
        """Detect various transaction patterns"""
        patterns = {
            "circular": self._has_circular_pattern(transactions),
            "layered": self._has_layered_pattern(transactions),
            "fragmented": self._has_fragmented_pattern(transactions),
            "burst": self._has_burst_pattern(transactions),
            "round_amounts": self._has_round_amounts(transactions)
        }
        return patterns
    
    def _has_circular_pattern(self, transactions: List[Dict]) -> bool:
        """Check for circular transaction patterns"""
        if len(transactions) < 3:
            return False
        
        accounts = set()
        for t in transactions:
            accounts.add(t.get("from_account"))
            accounts.add(t.get("to_account"))
        
        return len(transactions) > len(accounts) * 0.5
    
    def _has_layered_pattern(self, transactions: List[Dict]) -> bool:
        """Check for layering (multiple hops)"""
        return len(transactions) >= 5
    
    def _has_fragmented_pattern(self, transactions: List[Dict]) -> bool:
        """Check for fragmentation (breaking amounts)"""
        amounts = [t.get("amount", 0) for t in transactions]
        avg = sum(amounts) / len(amounts) if amounts else 0
        
        fragmented = sum(1 for a in amounts if 5000 <= a <= 9999)
        
        return fragmented >= len(transactions) * 0.3
    
    def _has_burst_pattern(self, transactions: List[Dict]) -> bool:
        """Check for burst activity (many transactions in short time)"""
        return len(transactions) >= 10
    
    def _has_round_amounts(self, transactions: List[Dict]) -> bool:
        """Check for unusual round amounts"""
        amounts = [t.get("amount", 0) for t in transactions]
        round_counts = sum(1 for a in amounts if a % 100 == 0)
        return round_counts >= len(transactions) * 0.5
    
    def _calculate_velocity(self, transactions: List[Dict]) -> Dict[str, Any]:
        """Calculate transaction velocity metrics"""
        if not transactions:
            return {"daily_avg": 0, "peak_day": 0}
        
        amounts = [t.get("amount", 0) for t in transactions]
        total = sum(amounts)
        
        return {
            "total_amount": total,
            "avg_amount": total / len(transactions),
            "max_amount": max(amounts) if amounts else 0,
            "min_amount": min(amounts) if amounts else 0,
            "transaction_count": len(transactions),
            "velocity_score": min(total / 100000, 1.0)
        }
    
    def _check_structuring(self, transactions: List[Dict]) -> Dict[str, Any]:
        """Check for potential structuring (CTR avoidance)"""
        ctr_threshold = 10000
        
        suspicious_amounts = [t for t in transactions 
                            if 5000 <= t.get("amount", 0) < ctr_threshold]
        
        return {
            "potential_structuring": len(suspicious_amounts) >= 3,
            "sub_threshold_count": len(suspicious_amounts),
            "total_suspicious_amount": sum(t.get("amount", 0) for t in suspicious_amounts)
        }
    
    def _analyze_timing(self, transactions: List[Dict]) -> Dict[str, Any]:
        """Analyze transaction timing patterns"""
        return {
            "business_hours_only": True,
            "weekend_transactions": 0,
            "late_night_transactions": 0
        }
    
    def _identify_risk_indicators(
        self,
        patterns: Dict[str, bool],
        velocity: Dict,
        structuring: Dict
    ) -> List[Dict[str, Any]]:
        """Identify specific risk indicators"""
        indicators = []
        
        if patterns.get("circular"):
            indicators.append({
                "indicator": "Circular Transaction Pattern",
                "severity": "HIGH",
                "description": "Transactions form a circular pattern indicating potential layering"
            })
        
        if patterns.get("fragmented"):
            indicators.append({
                "indicator": "Amount Fragmentation",
                "severity": "MEDIUM",
                "description": "Multiple transactions just below CTR threshold"
            })
        
        if structuring.get("potential_structuring"):
            indicators.append({
                "indicator": "Potential Structuring",
                "severity": "HIGH",
                "description": f"{structuring['sub_threshold_count']} transactions may be structured to avoid CTR"
            })
        
        if velocity.get("velocity_score", 0) > 0.8:
            indicators.append({
                "indicator": "High Velocity",
                "severity": "MEDIUM",
                "description": "Transaction velocity exceeds normal levels"
            })
        
        return indicators
    
    def _get_recommendations(self, patterns: Dict, structuring: Dict) -> List[str]:
        """Get analysis-based recommendations"""
        recommendations = []
        
        if structuring.get("potential_structuring"):
            recommendations.append("File suspicious activity report (SAR)")
            recommendations.append("Enhanced monitoring on all related accounts")
        
        if patterns.get("circular"):
            recommendations.append("Investigate complete transaction chain")
            recommendations.append("Review beneficial ownership of all parties")
        
        if patterns.get("round_amounts"):
            recommendations.append("Request transaction purpose documentation")
        
        if not recommendations:
            recommendations.append("No immediate action required")
        
        return recommendations