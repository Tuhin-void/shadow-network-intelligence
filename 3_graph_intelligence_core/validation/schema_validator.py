"""Schema validator — validates TigerGraph schema against canonical definition."""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SchemaValidator:
    """Validates that a live TigerGraph graph matches the canonical ShadowGraph schema."""

    CANONICAL_VERTEX_TYPES = [
        "Person", "Company", "Account", "Address", "Device", "Transaction", "FraudRing",
    ]

    CANONICAL_EDGE_TYPES = [
        # Infrastructure
        "OWNS", "HAS_ACCOUNT", "TRANSFERRED_TO", "LOCATED_AT", "ASSOCIATED_WITH",
        "USES_DEVICE", "ACCESSED_FROM", "SENT_TRANSACTION", "RECEIVED_TRANSACTION",
        "REGISTERED_AT", "BENEFITS_FROM", "SHARES_DEVICE_WITH", "SHARES_ADDRESS_WITH",
        # Explicit ring membership
        "PERSON_MEMBER_OF_RING", "COMPANY_MEMBER_OF_RING", "ACCOUNT_MEMBER_OF_RING",
        "TRANSACTION_MEMBER_OF_RING", "DEVICE_CONNECTED_TO_RING", "ADDRESS_CONNECTED_TO_RING",
    ]

    def __init__(self, graph_client: "GraphClient"):
        self.client = graph_client

    def validate(self) -> "ValidationReport":
        report = ValidationReport()

        try:
            health = self.client.health_check()
            report.connection_ok = health.get("restpp", False)
            if not report.connection_ok:
                report.add_error(f"Cannot connect to TigerGraph: {health}")
                return report
        except Exception as e:
            report.add_error(f"Connection failed: {e}")
            return report

        # Validate vertices via pyTigerGraph
        try:
            live_vtypes = self.client._tg_conn.getVertexTypes() if self.client._tg_conn else []
            missing_v = set(self.CANONICAL_VERTEX_TYPES) - set(live_vtypes)
            if missing_v:
                report.add_error(f"Missing vertex types: {sorted(missing_v)}")
            else:
                report.add_success(f"All {len(self.CANONICAL_VERTEX_TYPES)} vertex types present: {live_vtypes}")
            report.found_vertex_types = list(live_vtypes)
        except Exception as e:
            report.add_error(f"Failed to read vertex types: {e}")

        # Validate edges via pyTigerGraph
        try:
            live_etypes = self.client._tg_conn.getEdgeTypes() if self.client._tg_conn else []
            live_edge_names = [e if isinstance(e, str) else e.get("Name", "") for e in live_etypes]
            missing_e = set(self.CANONICAL_EDGE_TYPES) - set(live_edge_names)
            if missing_e:
                report.add_error(f"Missing edge types: {sorted(missing_e)}")
            else:
                report.add_success(f"All {len(self.CANONICAL_EDGE_TYPES)} edge types present")
            report.found_edge_types = live_edge_names
        except Exception as e:
            report.add_error(f"Failed to read edge types: {e}")

        report.is_valid = len(report.errors) == 0
        return report

    def is_valid(self) -> bool:
        return self.validate().is_valid

    def get_schema_info(self) -> dict:
        report = self.validate()
        return {
            "connection_ok": report.connection_ok,
            "valid": report.is_valid,
            "vertex_types": report.found_vertex_types,
            "edge_types": report.found_edge_types,
            "errors": report.errors,
        }


class ValidationReport:
    def __init__(self):
        self.is_valid: bool = False
        self.connection_ok: bool = False
        self.found_vertex_types: list[str] = []
        self.found_edge_types: list[str] = []
        self.errors: list[str] = []
        self.successes: list[str] = []

    def add_error(self, error: str) -> None:
        self.errors.append(error)
        logger.error(f"Schema validation error: {error}")

    def add_success(self, msg: str) -> None:
        self.successes.append(msg)
        logger.info(f"Schema validation: {msg}")

    def __repr__(self) -> str:
        status = "✓ VALID" if self.is_valid else "✗ INVALID"
        lines = [f"SchemaValidationReport({status})"]
        for s in self.successes:
            lines.append(f"  ✓ {s}")
        for e in self.errors:
            lines.append(f"  ✗ {e}")
        return "\n".join(lines)
