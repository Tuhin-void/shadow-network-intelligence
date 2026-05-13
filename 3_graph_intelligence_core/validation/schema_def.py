"""ShadowGraph schema definition — canonical 6 vertex types, 13 edge types."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class VertexType:
    name: str
    primary_id: str
    attributes: list[dict]
    description: str = ""

    def gsql_create(self) -> str:
        attrs = ", ".join(
            f"{a['name']} {a['type']}" + (f" DEFAULT {a.get('default', 'DEFAULT')}" if a.get('default') else "")
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
    is_optional: bool = True

    def gsql_create(self) -> str:
        attrs = ""
        if self.attributes:
            attr_str = ", ".join(f"{a['name']} {a['type']}" for a in self.attributes)
            attrs = f" WITH SPECIFIC ATTRIBUTES ({attr_str})"
        reverse = "REVERSE_EDGE" if not self.is_directed else ""
        from_t = ",".join(self.from_types)
        to_t = ",".join(self.to_types)
        return f"CREATE DIRECTED EDGE {self.name} (FROM {from_t}, TO {to_t}){attrs}"


VERTEX_TYPES = [
    VertexType(
        name="Person",
        primary_id="v_id STRING",
        attributes=[
            {"name": "v_id", "type": "STRING"},
            {"name": "name", "type": "STRING"},
            {"name": "email", "type": "STRING"},
            {"name": "phone", "type": "STRING"},
            {"name": "country", "type": "STRING"},
            {"name": "risk_score", "type": "DOUBLE"},
            {"name": "tags", "type": "LIST<STRING>"},
            {"name": "created_at", "type": "UINT"},
        ],
        description="Natural person (individual)",
    ),
    VertexType(
        name="Company",
        primary_id="v_id STRING",
        attributes=[
            {"name": "v_id", "type": "STRING"},
            {"name": "name", "type": "STRING"},
            {"name": "jurisdiction", "type": "STRING"},
            {"name": "industry", "type": "STRING"},
            {"name": "is_shell", "type": "BOOL"},
            {"name": "is_offshore", "type": "BOOL"},
            {"name": "risk_score", "type": "DOUBLE"},
            {"name": "tags", "type": "LIST<STRING>"},
            {"name": "incorporated_date", "type": "UINT"},
        ],
        description="Legal entity / company",
    ),
    VertexType(
        name="Account",
        primary_id="v_id STRING",
        attributes=[
            {"name": "v_id", "type": "STRING"},
            {"name": "account_number", "type": "STRING"},
            {"name": "bank_name", "type": "STRING"},
            {"name": "account_type", "type": "STRING"},
            {"name": "balance", "type": "DOUBLE"},
            {"name": "currency", "type": "STRING"},
            {"name": "risk_score", "type": "DOUBLE"},
            {"name": "is_offshore", "type": "BOOL"},
            {"name": "opened_date", "type": "UINT"},
            {"name": "closed_date", "type": "UINT"},
            {"name": "tags", "type": "LIST<STRING>"},
        ],
        description="Financial account",
    ),
    VertexType(
        name="Address",
        primary_id="v_id STRING",
        attributes=[
            {"name": "v_id", "type": "STRING"},
            {"name": "full_address", "type": "STRING"},
            {"name": "city", "type": "STRING"},
            {"name": "country", "type": "STRING"},
            {"name": "postal_code", "type": "STRING"},
            {"name": "address_type", "type": "STRING"},
        ],
        description="Physical address",
    ),
    VertexType(
        name="Device",
        primary_id="v_id STRING",
        attributes=[
            {"name": "v_id", "type": "STRING"},
            {"name": "device_type", "type": "STRING"},
            {"name": "ip_address", "type": "STRING"},
            {"name": "user_agent", "type": "STRING"},
            {"name": "country", "type": "STRING"},
            {"name": "risk_score", "type": "DOUBLE"},
        ],
        description="Computing device",
    ),
    VertexType(
        name="Transaction",
        primary_id="v_id STRING",
        attributes=[
            {"name": "v_id", "type": "STRING"},
            {"name": "tx_hash", "type": "STRING"},
            {"name": "amount", "type": "DOUBLE"},
            {"name": "currency", "type": "STRING"},
            {"name": "tx_type", "type": "STRING"},
            {"name": "timestamp", "type": "UINT"},
            {"name": "from_account", "type": "STRING"},
            {"name": "to_account", "type": "STRING"},
            {"name": "risk_score", "type": "DOUBLE"},
            {"name": "is_suspicious", "type": "BOOL"},
            {"name": "tags", "type": "LIST<STRING>"},
        ],
        description="Financial transaction",
    ),
]

EDGE_TYPES = [
    EdgeType(
        name="KNOWS",
        from_types=["Person", "Person"],
        to_types=["Person", "Person"],
        attributes=[],
        description="Person-person social relationship",
        is_directed=False,
    ),
    EdgeType(
        name="EMPLOYED_BY",
        from_types=["Person"],
        to_types=["Company"],
        attributes=[
            {"name": "role", "type": "STRING"},
            {"name": "start_date", "type": "UINT"},
            {"name": "end_date", "type": "UINT"},
        ],
        description="Employment relationship",
        is_directed=True,
    ),
    EdgeType(
        name="OWNS",
        from_types=["Person", "Company"],
        to_types=["Company", "Account"],
        attributes=[
            {"name": "ownership_pct", "type": "DOUBLE"},
            {"name": "is_beneficial_owner", "type": "BOOL"},
        ],
        description="Ownership stake",
        is_directed=True,
    ),
    EdgeType(
        name="RELATED_TO",
        from_types=["Person", "Company"],
        to_types=["Person", "Company"],
        attributes=[
            {"name": "relationship_type", "type": "STRING"},
            {"name": "description", "type": "STRING"},
        ],
        description="Generic related-to relationship",
        is_directed=False,
    ),
    EdgeType(
        name="SENT_TRANSACTION",
        from_types=["Account"],
        to_types=["Transaction"],
        attributes=[
            {"name": "amount", "type": "DOUBLE"},
            {"name": "timestamp", "type": "UINT"},
            {"name": "tx_hash", "type": "STRING"},
        ],
        description="Account sends transaction",
        is_directed=True,
    ),
    EdgeType(
        name="RECEIVED_TRANSACTION",
        from_types=["Transaction"],
        to_types=["Account"],
        attributes=[
            {"name": "amount", "type": "DOUBLE"},
            {"name": "timestamp", "type": "UINT"},
            {"name": "tx_hash", "type": "STRING"},
        ],
        description="Account receives transaction",
        is_directed=True,
    ),
    EdgeType(
        name="LINKED_TO_ACCOUNT",
        from_types=["Person", "Company"],
        to_types=["Account"],
        attributes=[
            {"name": "link_type", "type": "STRING"},
        ],
        description="Entity linked to financial account",
        is_directed=True,
    ),
    EdgeType(
        name="RESIDES_AT",
        from_types=["Person"],
        to_types=["Address"],
        attributes=[],
        description="Person resides at address",
        is_directed=True,
    ),
    EdgeType(
        name="REGISTERED_AT",
        from_types=["Company"],
        to_types=["Address"],
        attributes=[],
        description="Company registered at address",
        is_directed=True,
    ),
    EdgeType(
        name="LOCATED_AT",
        from_types=["Account", "Company"],
        to_types=["Address"],
        attributes=[],
        description="Entity located at address",
        is_directed=True,
    ),
    EdgeType(
        name="USED_DEVICE",
        from_types=["Person", "Account"],
        to_types=["Device"],
        attributes=[
            {"name": "last_used", "type": "UINT"},
        ],
        description="Entity used device",
        is_directed=True,
    ),
    EdgeType(
        name="PART_OF",
        from_types=["Person", "Company", "Account"],
        to_types=["FraudRing"],
        attributes=[
            {"name": "role", "type": "STRING"},
            {"name": "risk_contribution", "type": "DOUBLE"},
        ],
        description="Entity part of fraud ring",
        is_directed=True,
    ),
    EdgeType(
        name="CONNECTED_TO",
        from_types=["Device", "Device"],
        to_types=["Device", "Device"],
        attributes=[],
        description="Device network connection",
        is_directed=False,
    ),
]

VERTEX_NAMES = [v.name for v in VERTEX_TYPES]
EDGE_NAMES = [e.name for e in EDGE_TYPES]

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