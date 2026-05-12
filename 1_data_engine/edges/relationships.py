"""
Relationships - Relationship type definitions and weights
"""
from enum import Enum


class RelationshipType(Enum):
    OWNS = "OWNS"
    HAS_ACCOUNT = "HAS_ACCOUNT"
    TRANSFERRED_TO = "TRANSFERRED_TO"
    LOCATED_AT = "LOCATED_AT"
    ASSOCIATED_WITH = "ASSOCIATED_WITH"
    USES_DEVICE = "USES_DEVICE"
    ACCESSED_FROM = "ACCESSED_FROM"
    SENT_TRANSACTION = "SENT_TRANSACTION"
    RECEIVED_TRANSACTION = "RECEIVED_TRANSACTION"
    REGISTERED_AT = "REGISTERED_AT"
    BENEFITS_FROM = "BENEFITS_FROM"
    SHARES_DEVICE_WITH = "SHARES_DEVICE_WITH"
    SHARES_ADDRESS_WITH = "SHARES_ADDRESS_WITH"
    CONTROLS = "CONTROLS"
    DIRECTOR_OF = "DIRECTOR_OF"


RELATIONSHIP_TYPES = [
    "OWNS",
    "HAS_ACCOUNT",
    "TRANSFERRED_TO",
    "LOCATED_AT",
    "ASSOCIATED_WITH",
    "USES_DEVICE",
    "ACCESSED_FROM",
    "SENT_TRANSACTION",
    "RECEIVED_TRANSACTION",
    "REGISTERED_AT",
    "BENEFITS_FROM",
    "SHARES_DEVICE_WITH",
    "SHARES_ADDRESS_WITH",
    "CONTROLS",
    "DIRECTOR_OF",
]

RELATIONSHIP_WEIGHTS = {
    "OWNS": 1.0,
    "HAS_ACCOUNT": 0.7,
    "TRANSFERRED_TO": 0.8,
    "LOCATED_AT": 0.4,
    "ASSOCIATED_WITH": 0.5,
    "USES_DEVICE": 0.6,
    "ACCESSED_FROM": 0.5,
    "SENT_TRANSACTION": 0.9,
    "RECEIVED_TRANSACTION": 0.9,
    "REGISTERED_AT": 0.5,
    "BENEFITS_FROM": 0.8,
    "SHARES_DEVICE_WITH": 0.6,
    "SHARES_ADDRESS_WITH": 0.7,
    "CONTROLS": 0.9,
    "DIRECTOR_OF": 0.8,
}


SOURCE_TYPES = ["Person", "Company", "Account", "Address", "Device"]
TARGET_TYPES = ["Person", "Company", "Account", "Address", "Device"]


VALID_RELATIONSHIP_PAIRS = {
    "Person": ["Company", "Account", "Address", "Device"],
    "Company": ["Company", "Account", "Address"],
    "Account": ["Account", "Device"],
    "Address": [],
    "Device": [],
}