"""
Device Entity - Device schema for device tracking
"""
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List, Dict, Any


@dataclass
class DeviceEntity:
    """Device entity for AML intelligence generation"""

    id: str
    device_type: str = "desktop"
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    user_agent: Optional[str] = None

    # Ownership
    owner_id: Optional[str] = None
    owner_type: str = "Person"

    # Location
    location_country: Optional[str] = None
    location_city: Optional[str] = None

    # Activity
    first_seen: date = field(default_factory=date.today)
    last_seen: Optional[date] = None
    login_count: int = 0

    # Risk
    risk_score: float = 0.0
    is_burner: bool = False
    is_vpn: bool = False

    # Shared users
    shared_users: List[str] = field(default_factory=list)

    # Transactions
    transactions: List[str] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def entity_type(self) -> str:
        return "Device"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "entity_type": "Device",
            "device_type": self.device_type,
            "ip_address": self.ip_address,
            "owner_id": self.owner_id,
            "owner_type": self.owner_type,
            "location_country": self.location_country,
            "first_seen": self.first_seen.isoformat(),
            "risk_score": self.risk_score,
            "is_burner": self.is_burner,
            "is_vpn": self.is_vpn,
            "created_at": self.created_at.isoformat(),
        }

    def to_tigergraph(self) -> dict:
        return {
            "device_id": self.id,
            "device_type": self.device_type,
            "ip_address": self.ip_address or "",
            "owner_id": self.owner_id,
            "risk_score": self.risk_score,
            "is_burner": int(self.is_burner),
        }