"""Fraud alert schema definitions"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class FraudAlertSchema(BaseModel):
    alert_id: str
    entity_id: str
    alert_type: str
    severity: str
    risk_score: float
    description: str
    created_at: datetime
    status: str = "open"
    evidence: Optional[list] = None
