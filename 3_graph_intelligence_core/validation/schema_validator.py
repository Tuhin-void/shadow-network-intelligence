"""Schema validator — validates TigerGraph schema against canonical definition."""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SchemaValidator:
    """
    Validates that a TigerGraph graph has the canonical ShadowGraph schema.
    """

    CANONICAL_VERTEX_TYPES = ["Person", "Company", "Account", "Address", "Device", "Transaction"]
    CANONICAL_EDGE_TYPES = [
        "KNOWS", "EMPLOYED_BY", "OWNS", "RELATED_TO",
        "SENT_TRANSACTION", "RECEIVED_TRANSACTION", "LINKED_TO_ACCOUNT",
        "RESIDES_AT", "REGISTERED_AT", "LOCATED_AT", "USED_DEVICE",
        "PART_OF", "CONNECTED_TO",
    ]

    def __init__(self, graph_client: "GraphClient"):
        self.client = graph_client

    def validate(self) -> "ValidationReport":
        """Run full schema validation."""
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

        try:
            vertex_types = self._get_vertex_types()
            missing_vertices = set(self.CANONICAL_VERTEX_TYPES) - set(vertex_types)
            if missing_vertices:
                report.add_error(f"Missing vertex types: {missing_vertices}")
            else:
                report.add_success(f"All {len(vertex_types)} vertex types present")
            report.found_vertex_types = vertex_types
        except Exception as e:
            report.add_error(f"Failed to read vertex types: {e}")

        try:
            edge_types = self._get_edge_types()
            missing_edges = set(self.CANONICAL_EDGE_TYPES) - set(edge_types)
            if missing_edges:
                report.add_error(f"Missing edge types: {missing_edges}")
            else:
                report.add_success(f"All {len(edge_types)} edge types present")
            report.found_edge_types = edge_types
        except Exception as e:
            report.add_error(f"Failed to read edge types: {e}")

        report.is_valid = len(report.errors) == 0
        return report

    def _get_vertex_types(self) -> list[str]:
        """Get list of vertex types from TigerGraph via REST API."""
        url = f"{self.client._restpp_base}/gsqlserver/gsql/vertices"
        resp = self.client._session.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            if results:
                vertices = results[0].get("@@vertexTypes", [])
                return [v.get("name") for v in vertices if v.get("name")]
        return []

    def _get_edge_types(self) -> list[str]:
        """Get list of edge types from TigerGraph via REST API."""
        url = f"{self.client._restpp_base}/gsqlserver/gsql/edges"
        resp = self.client._session.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            if results:
                edges = results[0].get("@@edgeTypes", [])
                return [e.get("name") for e in edges if e.get("name")]
        return []

    def is_valid(self) -> bool:
        """Quick boolean check."""
        return self.validate().is_valid

    def get_schema_info(self) -> dict:
        """Get current schema info as dict."""
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