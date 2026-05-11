"""
Search API - Knowledge graph search
POST /search
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class SearchRequest(BaseModel):
    query: str
    entity_type: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    limit: int = 20

class EntityResult(BaseModel):
    id: str
    type: str
    name: str
    properties: Dict[str, Any]
    score: float

@router.post("/search", response_model=List[EntityResult])
async def search_graph(request: SearchRequest):
    """
    Search the knowledge graph for entities matching the query.
    """
    logger.info(f"Search request: {request.query}")
    
    results = [
        EntityResult(
            id="PERSON_001",
            type="Person",
            name="John Doe",
            properties={"occupation": "Engineer", "city": "New York"},
            score=0.95
        ),
        EntityResult(
            id="COMPANY_001",
            type="Company",
            name="Global Holdings LLC",
            properties={"industry": "Financial Services", "is_offshore": True},
            score=0.88
        ),
        EntityResult(
            id="TXN_001",
            type="Transaction",
            name="Wire Transfer $50,000",
            properties={"amount": 50000, "type": "WIRE", "date": "2024-01-15"},
            score=0.82
        )
    ]
    
    return results[:request.limit]

@router.get("/search/entity/{entity_id}")
async def get_entity(entity_id: str):
    """Get entity details by ID"""
    return {
        "id": entity_id,
        "type": "Person",
        "name": "John Doe",
        "properties": {
            "ssn": "***-**-1234",
            "address": "123 Main St",
            "risk_score": 0.45
        },
        "relationships": [
            {"type": "OWNS", "target_id": "COMPANY_001"},
            {"type": "HAS_ACCOUNT", "target_id": "ACCOUNT_001"}
        ]
    }
