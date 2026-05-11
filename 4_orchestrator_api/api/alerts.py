"""
Alerts API - Real-time fraud alerts
GET /alerts
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class Alert(BaseModel):
    id: str
    type: str
    severity: str
    description: str
    entity_id: str
    entity_type: str
    created_at: str
    status: str = "OPEN"
    risk_score: float

@router.get("/alerts", response_model=List[Alert])
async def get_alerts(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 50
):
    """Get fraud alerts"""
    alerts = [
        Alert(
            id="ALT_001",
            type="RAPID_TRANSFER",
            severity="HIGH",
            description="5 transactions within 1 hour between same accounts",
            entity_id="ACCOUNT_PERSON_001",
            entity_type="BankAccount",
            created_at=datetime.now().isoformat(),
            risk_score=0.85
        ),
        Alert(
            id="ALT_002",
            type="SHELL_COMPANY",
            severity="CRITICAL",
            description="Circular ownership detected between 3 companies",
            entity_id="COMPANY_001",
            entity_type="Company",
            created_at=datetime.now().isoformat(),
            risk_score=0.92
        ),
        Alert(
            id="ALT_003",
            type="OFFSHORE_TRANSFER",
            severity="MEDIUM",
            description="Transfer to offshore jurisdiction",
            entity_id="TXN_005",
            entity_type="Transaction",
            created_at=datetime.now().isoformat(),
            risk_score=0.65
        )
    ]
    
    if status:
        alerts = [a for a in alerts if a.status == status]
    if severity:
        alerts = [a for a in alerts if a.severity == severity]
    
    return alerts[:limit]

@router.get("/alerts/{alert_id}")
async def get_alert(alert_id: str):
    """Get single alert by ID"""
    return Alert(
        id=alert_id,
        type="RAPID_TRANSFER",
        severity="HIGH",
        description="Alert details",
        entity_id="ACCOUNT_001",
        entity_type="BankAccount",
        created_at=datetime.now().isoformat(),
        risk_score=0.75
    )

@router.put("/alerts/{alert_id}/status")
async def update_alert_status(alert_id: str, status: str):
    """Update alert status"""
    return {"alert_id": alert_id, "status": status, "updated": True}
