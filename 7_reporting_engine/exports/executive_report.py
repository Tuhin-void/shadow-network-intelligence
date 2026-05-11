"""
Shadow Network Intelligence - Executive Report Generator
Generates executive summary reports
"""
from typing import Dict, List, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ExecutiveReportGenerator:
    """
    Generates executive summary reports from investigation results.
    """
    
    def __init__(self):
        self.report_version = "1.0"
    
    def generate(
        self,
        period_start: datetime,
        period_end: datetime,
        investigations: List[Dict],
        metrics: Dict
    ) -> Dict[str, Any]:
        """Generate executive summary report"""
        
        high_risk = sum(1 for i in investigations if i.get("risk_level") in ["HIGH", "CRITICAL"])
        
        return {
            "report_type": "EXECUTIVE_SUMMARY",
            "version": self.report_version,
            "period": {
                "start": period_start.isoformat(),
                "end": period_end.isoformat()
            },
            "summary": {
                "total_investigations": len(investigations),
                "high_risk_cases": high_risk,
                "sar_filings": metrics.get("sar_count", 0),
                "avg_investigation_time_ms": metrics.get("avg_time", 0)
            },
            "risk_breakdown": self._get_risk_breakdown(investigations),
            "top_patterns": self._get_top_patterns(investigations),
            "recommendations": self._get_recommendations(investigations, high_risk),
            "generated_at": datetime.now().isoformat()
        }
    
    def _get_risk_breakdown(self, investigations: List[Dict]) -> Dict[str, int]:
        """Get breakdown by risk level"""
        breakdown = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for inv in investigations:
            level = inv.get("risk_level", "LOW")
            if level in breakdown:
                breakdown[level] += 1
        return breakdown
    
    def _get_top_patterns(self, investigations: List[Dict]) -> List[Dict]:
        """Get most common patterns"""
        pattern_counts = {}
        for inv in investigations:
            for pattern in inv.get("patterns_detected", []):
                pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
        
        return sorted(
            [{"pattern": k, "count": v} for k, v in pattern_counts.items()],
            key=lambda x: x["count"],
            reverse=True
        )[:5]
    
    def _get_recommendations(
        self,
        investigations: List[Dict],
        high_risk_count: int
    ) -> List[str]:
        """Get executive recommendations"""
        recommendations = []
        
        if high_risk_count > 10:
            recommendations.append(
                "Consider increasing compliance staff to handle elevated caseload"
            )
        
        recommendations.append(
            "Review and update transaction monitoring thresholds"
        )
        
        recommendations.append(
            "Schedule quarterly review of shell company detection rules"
        )
        
        return recommendations