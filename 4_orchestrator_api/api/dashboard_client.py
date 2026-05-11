"""
Shadow Network Intelligence - Dashboard API Client
Connects React dashboard to backend API
"""
from typing import Dict, List, Any, Optional
import logging
import requests

logger = logging.getLogger(__name__)

class DashboardAPIClient:
    """
    Client for connecting React dashboard to backend API.
    """
    
    def __init__(self, base_url: str = "http://localhost:8000/api/v1"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json"
        })
    
    def get_health(self) -> Dict[str, Any]:
        """Get system health status"""
        try:
            response = self.session.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_alerts(self, status: str = "open", limit: int = 50) -> Dict[str, Any]:
        """Get fraud alerts"""
        try:
            response = self.session.get(
                f"{self.base_url}/alerts",
                params={"status": status, "limit": limit}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get alerts: {e}")
            return {"alerts": [], "error": str(e)}
    
    def investigate(self, query: str, entity_id: str = None) -> Dict[str, Any]:
        """Run investigation"""
        try:
            response = self.session.post(
                f"{self.base_url}/investigate",
                json={"query": query, "entity_id": entity_id}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Investigation failed: {e}")
            return {"error": str(e)}
    
    def get_investigation(self, investigation_id: str) -> Dict[str, Any]:
        """Get investigation by ID"""
        try:
            response = self.session.get(
                f"{self.base_url}/investigate/{investigation_id}"
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get investigation: {e}")
            return {"error": str(e)}
    
    def generate_sar(self, investigation_id: str, format: str = "json") -> Dict[str, Any]:
        """Generate SAR report"""
        try:
            response = self.session.post(
                f"{self.base_url}/reports/sar",
                json={"investigation_id": investigation_id, "format": format}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"SAR generation failed: {e}")
            return {"error": str(e)}
    
    def search(self, query: str, filters: Dict = None) -> Dict[str, Any]:
        """Search transactions"""
        try:
            response = self.session.post(
                f"{self.base_url}/search",
                json={"query": query, "filters": filters or {}}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {"error": str(e)}
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get dashboard metrics"""
        try:
            response = self.session.get(f"{self.base_url}/metrics")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return {"error": str(e)}
    
    def run_benchmark(self, query: str) -> Dict[str, Any]:
        """Run benchmark comparison"""
        try:
            response = self.session.post(
                f"{self.base_url}/benchmark",
                json={"query": query}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Benchmark failed: {e}")
            return {"error": str(e)}