"""
Shadow Network Intelligence - SAR Generator
Generates Suspicious Activity Reports for regulatory filing
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class SARGenerator:
    """
    Generates Suspicious Activity Reports (SARs).
    
    Produces reports in FinCEN-compatible formats for filing
    with regulatory authorities.
    """
    
    SAR_FIELDS = [
        "Filing Institution",
        "Date of Suspicious Activity",
        "Suspicious Activity Type",
        "Amount Involved",
        "Subject Information",
        "Narrative",
        "Disclosure"
    ]
    
    ACTIVITY_TYPES = {
        "MONEY_LAUNDERING": "Money Laundering",
        "FRAUD": "Fraud",
        "TERRORISM_FINANCING": "Terrorist Financing",
        "STRUCTURING": "Structuring",
        "BONAFIDE": "No Suspicious Activity"
    }
    
    def __init__(self):
        self.fincen_format_version = "3.2"
    
    def generate_sar(
        self,
        entity_info: Dict,
        transactions: List[Dict],
        suspicious_activities: List[Dict],
        narrative: str,
        filing_institution: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Generate a complete SAR document.
        """
        logger.info(f"Generating SAR for {entity_info.get('id')}")
        
        total_amount = sum(t.get("amount", 0) for t in transactions)
        
        sar = {
            "report_type": "SAR",
            "version": self.fincen_format_version,
            "generated_at": datetime.now().isoformat(),
            "filing_institution": filing_institution or self._default_institution(),
            "report_date": datetime.now().strftime("%Y-%m-%d"),
            "subject": self._format_subject(entity_info),
            "suspicious_activity": {
                "date_range": self._get_date_range(transactions),
                "total_amount": total_amount,
                "activity_types": [self.ACTIVITY_TYPES.get(a.get("type"), "Other") for a in suspicious_activities],
                "transaction_count": len(transactions),
                "details": suspicious_activities
            },
            "transactions": transactions[:50],
            "narrative": narrative,
            "disclosure": self._standard_disclosure(),
            "prepared_by": entity_info.get("prepared_by", "Automated System")
        }
        
        return sar
    
    def generate_summary(self, sar: Dict) -> str:
        """
        Generate human-readable SAR summary.
        """
        return f"""
========================================
SUSPICIOUS ACTIVITY REPORT SUMMARY
========================================

Report Date: {sar.get('report_date')}
Subject: {sar.get('subject', {}).get('name', 'Unknown')}
Activity Types: {', '.join(sar.get('suspicious_activity', {}).get('activity_types', []))}
Total Amount: ${sar.get('suspicious_activity', {}).get('total_amount', 0):,.2f}
Transactions Reviewed: {sar.get('suspicious_activity', {}).get('transaction_count', 0)}

Filing Institution: {sar.get('filing_institution', {}).get('name', 'Unknown')}

========================================
"""
    
    def _default_institution(self) -> Dict:
        """Default filing institution info"""
        return {
            "name": "Shadow Network Intelligence",
            "type": "Automated Detection System",
            "contact": "compliance@shadownetwork.example"
        }
    
    def _format_subject(self, entity_info: Dict) -> Dict:
        """Format subject information"""
        return {
            "type": entity_info.get("type", "Unknown"),
            "name": entity_info.get("name", "Unknown Entity"),
            "id": entity_info.get("id"),
            "risk_score": entity_info.get("risk_score", 0.0)
        }
    
    def _get_date_range(self, transactions: List[Dict]) -> Dict:
        """Get date range from transactions"""
        if not transactions:
            return {"start": None, "end": None}
        
        dates = [t.get("date", "") for t in transactions if t.get("date")]
        return {
            "start": min(dates) if dates else None,
            "end": max(dates) if dates else None
        }
    
    def _standard_disclosure(self) -> str:
        """Standard SAR disclosure text"""
        return """
CONFIDENTIAL - LAW ENFORCEMENT SENSITIVE

This report is submitted pursuant to 31 U.S.C. § 5318(g) and 31 CFR § 1020.320.

The information contained in this report is proprietary and confidential. 
Unauthorized disclosure or use may be prohibited by law.

By filing this report, the institution does not necessarily disclose all suspicious 
activity of which it has knowledge.
"""
    
    def export_to_json(self, sar: Dict) -> str:
        """Export SAR to JSON format"""
        import json
        return json.dumps(sar, indent=2)
    
    def export_to_html(self, sar: Dict) -> str:
        """Export SAR to HTML format"""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>SAR - {sar.get('subject', {}).get('name')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .header {{ background: #1a365d; color: white; padding: 20px; }}
        .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; }}
        .field {{ margin: 10px 0; }}
        .label {{ font-weight: bold; color: #4a5568; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>SUSPICIOUS ACTIVITY REPORT</h1>
        <p>Report Date: {sar.get('report_date')}</p>
    </div>
    <div class="section">
        <h2>Subject Information</h2>
        <div class="field">
            <span class="label">Name:</span> {sar.get('subject', {}).get('name')}
        </div>
        <div class="field">
            <span class="label">Type:</span> {sar.get('subject', {}).get('type')}
        </div>
    </div>
    <div class="section">
        <h2>Suspicious Activity Summary</h2>
        <div class="field">
            <span class="label">Total Amount:</span> ${sar.get('suspicious_activity', {}).get('total_amount', 0):,.2f}
        </div>
        <div class="field">
            <span class="label">Transaction Count:</span> {sar.get('suspicious_activity', {}).get('transaction_count', 0)}
        </div>
    </div>
</body>
</html>
"""
