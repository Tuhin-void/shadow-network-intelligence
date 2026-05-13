"""
GraphClient — Hybrid pyTigerGraph + RESTPP wrapper.

- pyTigerGraph for connection/session management and installed query execution.
- Direct RESTPP for fine-grained retrieval and batch upserts.
"""
import logging
import time
from typing import Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

try:
    from pyTigerGraph import TigerGraphConnection
    PYGT_AVAILABLE = True
except ImportError:
    PYGT_AVAILABLE = False
    TigerGraphConnection = None

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


@dataclass
class InstallResult:
    name: str
    success: bool
    message: str = ""


class GraphClient:
    """
    Hybrid TigerGraph client.

    - get_connection() → pyTigerGraph connection (for installed queries + session mgmt)
    - RESTPP methods → fine-grained control (upserts, vertex/edge reads)
    """

    def __init__(self, config: "Config"):
        from configs.config import Config
        if not isinstance(config, Config):
            from configs.config import load_config
            config = load_config(config)

        self.config = config
        self.tg = config.tigergraph
        self._pygt_conn: Optional[TigerGraphConnection] = None
        self._session = None
        self._restpp_base: str = ""

        if PYGT_AVAILABLE and REQUESTS_AVAILABLE:
            self._init_pygt()
            self._init_session()
        elif not PYGT_AVAILABLE:
            logger.warning("pyTigerGraph not installed — falling back to RESTPP-only mode")
            self._init_session()
        elif not REQUESTS_AVAILABLE:
            raise RuntimeError("requests library required")

    def _init_pygt(self) -> None:
        """Initialize pyTigerGraph connection."""
        try:
            host = self.tg.host.rstrip("/")
            if self.tg.use_ssl:
                scheme = "https"
            else:
                scheme = "http"

            self._pygt_conn = TigerGraphConnection(
                host=f"{scheme}://{host}",
                graphname=self.tg.graph,
                username=self.tg.username,
                password=self.tg.password,
                version="4.2",
            )
            logger.info(f"pyTigerGraph connected to {self.tg.graph}")
        except Exception as e:
            logger.warning(f"pyTigerGraph connection failed: {e}, using RESTPP-only mode")
            self._pygt_conn = None

    def _init_session(self) -> None:
        """Initialize requests session with auth."""
        import requests
        self._session = requests.Session()
        self._session.auth = (self.tg.username, self.tg.password)
        self._session.headers.update({"Content-Type": "application/json"})
        self._restpp_base = f"{self.tg.host}:{self.tg.restpp_port}/restpp"

    def get_connection(self) -> Optional[TigerGraphConnection]:
        """Get pyTigerGraph connection object."""
        return self._pygt_conn

    def health_check(self) -> dict:
        """Check TigerGraph connectivity."""
        result = {"restpp": False, "gsql": False, "pygt": False}

        try:
            resp = self._session.get(
                f"{self._restpp_base}/health",
                timeout=10,
            )
            result["restpp"] = resp.status_code == 200
        except Exception as e:
            result["restpp_error"] = str(e)

        if self._pygt_conn:
            try:
                self._pygt_conn.getVertexTypes()
                result["pygt"] = True
            except Exception as e:
                result["pygt_error"] = str(e)

        try:
            resp = self._session.get(
                f"{self.tg.host}:{self.tg.restpp_port}/gsqlserver/gsql/version",
                timeout=5,
            )
            result["gsql"] = resp.status_code == 200
        except Exception as e:
            result["gsql_error"] = str(e)

        result["healthy"] = result["restpp"]
        return result

    # === RESTPP Methods ===

    def get_vertex(self, vertex_type: str, vertex_id: str) -> Optional[dict]:
        """Get single vertex by ID."""
        url = f"{self._restpp_base}/graph/{self.tg.graph}/vertices/{vertex_type}/{vertex_id}"
        try:
            resp = self._session.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("results", [{}])[0] if data.get("results") else None
            return None
        except Exception as e:
            logger.error(f"get_vertex failed: {e}")
            return None

    def get_vertices(self, vertex_type: str, limit: int = 100, where: str = "") -> list[dict]:
        """Get vertices of a type, optionally filtered."""
        url = f"{self._restpp_base}/graph/{self.tg.graph}/vertices/{vertex_type}"
        params = {"limit": limit}
        if where:
            params["where"] = where
        try:
            resp = self._session.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                return resp.json().get("results", [])
            return []
        except Exception as e:
            logger.error(f"get_vertices failed: {e}")
            return []

    def get_neighbors(
        self,
        entity_id: str,
        edge_type: str = "",
        limit: int = 50,
        depth: int = 1,
    ) -> dict:
        """Get neighbors of a vertex via RESTPP."""
        if edge_type:
            url = f"{self._restpp_base}/graph/{self.tg.graph}/neighbors/{entity_id}"
            params = {"limit": limit, "edgeType": edge_type, "maxHops": depth}
        else:
            url = f"{self._restpp_base}/graph/{self.tg.graph}/neighbors/{entity_id}"
            params = {"limit": limit, "maxHops": depth}
        try:
            resp = self._session.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            return {"error": f"HTTP {resp.status_code}"}
        except Exception as e:
            logger.error(f"get_neighbors failed: {e}")
            return {"error": str(e)}

    def get_edges(
        self,
        edge_type: str,
        from_id: str,
        to_type: str = "",
        limit: int = 100,
    ) -> list[dict]:
        """Get edges of a type from a vertex."""
        url = f"{self._restpp_base}/graph/{self.tg.graph}/edges/{from_id}/{edge_type}"
        if to_type:
            url += f"/{to_type}"
        params = {"limit": limit}
        try:
            resp = self._session.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                return resp.json().get("results", [])
            return []
        except Exception as e:
            logger.error(f"get_edges failed: {e}")
            return []

    def upsert_vertex(self, vertex_type: str, attributes: dict) -> bool:
        """Upsert a single vertex."""
        url = f"{self._restpp_base}/graph/{self.tg.graph}/vertices/{vertex_type}"
        vertex_id = attributes.get("v_id") or attributes.get("id")
        if vertex_id:
            url += f"/{vertex_id}"

        payload = {"attributes": {k: v for k, v in attributes.items() if k != "v_id" and k != "id"}}
        try:
            resp = self._session.post(url, json=payload, timeout=15)
            return resp.status_code in (200, 201)
        except Exception as e:
            logger.error(f"upsert_vertex failed: {e}")
            return False

    def upsert_edge(
        self,
        edge_type: str,
        from_id: str,
        to_id: str,
        attributes: Optional[dict] = None,
    ) -> bool:
        """Upsert a single edge."""
        url = f"{self._restpp_base}/graph/{self.tg.graph}/edges/{from_id}/{edge_type}/{to_id}"
        payload = {"attributes": attributes or {}}
        try:
            resp = self._session.put(url, json=payload, timeout=15)
            return resp.status_code in (200, 201)
        except Exception as e:
            logger.error(f"upsert_edge failed: {e}")
            return False

    def upsert_batch_vertices(self, vertex_type: str, records: list[dict]) -> dict:
        """Upsert multiple vertices via RESTPP batch."""
        if not records:
            return {"load_success": 0, "load_failure": 0}

        url = f"{self._restpp_base}/graph/{self.tg.graph}/vertices/{vertex_type}"

        json_data = {"jsonLiteral": records}
        try:
            resp = self._session.post(url, json=json_data, timeout=120)
            if resp.status_code == 200:
                return resp.json()
            return {"error": f"HTTP {resp.status_code}: {resp.text}"}
        except Exception as e:
            logger.error(f"upsert_batch_vertices failed: {e}")
            return {"error": str(e)}

    def upsert_batch_edges(self, edge_type: str, records: list[dict]) -> dict:
        """Upsert multiple edges via RESTPP batch."""
        if not records:
            return {"load_success": 0, "load_failure": 0}

        url = f"{self._restpp_base}/graph/{self.tg.graph}/edges"

        json_data = {"jsonLiteral": records, "edgeType": edge_type}
        try:
            resp = self._session.post(url, json=json_data, timeout=120)
            if resp.status_code == 200:
                return resp.json()
            return {"error": f"HTTP {resp.status_code}: {resp.text}"}
        except Exception as e:
            logger.error(f"upsert_batch_edges failed: {e}")
            return {"error": str(e)}

    def run_gsql(self, query_string: str) -> dict:
        """Run inline GSQL query via RESTPP."""
        encoded = query_string.replace(" ", "%20").replace("\n", "%0A")
        url = f"{self.tg.host}:{self.tg.restpp_port}/gsqlserver/gsql/query/{self.tg.graph}"
        params = {"graphname": self.tg.graph}
        payload = {"query": query_string}
        try:
            resp = self._session.post(url, json=payload, params=params, timeout=60)
            if resp.status_code == 200:
                return resp.json()
            return {"error": f"HTTP {resp.status_code}: {resp.text}"}
        except Exception as e:
            logger.error(f"run_gsql failed: {e}")
            return {"error": str(e)}

    # === Installed Query Methods ===

    def run_installed_query(self, name: str, params: Optional[dict] = None) -> dict:
        """Run an installed GSQL query via pyTigerGraph."""
        if self._pygt_conn:
            try:
                return self._pygt_conn.runInstalledQuery(name, params or {}, timeout=30)
            except Exception as e:
                logger.warning(f"Installed query '{name}' failed via pyTigerGraph: {e}")

        gsql_str = self._inline_query_template(name, params or {})
        return self.run_gsql(gsql_str)

    def _inline_query_template(self, name: str, params: dict) -> str:
        """Build inline GSQL for common query patterns."""
        p = params

        if name == "tg_neighbors":
            vt = p.get("vertex_type", "Person")
            vid = p.get("vertex_id", "")
            depth = p.get("depth", 2)
            limit = p.get("limit", 50)
            return f"""
                INTERPRET QUERY (STRING v_type="{vt}", STRING v_id="{vid}", INT depth={depth}, INT limit={limit}) FOR GRAPH {self.tg.graph} {{
                    start = {{.{vt}(.*).id == "{vid}"}};
                    neighbors = SELECT s FROM start-(:e)-:{vt} WHERE s.type != start.type LIMIT limit;
                    PRINT neighbors;
                }}
            """

        if name == "tg_entity_profile":
            vid = p.get("vertex_id", "")
            return f"""
                INTERPRET QUERY (STRING vid="{vid}") FOR GRAPH {self.tg.graph} {{
                    entity = {{*.{vid}}};
                    PRINT entity;
                }}
            """

        if name == "tg_connected_component":
            vid = p.get("vertex_id", "")
            return f"""
                INTERPRET QUERY (STRING vid="{vid}") FOR GRAPH {self.tg.graph} {{
                    start = {{*.{vid}}};
                    PRINT start;
                }}
            """

        if name == "tg_fraud_ring":
            vid = p.get("vertex_id", "")
            threshold = p.get("risk_threshold", 0.7)
            return f"""
                INTERPRET QUERY (STRING vid="{vid}", FLOAT threshold={threshold}) FOR GRAPH {self.tg.graph} {{
                    seed = {{*.{vid}}};
                    result = SELECT v FROM seed-(:e)-:*v WHERE v.risk_score >= threshold OR v.type == "FraudRing";
                    PRINT result;
                }}
            """

        if name == "tg_layering_chain":
            from_acc = p.get("from_account", "")
            to_acc = p.get("to_account", "")
            min_hops = p.get("min_hops", 3)
            max_hops = p.get("max_hops", 7)
            return f"""
                INTERPRET QUERY (STRING from="{from_acc}", STRING to="{to_acc}", INT min_hops={min_hops}, INT max_hops={max_hops}) FOR GRAPH {self.tg.graph} {{
                    Path = SELECT v FROM Account:* -{{1:{max_hops}}}-> Account:*v WHERE v.id == "{to_acc}" AND length(Path) >= {min_hops};
                    PRINT Path;
                }}
            """

        if name == "tg_shell_cluster":
            min_entities = p.get("min_entities", 3)
            threshold = p.get("risk_threshold", 0.6)
            return f"""
                INTERPRET QUERY (INT min_e={min_entities}, FLOAT thresh={threshold}) FOR GRAPH {self.tg.graph} {{
                    offshore = SELECT c FROM Company:c WHERE c.is_offshore == true OR c.is_shell == true OR c.risk_score >= thresh;
                    PRINT offshore;
                }}
            """

        if name == "tg_smurfing":
            funnel = p.get("funnel_account", "")
            threshold = p.get("threshold", 10000)
            return f"""
                INTERPRET QUERY (STRING funnel="{funnel}", FLOAT thresh={threshold}) FOR GRAPH {self.tg.graph} {{
                    funnel_acc = {{Account."{funnel}"}};
                    incoming = SELECT t FROM funnel_acc<-(:TRANSFERRED_TO)-Account:a -(:TRANSFERRED_TO)-> Transaction:t WHERE t.amount < {threshold};
                    PRINT incoming;
                }}
            """

        if name == "tg_ownership_chain":
            company_id = p.get("company_id", "")
            max_depth = p.get("max_depth", 4)
            return f"""
                INTERPRET QUERY (STRING cid="{company_id}", INT max_d={max_depth}) FOR GRAPH {self.tg.graph} {{
                    start = {{Company."{company_id}"}};
                    chain = SELECT v FROM start-(:OWNS)-Person:p -(:OWNS)-{{1:{max_d}}}->Company:v;
                    PRINT chain;
                }}
            """

        if name == "tg_temporal_spike":
            account_id = p.get("account_id", "")
            window = p.get("window_hours", 24)
            return f"""
                INTERPRET QUERY (STRING acc="{account_id}", INT window={window}) FOR GRAPH {self.tg.graph} {{
                    acc = {{Account."{account_id}"}};
                    txns = SELECT t FROM acc-(:SENT_TRANSACTION|:RECEIVED_TRANSACTION)-Transaction:t;
                    PRINT txns;
                }}
            """

        if name == "tg_entity_risk":
            vid = p.get("vertex_id", "")
            return f"""
                INTERPRET QUERY (STRING vid="{vid}") FOR GRAPH {self.tg.graph} {{
                    entity = {{*.{vid}}};
                    PRINT entity.risk_score;
                }}
            """

        if name == "tg_shortest_path":
            from_id = p.get("from_id", "")
            to_id = p.get("to_id", "")
            mhops = p.get("max_hops", 5)
            return f"""
                INTERPRET QUERY (STRING f="{from_id}", STRING t="{to_id}", INT max_hops={mhops}) FOR GRAPH {self.tg.graph} {{
                    Path = SELECT v FROM *:* -{{1:{mhops}}}-> *:* WHERE v.id == "{to_id}";
                    PRINT Path;
                }}
            """

        return f'SELECT * FROM *:* LIMIT 1'

    def install_queries(self, gsql_dir: str) -> dict[str, InstallResult]:
        """Install GSQL queries from a directory."""
        from pathlib import Path
        import os

        results = {}
        gsql_path = Path(gsql_dir)

        for gsql_file in sorted(gsql_path.rglob("*.gsql")):
            name = gsql_file.stem
            try:
                with open(gsql_file, "r") as f:
                    gsql_content = f.read()

                url = f"{self.tg.host}:{self.tg.restpp_port}/gsqlserver/gsql"
                resp = self._session.post(
                    url,
                    json={"query": gsql_content},
                    params={"graphname": self.tg.graph},
                    timeout=60,
                )

                if resp.status_code == 200:
                    results[name] = InstallResult(name=name, success=True, message="installed")
                else:
                    results[name] = InstallResult(name=name, success=False, message=resp.text[:200])
            except Exception as e:
                results[name] = InstallResult(name=name, success=False, message=str(e))

        return results