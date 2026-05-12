"""
Device Schema - Device entities for infrastructure tracking
"""
import random
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List
from enum import Enum


class DeviceType(Enum):
    COMPUTER = "computer"
    MOBILE = "mobile"
    TABLET = "tablet"
    SERVER = "server"
    VPN = "vpn"
    BURNER = "burner"


class OSType(Enum):
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    ANDROID = "ios"
    IOS = "ios"


class DeviceStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    COMPROMISED = "compromised"


@dataclass
class DeviceSchema:
    """Device entity schema for AML data generation"""

    id: str
    device_type: DeviceType
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    hostname: Optional[str] = None
    os_type: Optional[OSType] = None
    browser: Optional[str] = None
    user_agent: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    is_vpn: bool = False
    is_proxy: bool = False
    is_tor: bool = False
    risk_score: float = 0.0
    status: DeviceStatus = DeviceStatus.ACTIVE
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    fingerprint: Optional[str] = None
    associated_entities: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "device_type": self.device_type.value,
            "ip_address": self.ip_address,
            "mac_address": self.mac_address,
            "hostname": self.hostname,
            "os_type": self.os_type.value if self.os_type else None,
            "browser": self.browser,
            "country": self.country,
            "is_vpn": self.is_vpn,
            "is_proxy": self.is_proxy,
            "is_tor": self.is_tor,
            "risk_score": self.risk_score,
            "status": self.status.value,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "fingerprint": self.fingerprint,
            "associated_entities": self.associated_entities,
        }

    def to_tigergraph_row(self) -> dict:
        return {
            "device_id": self.id,
            "device_type": self.device_type.value,
            "ip_address": self.ip_address or "",
            "os_type": self.os_type.value if self.os_type else "",
            "is_vpn": int(self.is_vpn),
            "is_proxy": int(self.is_proxy),
            "risk_score": self.risk_score,
            "status": self.status.value,
        }

    def to_chromadb_doc(self) -> str:
        doc = f"Device: {self.id}. Type: {self.device_type.value}. "
        if self.ip_address:
            doc += f"IP: {self.ip_address}. "
        if self.is_vpn:
            doc += "VPN detected. "
        if self.is_tor:
            doc += "Tor node. "
        if self.risk_score > 0.6:
            doc += f"High risk: {self.risk_score}. "
        return doc


class DeviceGenerator:
    """Generator for device entities"""

    IP_RANGES = [
        "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
        "185.220.0.0/16",  # Tor exit nodes
        "103.75.190.0/24",  # Proxy ranges
    ]

    HOSTNAME_PREFIXES = [
        "workstation", "laptop", "server", "desktop", "mobile",
        "vpn-gateway", "firewall", "proxy", "node"
    ]

    BROWSERS = [
        "Chrome 120", "Firefox 121", "Safari 17", "Edge 120",
        "Chrome 119", "Firefox 120", "Opera 105"
    ]

    COUNTRIES = [
        "US", "GB", "DE", "FR", "NL", "RU", "CN", "UA", "BR", "IN",
        "PA", "KY", "VG", "BS", "CY"
    ]

    CITIES = [
        "New York", "London", "Frankfurt", "Paris", "Amsterdam",
        "Moscow", "Beijing", "Kyiv", "Panama City", "George Town"
    ]

    def __init__(self, seed: Optional[int] = None):
        self._random = random.Random(seed)
        self._counter = 0

    def generate(
        self,
        seed_override: Optional[int] = None,
        force_suspicious: bool = False,
    ) -> DeviceSchema:
        """Generate a single device entity"""
        r = random.Random(seed_override) if seed_override else self._random
        self._counter += 1

        device_types = list(DeviceType)
        if force_suspicious:
            device_types = [DeviceType.VPN, DeviceType.BURNER, DeviceType.SERVER]

        device_type = r.choice(device_types)
        os_types = list(OSType)
        os_type = r.choice(os_types)

        ip_parts = [str(r.randint(1, 255)) for _ in range(4)]
        ip_address = ".".join(ip_parts)

        is_vpn = r.random() < 0.08 or (force_suspicious and r.random() < 0.3)
        is_proxy = r.random() < 0.05 or (force_suspicious and r.random() < 0.2)
        is_tor = r.random() < 0.02 or (force_suspicious and r.random() < 0.15)

        risk_score = round(r.uniform(0, 1), 4)
        if is_vpn or is_proxy or is_tor:
            risk_score = min(1.0, risk_score + 0.4)

        from datetime import timedelta
        days_ago = r.randint(0, 730)
        first_seen = datetime.now() - timedelta(days=days_ago)
        last_seen = first_seen + timedelta(days=r.randint(0, 30))

        hostname = f"{r.choice(self.HOSTNAME_PREFIXES)}-{r.randint(1000, 9999)}"

        return DeviceSchema(
            id=f"D-{self._counter:06d}",
            device_type=device_type,
            ip_address=ip_address,
            mac_address=f"{r.randint(0, 255):02x}:{r.randint(0, 255):02x}:{r.randint(0, 255):02x}:{r.randint(0, 255):02x}:{r.randint(0, 255):02x}:{r.randint(0, 255):02x}",
            hostname=hostname,
            os_type=os_type,
            browser=r.choice(self.BROWSERS),
            country=r.choice(self.COUNTRIES),
            city=r.choice(self.CITIES),
            is_vpn=is_vpn,
            is_proxy=is_proxy,
            is_tor=is_tor,
            risk_score=risk_score,
            status=DeviceStatus.ACTIVE,
            first_seen=first_seen,
            last_seen=last_seen,
            fingerprint=f"fp_{r.randint(1000000, 9999999)}",
        )