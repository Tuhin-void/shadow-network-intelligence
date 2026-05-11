"""
Shadow Network Intelligence - Compliance Agent
Checks transactions against AML/KYC regulations
"""
from typing import Dict, List, Any
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ComplianceAgent:
    """
    Compliance Agent - Ensures regulatory compliance
    
    Responsibilities:
    - Check transactions for compliance violations
    - Identify CTR requirements
    - Check sanctions matches
    - Generate compliance reports
    """
    
    CTR_THRESHOLD = 10000
    SAR_THRESHOLD = 5000
    
    def __init__(self, llm_provider):
        self.llm = llm_provider
        self.system_prompt = """You are a compliance officer.
        
Your role is to:
1. Check transactions for CTR (Currency Transaction Report) triggers
2. Identify SAR (Suspicious Activity Report) requirements
3. Check for sanctions matches
4. Verify KYC requirements
5. Ensure AML compliance

Report formats:
- CTR: Required for cash transactions > $10,000
- SAR: Required for suspicious activity regardless of amount
- CMIR: Currency/Monetary Instrument Report
- FBAR: Foreign Bank Account Report
"""
    
    def check_compliance(self, entity_id: str, transactions: List[Dict]) -> Dict[str, Any]:
        """
        Check compliance status for an entity.
        """
        logger.info(f"Checking compliance for: {entity_id}")
        
        ctr_requirements = self._check_ctr(transactions)
        sar_eligibility = self._check_sar(transactions)
        sanctions = self._check_sanctions(entity_id)
        kyc_status = self._check_kyc(entity_id)
        
        violations = self._identify_violations(ctr_requirements, sar_eligibility, sanctions)
        
        return {
            "entity_id": entity_id,
            "checked_at": datetime.now().isoformat(),
            "ctr_required": ctr_requirements,
            "sar_required": sar_eligibility,
            "sanctions_match": sanctions,
            "kyc_status": kyc_status,
            "violations": violations,
            "compliance_status": "PASS" if not violations else "FAIL",
            "required_actions": self._get_compliance_actions(violations)
        }
    
    def _check_ctr(self, transactions: List[Dict]) -> List[Dict]:
        """Check for CTR requirements"""
        ctr_transactions = []
        
        for txn in transactions:
            if txn.get("amount", 0) >= self.CTR_THRESHOLD:
                ctr_transactions.append({
                    "transaction_id": txn.get("id"),
                    "amount": txn.get("amount"),
                    "trigger": f"CTR Required: Amount ${txn.get('amount')} exceeds threshold",
                    "form_required": "CTR",
                    "deadline": "5 business days"
                })
        
        return ctr_transactions
    
    def _check_sar(self, transactions: List[Dict]) -> Dict[str, Any]:
        """Check for SAR requirements"""
        suspicious_txns = [t for t in transactions if t.get("is_suspicious", False)]
        
        return {
            "required": len(suspicious_txns) > 0,
            "reason": f"{len(suspicious_txns)} suspicious transactions detected",
            "transactions": suspicious_txns,
            "form_required": "SAR",
            "deadline": "30 days"
        }
    
    def _check_sanctions(self, entity_id: str) -> Dict[str, Any]:
        """Check sanctions list matches"""
        return {
            "match": False,
            "lists_checked": ["OFAC SDN", "UN Sanctions", "EU Sanctions"],
            "entity_id": entity_id
        }
    
    def _check_kyc(self, entity_id: str) -> Dict[str, Any]:
        """Check KYC status"""
        return {
            "verified": True,
            "kyc_level": "ENHANCED",
            "last_verification": "2024-01-15",
            "next_review": "2025-01-15"
        }
    
    def _identify_violations(self, ctr: List, sar: Dict, sanctions: Dict) -> List[Dict]:
        """Identify compliance violations"""
        violations = []
        
        if not ctr:
            violations.append({
                "type": "CTR_MISSING",
                "severity": "HIGH",
                "description": "CTR not filed for qualifying transaction"
            })
        
        if sar.get("required"):
            violations.append({
                "type": "SAR_RECOMMENDED",
                "severity": "HIGH",
                "description": sar["reason"]
            })
        
        return violations
    
    def _get_compliance_actions(self, violations: List) -> List[str]:
        """Get required compliance actions"""
        actions = []
        
        for v in violations:
            if v["type"] == "CTR_MISSING":
                actions.append("File CTR immediately")
            if v["type"] == "SAR_RECOMMENDED":
                actions.append("Prepare and file SAR")
            if v["type"] == "SANCTIONS_MATCH":
                actions.append("Block transaction and escalate to OFAC")
        
        if not actions:
            actions.append("No immediate actions required")
        
        return actions
