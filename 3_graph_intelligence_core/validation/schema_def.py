"""ShadowGraph canonical schema — 7 vertex types, 19 edge types (live production schema)."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class VertexType:
    name: str
    primary_id: str
    attributes: list[dict]
    description: str = ""

    def gsql_create(self) -> str:
        attrs = ", ".join(
            f"{a['name']} {a['type']}"
            for a in self.attributes
        )
        return f"CREATE VERTEX {self.name} (PRIMARY_ID {self.primary_id} {self.attributes[0]['type']}, {attrs})"


@dataclass
class EdgeType:
    name: str
    from_types: list[str]
    to_types: list[str]
    attributes: list[dict]
    description: str = ""
    is_directed: bool = True

    def gsql_create(self) -> str:
        attrs = ""
        if self.attributes:
            attr_str = ", ".join(f"{a['name']} {a['type']}" for a in self.attributes)
            attrs = f" WITH SPECIFIC ATTRIBUTES ({attr_str})"
        from_t = "|".join(self.from_types)
        to_t = "|".join(self.to_types)
        return f"CREATE DIRECTED EDGE {self.name} (FROM {from_t}, TO {to_t}){attrs}"


# ── Vertices ──────────────────────────────────────────────────────────────────

VERTEX_TYPES: list[VertexType] = [
    VertexType(
        name="Person",
        primary_id="v_id STRING",
        attributes=[
            {"name": "name",           "type": "STRING"},
            {"name": "dob",            "type": "DATETIME"},
            {"name": "nationality",    "type": "STRING"},
            {"name": "email",          "type": "STRING"},
            {"name": "phone",          "type": "STRING"},
            {"name": "risk_score",     "type": "INT"},
            {"name": "pep_flag",       "type": "BOOL"},
            {"name": "sanctions_flag", "type": "BOOL"},
            {"name": "aliases",        "type": "LIST<STRING>"},
            {"name": "occupation",     "type": "STRING"},
            {"name": "source_country", "type": "STRING"},
        ],
        description="Natural person (individual)",
    ),
    VertexType(
        name="Company",
        primary_id="v_id STRING",
        attributes=[
            {"name": "name",                 "type": "STRING"},
            {"name": "registration_country", "type": "STRING"},
            {"name": "incorporation_date",   "type": "DATETIME"},
            {"name": "industry",             "type": "STRING"},
            {"name": "risk_score",           "type": "INT"},
            {"name": "offshore_flag",        "type": "BOOL"},
            {"name": "shell_company_flag",   "type": "BOOL"},
            {"name": "aliases",              "type": "LIST<STRING>"},
            {"name": "tax_id",               "type": "STRING"},
            {"name": "company_status",       "type": "STRING"},
        ],
        description="Legal entity / company",
    ),
    VertexType(
        name="Account",
        primary_id="v_id STRING",
        attributes=[
            {"name": "bank_name",      "type": "STRING"},
            {"name": "currency",       "type": "STRING"},
            {"name": "balance",        "type": "DOUBLE"},
            {"name": "account_type",   "type": "STRING"},
            {"name": "account_status", "type": "STRING"},
            {"name": "risk_score",     "type": "INT"},
            {"name": "iban",           "type": "STRING"},
            {"name": "swift_code",     "type": "STRING"},
        ],
        description="Financial account",
    ),
    VertexType(
        name="Address",
        primary_id="v_id STRING",
        attributes=[
            {"name": "full_address",  "type": "STRING"},
            {"name": "city",          "type": "STRING"},
            {"name": "country",       "type": "STRING"},
            {"name": "postal_code",   "type": "STRING"},
            {"name": "latitude",      "type": "DOUBLE"},
            {"name": "longitude",     "type": "DOUBLE"},
            {"name": "address_type",  "type": "STRING"},
            {"name": "risk_level",    "type": "STRING"},
        ],
        description="Physical address",
    ),
    VertexType(
        name="Device",
        primary_id="v_id STRING",
        attributes=[
            {"name": "ip_address",          "type": "STRING"},
            {"name": "device_type",         "type": "STRING"},
            {"name": "geo_location",        "type": "STRING"},
            {"name": "operating_system",    "type": "STRING"},
            {"name": "browser_fingerprint", "type": "STRING"},
            {"name": "risk_score",          "type": "INT"},
            {"name": "first_seen",          "type": "DATETIME"},
            {"name": "last_seen",           "type": "DATETIME"},
        ],
        description="Computing device",
    ),
    VertexType(
        name="Transaction",
        primary_id="v_id STRING",
        attributes=[
            {"name": "amount",           "type": "DOUBLE"},
            {"name": "currency",         "type": "STRING"},
            {"name": "transaction_type", "type": "STRING"},
            {"name": "timestamp",        "type": "DATETIME"},
            {"name": "risk_score",       "type": "INT"},
            {"name": "suspicious_flag",  "type": "BOOL"},
            {"name": "description",      "type": "STRING"},
            {"name": "channel",          "type": "STRING"},
        ],
        description="Financial transaction",
    ),
    VertexType(
        name="FraudRing",
        primary_id="v_id STRING",
        attributes=[
            {"name": "name",        "type": "STRING"},
            {"name": "ring_type",   "type": "STRING"},
            {"name": "severity",    "type": "STRING"},
            {"name": "description", "type": "STRING"},
        ],
        description="Fraud ring group — hub vertex for all ring membership edges",
    ),
]

# ── Edges — Infrastructure (13) ───────────────────────────────────────────────

_RING_MEMBERSHIP_ATTRS = [
    {"name": "role",             "type": "STRING"},
    {"name": "confidence_score", "type": "DOUBLE"},
    {"name": "discovered_at",    "type": "DATETIME"},
]

_RING_CONNECTION_ATTRS = [
    {"name": "relationship_kind", "type": "STRING"},
    {"name": "confidence_score",  "type": "DOUBLE"},
    {"name": "discovered_at",     "type": "DATETIME"},
]

EDGE_TYPES: list[EdgeType] = [
    # ── Infrastructure ────────────────────────────────────────────────────────
    EdgeType(
        name="OWNS",
        from_types=["Person", "Company"],
        to_types=["Company"],
        attributes=[
            {"name": "ownership_percent",  "type": "DOUBLE"},
            {"name": "beneficial_owner",   "type": "BOOL"},
            {"name": "ownership_type",     "type": "STRING"},
            {"name": "start_date",         "type": "DATETIME"},
            {"name": "end_date",           "type": "DATETIME"},
        ],
        description="Ownership stake in company",
    ),
    EdgeType(
        name="HAS_ACCOUNT",
        from_types=["Person", "Company"],
        to_types=["Account"],
        attributes=[
            {"name": "role",       "type": "STRING"},
            {"name": "created_at", "type": "DATETIME"},
        ],
        description="Entity holds or controls a financial account",
    ),
    EdgeType(
        name="TRANSFERRED_TO",
        from_types=["Account"],
        to_types=["Account"],
        attributes=[
            {"name": "amount",           "type": "DOUBLE"},
            {"name": "currency",         "type": "STRING"},
            {"name": "timestamp",        "type": "DATETIME"},
            {"name": "transaction_type", "type": "STRING"},
            {"name": "risk_score",       "type": "INT"},
            {"name": "transaction_id",   "type": "STRING"},
            {"name": "suspicious_flag",  "type": "BOOL"},
        ],
        description="Direct account-to-account fund transfer",
    ),
    EdgeType(
        name="LOCATED_AT",
        from_types=["Person", "Company", "Account"],
        to_types=["Address"],
        attributes=[
            {"name": "since",        "type": "DATETIME"},
            {"name": "address_role", "type": "STRING"},
        ],
        description="Entity physically located at an address",
    ),
    EdgeType(
        name="ASSOCIATED_WITH",
        from_types=["Person", "Company"],
        to_types=["Person", "Company"],
        attributes=[
            {"name": "relationship_type", "type": "STRING"},
            {"name": "confidence_score",  "type": "DOUBLE"},
            {"name": "discovered_at",     "type": "DATETIME"},
        ],
        description="Generic association between entities",
    ),
    EdgeType(
        name="USES_DEVICE",
        from_types=["Person"],
        to_types=["Device"],
        attributes=[
            {"name": "first_seen", "type": "DATETIME"},
            {"name": "last_seen",  "type": "DATETIME"},
        ],
        description="Person uses a device",
    ),
    EdgeType(
        name="ACCESSED_FROM",
        from_types=["Account"],
        to_types=["Device"],
        attributes=[
            {"name": "timestamp",    "type": "DATETIME"},
            {"name": "geo_location", "type": "STRING"},
            {"name": "session_id",   "type": "STRING"},
        ],
        description="Account accessed from a specific device",
    ),
    EdgeType(
        name="SENT_TRANSACTION",
        from_types=["Account"],
        to_types=["Transaction"],
        attributes=[
            {"name": "timestamp", "type": "DATETIME"},
        ],
        description="Account initiated / sent a transaction",
    ),
    EdgeType(
        name="RECEIVED_TRANSACTION",
        from_types=["Transaction"],
        to_types=["Account"],
        attributes=[
            {"name": "timestamp", "type": "DATETIME"},
        ],
        description="Transaction received by an account",
    ),
    EdgeType(
        name="REGISTERED_AT",
        from_types=["Company"],
        to_types=["Address"],
        attributes=[
            {"name": "registered_since", "type": "DATETIME"},
        ],
        description="Company formally registered at an address",
    ),
    EdgeType(
        name="BENEFITS_FROM",
        from_types=["Person"],
        to_types=["Company"],
        attributes=[
            {"name": "relationship_strength", "type": "DOUBLE"},
            {"name": "discovered_at",         "type": "DATETIME"},
        ],
        description="Entity is the beneficial recipient of a company's activity",
    ),
    EdgeType(
        name="SHARES_DEVICE_WITH",
        from_types=["Person"],
        to_types=["Person"],
        attributes=[
            {"name": "shared_device_count", "type": "INT"},
            {"name": "risk_score",          "type": "INT"},
        ],
        description="Two persons share access to the same device",
    ),
    EdgeType(
        name="SHARES_ADDRESS_WITH",
        from_types=["Person", "Company"],
        to_types=["Person", "Company"],
        attributes=[
            {"name": "shared_address_count", "type": "INT"},
            {"name": "risk_score",           "type": "INT"},
        ],
        description="Two entities share the same address",
    ),
    # ── Fraud ring membership — explicit per-type (6) ─────────────────────────
    EdgeType(
        name="PERSON_MEMBER_OF_RING",
        from_types=["Person"],
        to_types=["FraudRing"],
        attributes=_RING_MEMBERSHIP_ATTRS,
        description="Person is a member of a fraud ring",
    ),
    EdgeType(
        name="COMPANY_MEMBER_OF_RING",
        from_types=["Company"],
        to_types=["FraudRing"],
        attributes=_RING_MEMBERSHIP_ATTRS,
        description="Company is a member of a fraud ring",
    ),
    EdgeType(
        name="ACCOUNT_MEMBER_OF_RING",
        from_types=["Account"],
        to_types=["FraudRing"],
        attributes=_RING_MEMBERSHIP_ATTRS,
        description="Account is a member of a fraud ring",
    ),
    EdgeType(
        name="TRANSACTION_MEMBER_OF_RING",
        from_types=["Transaction"],
        to_types=["FraudRing"],
        attributes=_RING_MEMBERSHIP_ATTRS,
        description="Transaction is linked to a fraud ring",
    ),
    EdgeType(
        name="DEVICE_CONNECTED_TO_RING",
        from_types=["Device"],
        to_types=["FraudRing"],
        attributes=_RING_CONNECTION_ATTRS,
        description="Device used in fraud ring activity",
    ),
    EdgeType(
        name="ADDRESS_CONNECTED_TO_RING",
        from_types=["Address"],
        to_types=["FraudRing"],
        attributes=_RING_CONNECTION_ATTRS,
        description="Address associated with a fraud ring",
    ),
]

# ── Convenience lookups ───────────────────────────────────────────────────────

VERTEX_NAMES: list[str] = [v.name for v in VERTEX_TYPES]
EDGE_NAMES: list[str] = [e.name for e in EDGE_TYPES]

# All ring-to-FraudRing edge names (for traversal filtering)
RING_MEMBERSHIP_EDGES: frozenset[str] = frozenset({
    "PERSON_MEMBER_OF_RING",
    "COMPANY_MEMBER_OF_RING",
    "ACCOUNT_MEMBER_OF_RING",
    "TRANSACTION_MEMBER_OF_RING",
    "DEVICE_CONNECTED_TO_RING",
    "ADDRESS_CONNECTED_TO_RING",
})

# High-signal edges for evidence prioritization
PRIORITY_EDGES: frozenset[str] = frozenset({
    "OWNS",
    "SENT_TRANSACTION",
    "RECEIVED_TRANSACTION",
    "TRANSFERRED_TO",
    "REGISTERED_AT",
    "BENEFITS_FROM",
    "PERSON_MEMBER_OF_RING",
    "COMPANY_MEMBER_OF_RING",
    "ACCOUNT_MEMBER_OF_RING",
    "TRANSACTION_MEMBER_OF_RING",
})


def get_vertex(name: str) -> Optional[VertexType]:
    for v in VERTEX_TYPES:
        if v.name == name:
            return v
    return None


def get_edge(name: str) -> Optional[EdgeType]:
    for e in EDGE_TYPES:
        if e.name == name:
            return e
    return None
