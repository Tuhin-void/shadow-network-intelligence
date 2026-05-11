"""
Shadow Network Intelligence - Investigation Orchestrator
Orchestrates multi-agent investigations
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

from agents.detective import DetectiveAgent
from agents.transaction_analyst import TransactionAnalystAgent
from agents.graph_search import GraphSearchAgent

logger = logging.getLogger(__name__)

@dataclass
class InvestigationRequest:
    query: str
    entity_id: Optional[str] = None
    depth: str = "standard"
    approaches: List[str] = None

@dataclass
class InvestigationResult:
    investigation_id: str
    status: str
    findings: Dict[str, Any]
    agent_results: Dict[str, Any]
    execution_time_ms: float
    timestamp: datetime

class InvestigationOrchestrator:
    """
    Orchestrates multi-agent investigations.
    Coordinates detective, analyst, and search agents.
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.detective = DetectiveAgent(config)
        self.transaction_analyst = TransactionAnalystAgent(config)
        self.graph_search = GraphSearchAgent(config)
    
    async def investigate(
        self,
        request: InvestigationRequest
    ) -> InvestigationResult:
        """
        Run a complete investigation using multiple agents.
        """
        import time
        start = time.time()
        
        investigation_id = f"INV_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        logger.info(f"Starting investigation {investigation_id}")
        
        agent_results = await self._run_agents(request)
        
        findings = self._synthesize_findings(agent_results)
        
        execution_time_ms = (time.time() - start) * 1000
        
        return InvestigationResult(
            investigation_id=investigation_id,
            status="completed",
            findings=findings,
            agent_results=agent_results,
            execution_time_ms=execution_time_ms,
            timestamp=datetime.now()
        )
    
    async def _run_agents(
        self,
        request: InvestigationRequest
    ) -> Dict[str, Any]:
        """Run all applicable agents"""
        results = {}
        
        if request.entity_id:
            results["detective"] = await self.detective.investigate(
                request.entity_id,
                request.query
            )
            
            results["transaction_analysis"] = self.transaction_analyst.analyze_transactions(
                request.entity_id,
                []
            )
            
            results["graph_search"] = self.graph_search.search_entity(
                request.entity_id,
                depth=2
            )
        
        return results
    
    def _synthesize_findings(self, agent_results: Dict) -> Dict[str, Any]:
        """Combine findings from all agents"""
        risk_scores = []
        
        if "detective" in agent_results:
            risk_scores.append(agent_results["detective"].get("risk_score", 0))
        
        if "transaction_analysis" in agent_results:
            risk_scores.append(
                agent_results["transaction_analysis"].get("patterns", {}).get("score", 0)
            )
        
        avg_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0
        
        return {
            "risk_score": avg_risk,
            "risk_level": self._get_risk_level(avg_risk),
            "patterns_detected": self._collect_patterns(agent_results),
            "evidence": self._collect_evidence(agent_results)
        }
    
    def _get_risk_level(self, score: float) -> str:
        """Convert risk score to level"""
        if score >= 0.8:
            return "CRITICAL"
        elif score >= 0.6:
            return "HIGH"
        elif score >= 0.4:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _collect_patterns(self, agent_results: Dict) -> List[str]:
        """Collect detected patterns"""
        patterns = set()
        
        if "detective" in agent_results:
            patterns.update(
                agent_results["detective"].get("patterns_detected", [])
            )
        
        if "transaction_analysis" in agent_results:
            patterns.update(
                k for k, v in agent_results["transaction_analysis"]
                .get("patterns", {}).items() if v
            )
        
        return list(patterns)
    
    def _collect_evidence(self, agent_results: Dict) -> List[Dict]:
        """Collect all evidence"""
        evidence = []
        
        if "graph_search" in agent_results:
            for neighbor in agent_results["graph_search"].get("neighbors", []):
                evidence.append({
                    "type": "entity",
                    "id": neighbor.get("id"),
                    "source": "graph_search"
                })
        
        return evidence