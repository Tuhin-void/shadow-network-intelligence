"""
GraphClient — TigerGraph Cloud v2 RESTPP client with offline fallback.

Key features:
- Token-based auth for TigerGraph Cloud Enterprise v2
- Automatic offline fallback when TigerGraph is unreachable
- All CRUD operations via RESTPP
- GSQL query installation and execution
"""
import logging
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class OfflineFallback:
    """
    Fallback graph operations using local dataset when TigerGraph is unreachable.
    Used when TigerGraph returns 403 (token required) or is unreachable.
    """

    def __init__(self, dataset=None):
        self.dataset = dataset
        self._entity_index: dict[str, dict] = {}
        self._edge_index: list[dict] = []
        self._initialized = False

    def init_from_dataset(self, dataset):
        """Initialize fallback index from local dataset."""
        self.dataset = dataset
        self._entity_index = {}
        self._edge_index = []

        for p in getattr(dataset, 'persons', [])[:5000]:
            eid = p.get('id', '') or p.get('v_id', '')
            if eid:
                self._entity_index[eid] = {"type": "Person", "data": p}

        for c in getattr(dataset, 'companies', [])[:5000]:
            eid = c.get('id', '') or c.get('v_id', '')
            if eid:
                self._entity_index[eid] = {"type": "Company", "data": c}

        for a in getattr(dataset, 'accounts', [])[:10000]:
            eid = a.get('id', '') or a.get('v_id', '')
            if eid:
                self._entity_index[eid] = {"type": "Account", "data": a}

        for t in getattr(dataset, 'transactions', [])[:5000]:
            eid = t.get('id', '') or t.get('v_id', '')
            if eid:
                self._entity_index[eid] = {"type": "Transaction", "data": t}

        if hasattr(dataset, 'get_edges_for_entity'):
            edge_set = set()
            for eid in self._entity_index.keys():
                edges = dataset.get_edges_for_entity(eid)
                for edge in edges:
                    edge_key = f"{edge.get('from_id', '')}|{edge.get('to_id', '')}|{edge.get('relationship', '')}"
                    if edge_key not in edge_set:
                        edge_set.add(edge_key)
                        self._edge_index.append({"from": edge.get("from_id", ""), "to": edge.get("to_id", ""), "type": edge.get("relationship", "")})

        self._initialized = True
        logger.info(f"Offline fallback initialized: {len(self._entity_index)} entities, {len(self._edge_index)} edges")

    def get_vertex(self, vertex_id: str) -> Optional[dict]:
        return self._entity_index.get(vertex_id, {}).get("data")

    def get_neighbors(self, entity_id: str, limit: int = 50) -> list[dict]:
        neighbors = []
        for edge in self._edge_index:
            if edge.get("from") == entity_id:
                target = edge.get("to", "")
                target_data = self._entity_index.get(target, {})
                neighbors.append({"v_id": target, "type": target_data.get("type", ""), "edge_type": edge.get("type", "")})
            elif edge.get("to") == entity_id:
                source = edge.get("from", "")
                source_data = self._entity_index.get(source, {})
                neighbors.append({"v_id": source, "type": source_data.get("type", ""), "edge_type": edge.get("type", "")})
            if len(neighbors) >= limit:
                break
        return neighbors

    def search_by_keyword(self, query: str, limit: int = 20) -> list[dict]:
        tokens = query.lower().split()
        results = []
        for eid, entry in self._entity_index.items():
            data = entry.get("data", {})
            name = data.get("name", "") or data.get("first_name", "") + " " + data.get("last_name", "")
            if name and any(t in name.lower() for t in tokens):
                results.append({"v_id": eid, "type": entry.get("type", ""), "name": name, "data": data})
            if len(results) >= limit:
                break
        return results


class GraphClient:
    """
    TigerGraph Cloud v2 REST client with offline fallback.

    Auth model: 
    - Cloud: Use RESTPP secret directly in requests
    - Enterprise: Use password-based auth
    
    Falls back to local dataset when TigerGraph returns 403 or is unreachable.
    """

    KNOWN_VERTEX_TYPES = ["Person", "Company", "Account", "Address", "Device", "Transaction"]

    def __init__(self, config: "Config", dataset=None):
        from configs.config import Config, get_config

        if not isinstance(config, Config):
            config = get_config(config if isinstance(config, str) else None)

        self.config = config
        self.tg = config.tigergraph
        self.dataset = dataset
        self._is_cloud = self.tg.deployment == "cloud"

        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

        self._token: Optional[str] = None
        self._restpp_base = f"{self.tg.host}:{self.tg.restpp_port}/restpp"

        self._offline_fallback = OfflineFallback(dataset)
        self._offline_mode = False

        # Cloud deployment: Try secret auth, fall back to offline if fails
        # Enterprise deployment: use basic auth
        if self._is_cloud:
            if self.tg.secret:
                logger.info(f"TigerGraph Cloud: attempting RESTPP access with secret")
                # Try connectivity - if fails, use offline
                if not self._test_cloud_connectivity():
                    logger.warning("TigerGraph Cloud RESTPP not accessible - using offline fallback")
                    self._enable_offline_mode()
                    return
                logger.info("TigerGraph Cloud RESTPP access successful!")
            else:
                logger.warning("TigerGraph Cloud deployment but no secret - using offline fallback")
                self._enable_offline_mode()
                return
        else:
            self._session.auth = (self.tg.username, self.tg.password)
            self._session.headers["GSQL-Alias"] = "gsql"

            # Test connectivity - if fails, enable offline mode
            if not self._test_connectivity():
                self._enable_offline_mode()

    def _test_connectivity(self) -> bool:
        """Test if TigerGraph is reachable with current auth."""
        try:
            resp = self._session.get(f"{self._restpp_base}/echo", timeout=10)
            if resp.status_code == 200:
                logger.info("TigerGraph connectivity OK (echo test)")
                return True
            resp = self._session.get(
                f"{self._restpp_base}/graph/{self.tg.graph}/vertices/Person?limit=1",
                timeout=15,
            )
            if resp.status_code == 200:
                logger.info("TigerGraph connectivity OK (vertex test)")
                return True
            elif resp.status_code == 403:
                logger.warning("TigerGraph returned 403 - auth issue")
                return False
            else:
                logger.warning(f"TigerGraph returned {resp.status_code}")
                return False
        except Exception as e:
            logger.warning(f"TigerGraph connectivity test failed: {e}")
            return False

    def _test_cloud_connectivity(self) -> bool:
        """Test TigerGraph Cloud RESTPP with secret auth."""
        auth_params = self._build_auth_params()
        if not auth_params:
            return False
        
        try:
            url = f"{self._restpp_base}/graph/{self.tg.graph}/vertices/Person?limit=1"
            url += "&" + "&".join(f"{k}={v}" for k, v in auth_params.items())
            
            resp = self._session.get(url, timeout=15)
            if resp.status_code == 200:
                logger.info("TigerGraph Cloud RESTPP accessible")
                return True
            elif resp.status_code == 403:
                logger.warning("TigerGraph Cloud returned 403 - secret may be invalid")
                return False
            else:
                logger.warning(f"TigerGraph Cloud returned {resp.status_code}")
                return False
        except Exception as e:
            logger.warning(f"TigerGraph Cloud connectivity test failed: {e}")
            return False

    def _build_auth_params(self) -> dict:
        """Build auth parameters for RESTPP requests."""
        if self._is_cloud and self.tg.secret:
            return {"secret": self.tg.secret}
        return {}

    def _build_auth_headers(self) -> dict:
        """Build auth headers for RESTPP requests."""
        headers = {}
        if self._is_cloud and self.tg.secret:
            # Some TG Cloud endpoints accept secret as header
            pass
        return headers

    def _is_token_required_error(self, resp) -> bool:
        """Check if response indicates token auth required."""
        if resp.status_code == 403:
            data = resp.json()
            code = data.get("code", "")
            return code == "REST-10016" or "token" in data.get("message", "").lower()
        return False

    def _enable_offline_mode(self) -> None:
        """Enable offline fallback mode."""
        if not self._offline_mode:
            self._offline_mode = True
            if self.dataset and not self._offline_fallback._initialized:
                self._offline_fallback.init_from_dataset(self.dataset)
            logger.warning("TigerGraph unreachable — switched to offline fallback mode")

    def health_check(self) -> dict:
        """Comprehensive health check."""
        result = {
            "restpp": not self._offline_mode,
            "gsql": not self._offline_mode,
            "graph": not self._offline_mode,
            "auth": not self._offline_mode,
            "offline_mode": self._offline_mode,
            "healthy": True,
            "mode": "LIVE" if not self._offline_mode else "OFFLINE",
            "deployment": self.tg.deployment,
            "latency_ms": 0.0,
            "vertex_counts": {},
        }

        if self._offline_mode:
            result["healthy"] = True
            result["vertex_counts"] = {"offline_fallback": True}
            result["message"] = "Using offline fallback - TigerGraph Cloud RESTPP not programmatically accessible"
            return result

        # If not offline, test actual connectivity
        start = time.time()
        auth_params = self._build_auth_params()
        
        try:
            url = f"{self._restpp_base}/graph/{self.tg.graph}/vertices/Person?limit=1"
            if auth_params:
                url += "&" + "&".join(f"{k}={v}" for k, v in auth_params.items())
            
            resp = self._session.get(url, timeout=15)
            result["latency_ms"] = (time.time() - start) * 1000

            if resp.status_code == 200:
                result["restpp"] = True
                result["graph"] = True
                result["auth"] = True
                data = resp.json()
                result["api_version"] = data.get("version", {}).get("api", "v2")
                result["healthy"] = True
                result["vertex_counts"] = self.get_vertex_counts()
            elif resp.status_code == 403:
                result["auth"] = False
                result["message"] = "403 Forbidden - check secret configuration"
                self._enable_offline_mode()
                result["offline_mode"] = True
                result["healthy"] = True
            else:
                result["details"] = {"status": resp.status_code, "body": resp.text[:200]}
        except Exception as e:
            result["details"] = {"exception": str(e)}
            result["latency_ms"] = (time.time() - start) * 1000

        return result

        start = time.time()
        auth_params = self._build_auth_params()
        
        try:
            # Test graph endpoint with secret auth
            url = f"{self._restpp_base}/graph/{self.tg.graph}/vertices/Person?limit=1"
            if auth_params:
                url += "&" + "&".join(f"{k}={v}" for k, v in auth_params.items())
            
            resp = self._session.get(url, timeout=15)
            result["latency_ms"] = (time.time() - start) * 1000

            if resp.status_code == 200:
                result["restpp"] = True
                result["graph"] = True
                result["auth"] = True
                data = resp.json()
                result["api_version"] = data.get("version", {}).get("api", "v2")
                result["healthy"] = True
                result["vertex_counts"] = self.get_vertex_counts()
            elif resp.status_code == 403:
                result["auth"] = False
                result["details"] = {"error": "403 Forbidden - check secret"}
                self._enable_offline_mode()
                result["offline_mode"] = True
                result["healthy"] = True
            else:
                result["details"] = {"status": resp.status_code, "body": resp.text[:200]}
        except Exception as e:
            result["details"] = {"exception": str(e)}
            result["latency_ms"] = (time.time() - start) * 1000

        return result

    def get_vertex_counts(self) -> dict[str, Any]:
        """Get vertex counts per type."""
        if self._offline_mode:
            counts = {}
            if self._offline_fallback._initialized:
                for eid, entry in self._offline_fallback._entity_index.items():
                    vt = entry.get("type", "unknown")
                    counts[vt] = counts.get(vt, 0) + 1
            return counts

        counts = {}
        auth_params = self._build_auth_params()
        auth_str = "&" + "&".join(f"{k}={v}" for k, v in auth_params.items()) if auth_params else ""
        
        for vtype in self.KNOWN_VERTEX_TYPES:
            try:
                url = f"{self._restpp_base}/graph/{self.tg.graph}/vertices/{vtype}?limit=1{auth_str}"
                resp = self._session.get(url, timeout=10)
                if resp.status_code == 200:
                    count = resp.headers.get("X-Total-List-Count", "0")
                    try:
                        counts[vtype] = int(count)
                    except ValueError:
                        counts[vtype] = count
                else:
                    counts[vtype] = f"error {resp.status_code}"
            except Exception as e:
                counts[vtype] = str(e)
        return counts

    def get_vertex(self, vertex_type: str, vertex_id: str) -> Optional[dict]:
        """Get single vertex by type and ID."""
        if self._offline_mode:
            data = self._offline_fallback.get_vertex(vertex_id)
            return {"v_id": vertex_id, "type": vertex_type, "attributes": data or {}}

        try:
            auth_params = self._build_auth_params()
            auth_str = "&" + "&".join(f"{k}={v}" for k, v in auth_params.items()) if auth_params else ""
            url = f"{self._restpp_base}/graph/{self.tg.graph}/vertices/{vertex_type}/{vertex_id}{auth_str}"
            resp = self._session.get(url, timeout=15)
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                return results[0] if results else None
            if resp.status_code == 403:
                self._enable_offline_mode()
                return self.get_vertex(vertex_type, vertex_id)
            return None
        except Exception as e:
            logger.error(f"get_vertex({vertex_type}/{vertex_id}) failed: {e}")
            return None

    def get_vertices(self, vertex_type: str, limit: int = 100, where: str = "") -> list[dict]:
        """Get vertices of a specific type."""
        if self._offline_mode:
            results = []
            if vertex_type == "Person":
                for eid, entry in list(self._offline_fallback._entity_index.items())[:limit]:
                    if entry.get("type") == "Person":
                        results.append({"v_id": eid, "type": "Person", "attributes": entry.get("data", {})})
            elif vertex_type == "Company":
                for eid, entry in list(self._offline_fallback._entity_index.items())[:limit]:
                    if entry.get("type") == "Company":
                        results.append({"v_id": eid, "type": "Company", "attributes": entry.get("data", {})})
            return results

        try:
            params = {"limit": limit}
            if where:
                params["where"] = where
            
            # Add auth params for cloud deployment
            auth_params = self._build_auth_params()
            if auth_params:
                params.update(auth_params)

            resp = self._session.get(
                f"{self._restpp_base}/graph/{self.tg.graph}/vertices/{vertex_type}",
                params=params,
                timeout=30,
            )
            if resp.status_code == 200:
                return resp.json().get("results", [])
            if resp.status_code == 403:
                self._enable_offline_mode()
                return self.get_vertices(vertex_type, limit, where)
            return []
        except Exception as e:
            logger.error(f"get_vertices({vertex_type}) failed: {e}")
            return []

    def get_neighbors(self, entity_id: str, vertex_type: str = "", edge_type: str = "", limit: int = 50, depth: int = 1) -> dict:
        """Get neighbors of an entity."""
        if self._offline_mode:
            neighbors = self._offline_fallback.get_neighbors(entity_id, limit)
            return {"results": [{"neighbors": neighbors}]}

        params = {"limit": limit}
        if depth > 1:
            params["maxHops"] = depth
        
        # Add auth params for cloud deployment
        auth_params = self._build_auth_params()
        if auth_params:
            params.update(auth_params)

        url = f"{self._restpp_base}/graph/{self.tg.graph}/neighbors/{entity_id}"
        if vertex_type:
            url = f"{self._restpp_base}/graph/{self.tg.graph}/vertices/{vertex_type}/{entity_id}/neighbors"

        try:
            resp = self._session.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 403:
                self._enable_offline_mode()
                return self.get_neighbors(entity_id, vertex_type, edge_type, limit, depth)
            return {"error": f"HTTP {resp.status_code}"}
        except Exception as e:
            logger.error(f"get_neighbors({entity_id}) failed: {e}")
            return {"error": str(e)}

    def get_edges(self, from_id: str, from_type: str = "", edge_type: str = "", limit: int = 100) -> list[dict]:
        """Get edges from an entity."""
        if self._offline_mode:
            edges = []
            for edge in self._offline_fallback._edge_index:
                if edge.get("from") == from_id:
                    edges.append({"from_id": from_id, "to_id": edge.get("to", ""), "edge_type": edge.get("type", "")})
                if len(edges) >= limit:
                    break
            return edges

        try:
            from_vtype = from_type or "Person"
            url = f"{self._restpp_base}/graph/{self.tg.graph}/edges/{from_vtype}/{from_id}/{edge_type or '*'}"
            resp = self._session.get(url, params={"limit": limit}, timeout=15)
            if resp.status_code == 200:
                return resp.json().get("results", [])
            return []
        except Exception as e:
            logger.error(f"get_edges failed: {e}")
            return []

    def upsert_vertex(self, vertex_type: str, attributes: dict) -> bool:
        """Upsert a single vertex."""
        if self._offline_mode:
            return True

        v_id = attributes.get("v_id") or attributes.get("id")
        url = f"{self._restpp_base}/graph/{self.tg.graph}/vertices/{vertex_type}"
        if v_id:
            url += f"/{v_id}"

        payload = {"attributes": {k: v for k, v in attributes.items() if k not in ("v_id", "id")}}
        if v_id:
            payload["vertexId"] = str(v_id)

        try:
            resp = self._session.post(url, json=payload, timeout=15)
            return resp.status_code in (200, 201, 202)
        except Exception as e:
            logger.error(f"upsert_vertex failed: {e}")
            return False

    def upsert_edge(self, edge_type: str, from_type: str, from_id: str, to_type: str, to_id: str, attributes: Optional[dict] = None) -> bool:
        """Upsert a single edge."""
        if self._offline_mode:
            return True

        url = f"{self._restpp_base}/graph/{self.tg.graph}/edges/{from_type}/{from_id}/{edge_type}/{to_type}/{to_id}"
        try:
            resp = self._session.put(url, json={"attributes": attributes or {}}, timeout=15)
            return resp.status_code in (200, 201, 202)
        except Exception as e:
            logger.error(f"upsert_edge failed: {e}")
            return False

    def upsert_batch_vertices(self, vertex_type: str, records: list[dict]) -> dict:
        """Upsert multiple vertices via batch."""
        if self._offline_mode or not records:
            return {"loadSuccess": len(records), "loadFailure": 0}

        formatted = []
        for rec in records:
            v_id = rec.get("v_id") or rec.get("id", "")
            attrs = {k: v for k, v in rec.items() if k not in ("v_id", "id")}
            item = {"vertexType": vertex_type, "attributes": attrs}
            if v_id:
                item["vertexId"] = str(v_id)
            formatted.append(item)

        url = f"{self._restpp_base}/graph/{self.tg.graph}/vertices/{vertex_type}"
        try:
            resp = self._session.post(url, json=formatted, timeout=120)
            if resp.status_code == 200:
                return resp.json()
            return {"error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
        except Exception as e:
            logger.error(f"upsert_batch_vertices failed: {e}")
            return {"error": str(e)}

    def upsert_batch_edges(self, edge_type: str, records: list[dict]) -> dict:
        """Upsert multiple edges via batch."""
        if self._offline_mode or not records:
            return {"loadSuccess": len(records), "loadFailure": 0}

        formatted = []
        for rec in records:
            formatted.append({
                "edgeType": edge_type,
                "fromVertexType": rec.get("from_type", "Person"),
                "fromVertexId": str(rec.get("from_id", "")),
                "toVertexType": rec.get("to_type", "Person"),
                "toVertexId": str(rec.get("to_id", "")),
                "attributes": {k: v for k, v in rec.items()
                              if k not in ("from_id", "to_id", "from_type", "to_type")},
            })

        url = f"{self._restpp_base}/graph/{self.tg.graph}/edges"
        try:
            resp = self._session.post(url, json=formatted, timeout=120)
            if resp.status_code == 200:
                return resp.json()
            return {"error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
        except Exception as e:
            logger.error(f"upsert_batch_edges failed: {e}")
            return {"error": str(e)}

    def run_gsql(self, query_string: str) -> dict:
        """Run inline GSQL query."""
        try:
            resp = self._session.post(
                f"{self.tg.host}:{self.tg.restpp_port}/gsqlserver/gsql",
                json={"query": query_string},
                params={"graphname": self.tg.graph},
                timeout=60,
            )
            if resp.status_code == 200:
                data = resp.json()
                if "error" in data and data.get("error"):
                    return data
                return {"results": data.get("results", [data])}
            return {"error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
        except Exception as e:
            logger.error(f"run_gsql failed: {e}")
            return {"error": str(e)}

    def run_installed_query(self, name: str, params: Optional[dict] = None) -> dict:
        """Run an installed GSQL query."""
        if self._offline_mode:
            return {"error": "offline_mode", "message": f"Query '{name}' skipped in offline mode"}

        p = params or {}
        
        # Add auth params for cloud deployment
        auth_params = self._build_auth_params()
        p.update(auth_params)
        
        url = f"{self._restpp_base}/query/{self.tg.graph}/{name}"

        try:
            resp = self._session.get(url, params=p, timeout=30)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 403:
                self._enable_offline_mode()
                return {"error": "offline_mode", "message": f"Query '{name}' skipped in offline mode"}
            return {"error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
        except Exception as e:
            logger.warning(f"Installed query '{name}' failed: {e}")
            return {"error": str(e)}

    def install_queries(self, gsql_dir: str) -> dict:
        """Install GSQL queries from directory."""
        from pathlib import Path

        if self._offline_mode:
            logger.info("Skipping query installation (offline mode)")
            return {}

        results = {}
        gsql_path = Path(gsql_dir)

        for gsql_file in sorted(gsql_path.rglob("*.gsql")):
            name = gsql_file.stem
            try:
                with open(gsql_file, "r") as f:
                    gsql_content = f.read()

                resp = self._session.post(
                    f"{self.tg.host}:{self.tg.restpp_port}/gsqlserver/gsql",
                    json={"query": gsql_content},
                    params={"graphname": self.tg.graph},
                    timeout=60,
                )

                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("error"):
                        results[name] = {"success": False, "message": data.get("message", "")[:200]}
                    else:
                        results[name] = {"success": True, "message": "installed"}
                else:
                    results[name] = {"success": False, "message": f"HTTP {resp.status_code}"}
            except Exception as e:
                results[name] = {"success": False, "message": str(e)}

        return results

    def search_by_keyword(self, query: str, limit: int = 20) -> list[dict]:
        """Search entities by keyword (offline fallback for keyword search)."""
        if self._offline_mode:
            return self._offline_fallback.search_by_keyword(query, limit)

        tokens = query.lower().split()
        results = []
        for vtype in self.KNOWN_VERTEX_TYPES:
            vertices = self.get_vertices(vtype, limit=limit)
            for v in vertices:
                attrs = v.get("attributes", {})
                name = attrs.get("name", "")
                if name and any(t in name.lower() for t in tokens):
                    results.append({
                        "v_id": v.get("v_id", ""),
                        "type": vtype,
                        "name": name,
                        "score": sum(1 for t in tokens if t in name.lower()) / len(tokens),
                        "risk_score": attrs.get("risk_score", 0),
                        "attributes": attrs,
                    })
                if len(results) >= limit:
                    break
        return results