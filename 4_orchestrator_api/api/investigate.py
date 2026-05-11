"""
Investigate API - Run fraud investigations
POST /investigate
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class InvestigationRequest(BaseModel):
    query: str
    entity_id: Optional[str] = None
    transaction_ids: Optional[List[str]] = None
    depth: int = 2
    include_reasoning: bool = True

class InvestigationResponse(BaseModel):
    investigation_id: str
    query: str
    answer: str
    confidence: float
    evidence: List[Dict[str, Any]]
    reasoning: Optional[str] = None
    risk_score: float
    recommended_actions: List[str]

@router.post("/investigate", response_model=InvestigationResponse)
async def investigate(request: InvestigationRequest):
    """
    Run a fraud investigation query.
    
    Analyzes the query and returns:
    - Answer to the question
    - Supporting evidence
    - Risk assessment
    - Recommended actions
    """
    logger.info(f"Investigation request: {request.query}")
    
    investigation_id = f"INV_{hash(request.query) % 100000:05d}"
    
    return InvestigationResponse(
        investigation_id=investigation_id,
        query=request.query,
        answer="Investigation complete. See evidence for details.",
        confidence=0.85,
        evidence=[
            {
                "type": "transaction",
                "id": "TXN_001",
                "amount": 50000,
                "risk_factors": ["large_transaction", "offshore_destination"]
            }
        ],
        reasoning="Chain of thought reasoning would appear here.",
        risk_score=0.72,
        recommended_actions=[
            "File SAR if risk_score > 0.8",
            "Enhanced due diligence",
            "Notify compliance team"
        ]
    )

@router.get("/investigate/{investigation_id}")
async def get_investigation(investigation_id: str):
    """Get a previous investigation by ID"""
    return {
        "investigation_id": investigation_id,
        "status": "complete",
        "result": {}
    }
