"""
Shadow Network Intelligence - WebSocket Event Publisher
Publishes real-time events via WebSocket
"""
import asyncio
import json
from typing import Dict, List, Set, Callable, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class WebSocketPublisher:
    """
    WebSocket publisher for real-time event streaming.
    
    Manages WebSocket connections and broadcasts events
    to all connected clients.
    """
    
    def __init__(self):
        self.connections: Set = set()
        self.event_history: List[Dict] = []
        self.max_history = 1000
    
    def add_connection(self, websocket):
        """Add a new WebSocket connection"""
        self.connections.add(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.connections)}")
    
    def remove_connection(self, websocket):
        """Remove a WebSocket connection"""
        self.connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.connections)}")
    
    async def broadcast(self, event: Dict):
        """
        Broadcast event to all connected clients.
        
        Args:
            event: Event data to broadcast
        """
        if not self.connections:
            return
        
        event["timestamp"] = datetime.now().isoformat()
        
        self._add_to_history(event)
        
        disconnected = set()
        
        for websocket in self.connections:
            try:
                await websocket.send_json(event)
            except Exception as e:
                logger.error(f"Error sending to WebSocket: {e}")
                disconnected.add(websocket)
        
        for ws in disconnected:
            self.remove_connection(ws)
    
    async def send_to(self, websocket, event: Dict):
        """Send event to specific WebSocket"""
        try:
            await websocket.send_json(event)
        except Exception as e:
            logger.error(f"Error sending to WebSocket: {e}")
            self.remove_connection(websocket)
    
    def _add_to_history(self, event: Dict):
        """Add event to history buffer"""
        self.event_history.append(event)
        
        if len(self.event_history) > self.max_history:
            self.event_history = self.event_history[-self.max_history:]
    
    def get_history(self, limit: int = 100) -> List[Dict]:
        """Get recent event history"""
        return self.event_history[-limit:]
    
    def get_stats(self) -> Dict:
        """Get publisher statistics"""
        return {
            "active_connections": len(self.connections),
            "events_broadcast": len(self.event_history)
        }


class EventPublisher:
    """
    High-level event publisher for fraud detection events.
    """
    
    def __init__(self, websocket_publisher: WebSocketPublisher):
        self.publisher = websocket_publisher
    
    async def publish_alert(self, alert: Dict):
        """Publish a fraud alert event"""
        event = {
            "type": "alert",
            "data": alert
        }
        await self.publisher.broadcast(event)
    
    async def publish_transaction(self, transaction: Dict):
        """Publish a transaction event"""
        event = {
            "type": "transaction",
            "data": transaction
        }
        await self.publisher.broadcast(event)
    
    async def publish_risk_update(self, entity_id: str, risk_score: float):
        """Publish a risk score update"""
        event = {
            "type": "risk_update",
            "data": {
                "entity_id": entity_id,
                "risk_score": risk_score
            }
        }
        await self.publisher.broadcast(event)
    
    async def publish_investigation_update(self, investigation_id: str, status: str):
        """Publish investigation status update"""
        event = {
            "type": "investigation_update",
            "data": {
                "investigation_id": investigation_id,
                "status": status
            }
        }
        await self.publisher.broadcast(event)


# Global publisher instance
_global_publisher: Optional[WebSocketPublisher] = None

def get_publisher() -> WebSocketPublisher:
    """Get or create global publisher instance"""
    global _global_publisher
    if _global_publisher is None:
        _global_publisher = WebSocketPublisher()
    return _global_publisher
