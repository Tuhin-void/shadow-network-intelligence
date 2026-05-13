"""Schema manager — creates ShadowGraph schema + installs GSQL queries."""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SchemaManager:
    """
    Manages ShadowGraph schema lifecycle:
    - Creates graph + vertex/edge types via GSQL
    - Installs GSQL queries
    """

    def __init__(self, graph_client: "GraphClient", dry_run: bool = False):
        self.client = graph_client
        self.dry_run = dry_run

    def create_schema(self, if_not_exists: bool = True) -> dict:
        """
        Create the full ShadowGraph schema in TigerGraph.
        Returns summary dict with creation status per element.
        """
        results = {"vertices": [], "edges": [], "success": False, "errors": []}

        if self.dry_run:
            logger.info("[DRY RUN] Would create ShadowGraph schema")
            results["success"] = True
            return results

        self._ensure_graph_exists()

        vertex_results = self._create_vertices(if_not_exists)
        results["vertices"] = vertex_results

        edge_results = self._create_edges(if_not_exists)
        results["edges"] = edge_results

        results["success"] = all(v["success"] for v in vertex_results) and all(
            e["success"] for e in edge_results
        )

        return results

    def _ensure_graph_exists(self) -> bool:
        """Create the ShadowGraph if it doesn't exist."""
        gsql = f"CREATE GRAPH {self.client.tg.graph} *"
        try:
            resp = self.client.run_gsql(gsql)
            if "error" in resp and "already exists" in str(resp):
                logger.info("Graph ShadowGraph already exists")
                return True
            if "error" in resp:
                logger.warning(f"Graph creation response: {resp}")
                return True
            logger.info("Graph ShadowGraph created or already exists")
            return True
        except Exception as e:
            logger.warning(f"Graph existence check: {e}")
            return True

    def _create_vertices(self, if_not_exists: bool) -> list[dict]:
        from validation.schema_def import VERTEX_TYPES

        results = []
        for vt in VERTEX_TYPES:
            try:
                gsql = vt.gsql_create()
                if if_not_exists:
                    gsql = gsql.replace("CREATE VERTEX", "CREATE VERTEX IF NOT EXISTS", 1)
                resp = self.client.run_gsql(gsql)
                if "error" in resp:
                    msg = str(resp.get("error", resp))[:200]
                    if "already exists" in msg.lower():
                        results.append({"name": vt.name, "success": True, "message": "already exists"})
                    else:
                        results.append({"name": vt.name, "success": False, "message": msg})
                        logger.error(f"Vertex {vt.name} creation failed: {msg}")
                else:
                    results.append({"name": vt.name, "success": True, "message": "created"})
                    logger.info(f"Created vertex type: {vt.name}")
            except Exception as e:
                results.append({"name": vt.name, "success": False, "message": str(e)})
                logger.error(f"Vertex {vt.name} exception: {e}")
        return results

    def _create_edges(self, if_not_exists: bool) -> list[dict]:
        from validation.schema_def import EDGE_TYPES

        results = []
        for et in EDGE_TYPES:
            try:
                gsql = et.gsql_create()
                if if_not_exists:
                    gsql = gsql.replace("CREATE DIRECTED EDGE", "CREATE DIRECTED EDGE IF NOT EXISTS", 1)
                    gsql = gsql.replace("CREATE UNDIRECTED EDGE", "CREATE UNDIRECTED EDGE IF NOT EXISTS", 1)
                resp = self.client.run_gsql(gsql)
                if "error" in resp:
                    msg = str(resp.get("error", resp))[:200]
                    if "already exists" in msg.lower():
                        results.append({"name": et.name, "success": True, "message": "already exists"})
                    else:
                        results.append({"name": et.name, "success": False, "message": msg})
                        logger.error(f"Edge {et.name} creation failed: {msg}")
                else:
                    results.append({"name": et.name, "success": True, "message": "created"})
                    logger.info(f"Created edge type: {et.name}")
            except Exception as e:
                results.append({"name": et.name, "success": False, "message": str(e)})
                logger.error(f"Edge {et.name} exception: {e}")
        return results

    def install_queries(self, gsql_dir: Optional[str] = None) -> dict:
        """Install all GSQL queries from the gsql/ directory."""
        if gsql_dir is None:
            gsql_dir = str(Path(__file__).parent.parent / "gsql")

        results = self.client.install_queries(gsql_dir)
        success_count = sum(1 for r in results.values() if r.success)
        logger.info(f"Installed {success_count}/{len(results)} GSQL queries")
        return {
            "total": len(results),
            "success": success_count,
            "failed": len(results) - success_count,
            "details": {name: {"success": r.success, "message": r.message} for name, r in results.items()},
        }

    def full_setup(self, gsql_dir: Optional[str] = None) -> dict:
        """Run full schema setup: create schema + install queries."""
        logger.info("=== ShadowGraph Full Setup ===")
        schema_results = self.create_schema()
        logger.info(f"Schema creation: {schema_results}")

        query_results = self.install_queries(gsql_dir)
        logger.info(f"Query installation: {query_results}")

        return {"schema": schema_results, "queries": query_results}