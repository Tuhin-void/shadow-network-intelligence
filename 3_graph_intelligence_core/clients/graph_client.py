"""
GraphClient — TigerGraph Cloud client with offline fallback.

Key features:
- Uses pyTigerGraph native authentication (gsqlSecret + tgCloud=True)
- Automatic offline fallback when TigerGraph is unreachable
- All CRUD operations via pyTigerGraph
- GSQL query installation and execution
- Per-process TTL cache for get_neighbors / get_vertex (read-only hot path)

Auth: Uses TIGERGRAPH_GSQL_SECRET with pyTigerGraph's built-in cloud auth.
"""
import logging
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:
    import pyTigerGraph as tg
    PYTIGERGRAPH_AVAILABLE = True
except ImportError:
    PYTIGERGRAPH_AVAILABLE = False


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
    TigerGraph Cloud client using pyTigerGraph native authentication.

    Auth model:
    - Cloud: Uses pyTigerGraph with gsqlSecret and tgCloud=True
    - Enterprise: Uses username/password
    
    Falls back to local dataset when TigerGraph is unreachable.
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

        self._tg_conn = None
        self._offline_fallback = OfflineFallback(dataset)
        self._offline_mode = False

        # Read-only TTL cache for hot-path lookups (get_neighbors / get_vertex).
        # Significantly reduces latency for topology-rerank workloads that
        # walk the same vertices repeatedly in a single benchmark run.
        self._neighbor_cache: dict[tuple, tuple[float, dict]] = {}
        self._vertex_cache: dict[tuple, tuple[float, Optional[dict]]] = {}
        self._cache_ttl_s = 60.0
        self._cache_hits = 0
        self._cache_misses = 0

        # Liveness probe cache (see `probe_liveness`). The probe runs a TG
        # echo with a hard thread-bounded timeout so the orchestrator can
        # detect a paused/stopped workspace within seconds instead of
        # waiting for the next failed graph query.
        self._last_probe_at: float = 0.0
        self._last_probe_result: Optional[bool] = None

        # Initialize pyTigerGraph connection or fall back to offline
        if PYTIGERGRAPH_AVAILABLE:
            self._init_pyTigerGraph()
        else:
            logger.warning("pyTigerGraph not available - using offline fallback")
            self._enable_offline_mode()

    def _init_pyTigerGraph(self) -> None:
        """Initialize pyTigerGraph connection with native cloud auth."""
        try:
            if self._is_cloud and self.tg.gsql_secret:
                logger.info(f"Connecting to TigerGraph Cloud with gsqlSecret (tgCloud=True)")
                
                self._tg_conn = tg.TigerGraphConnection(
                    host=self.tg.host,
                    graphname=self.tg.graph,
                    gsqlSecret=self.tg.gsql_secret,
                    tgCloud=True,
                    sslPort=self.tg.restpp_port,
                )

                # getToken() sets authHeader correctly but doesn't call _refresh_auth_headers(),
                # so _cached_auth (used by every _prep_req call) keeps the old Basic auth header.
                # Calling _refresh_auth_headers() after getToken() fixes this.
                self._tg_conn.getToken(self.tg.gsql_secret)
                self._tg_conn._refresh_auth_headers()

                # Verify connection - try echo endpoint first
                try:
                    echo_result = self._tg_conn.echo()
                    logger.info(f"TigerGraph Cloud echo: {echo_result}")
                except Exception as echo_err:
                    logger.warning(f"Echo test failed: {echo_err}")

                # Try getting vertex types as verification
                vertex_types = self._tg_conn.getVertexTypes()
                logger.info(f"TigerGraph Cloud connected! Vertex types: {len(vertex_types)}")
                
            elif not self._is_cloud and self.tg.username and self.tg.password:
                logger.info(f"Connecting to TigerGraph Enterprise with username/password")
                
                self._tg_conn = tg.TigerGraphConnection(
                    host=self.tg.host,
                    graphname=self.tg.graph,
                    username=self.tg.username,
                    password=self.tg.password,
                    sslPort=self.tg.restpp_port,
                )
                
                vertex_types = self._tg_conn.getVertexTypes()
                logger.info(f"TigerGraph Enterprise connected! Vertex types: {len(vertex_types)}")
                
            else:
                logger.warning("No valid TigerGraph credentials - using offline fallback")
                self._enable_offline_mode()
                
        except Exception as e:
            logger.error(f"pyTigerGraph connection failed: {type(e).__name__}: {e}")
            logger.info("Falling back to offline mode")
            self._enable_offline_mode()

    def _test_connectivity(self) -> bool:
        """Test if TigerGraph is reachable via pyTigerGraph echo."""
        if not self._tg_conn:
            return False
        try:
            self._tg_conn.echo()
            return True
        except Exception as e:
            logger.warning(f"TigerGraph connectivity test failed: {e}")
            return False

    def probe_liveness(self, max_age_s: float = 10.0, timeout_s: float = 3.0) -> bool:
        """Proactive TG liveness probe with thread-bounded timeout.

        The platform's lazy `_offline_mode` flag only flips when a graph
        call fails — so a TG workspace that pauses while the system is
        idle goes unnoticed until the next investigation. This method
        gives callers (`/orchestrator/status`, `/ingest/environment`,
        `/health`) a cheap, cached way to ask "is TG actually up RIGHT
        NOW" and updates the offline flag accordingly.

        Result caching: probes are cached for `max_age_s` seconds so a
        15-second frontend poll doesn't hammer TG. Pass `max_age_s=0` to
        force a fresh probe (e.g. when an operator clicks Reconnect).

        Hard timeout: pyTigerGraph's underlying requests session has no
        default timeout — when TG is paused, `echo()` can block for
        30+ seconds. We bound the probe with `concurrent.futures` so
        the status endpoint stays responsive (default 3 s cap).

        Returns:
            True iff TG echo succeeded within `timeout_s`. Side effect:
            updates `self._offline_mode` to match the probe result, so
            subsequent `_offline_mode` reads are accurate without
            requiring another probe.
        """
        import concurrent.futures
        now = time.time()
        if (max_age_s > 0
                and self._last_probe_at
                and (now - self._last_probe_at) < max_age_s
                and self._last_probe_result is not None):
            return self._last_probe_result

        self._last_probe_at = now

        if self._tg_conn is None:
            # Never had a connection — definitionally offline. Keep the
            # offline flag truthful.
            self._last_probe_result = False
            if not self._offline_mode:
                self._enable_offline_mode()
            return False

        def _do_echo() -> bool:
            try:
                self._tg_conn.echo()
                return True
            except Exception:
                return False

        # NOTE: do NOT use `with ThreadPoolExecutor(...) as ex:` here —
        # the `with` block's __exit__ calls shutdown(wait=True), which
        # blocks until the submitted task finishes. When TG is paused
        # the echo() can block for tens of seconds, defeating our
        # timeout. We construct the executor explicitly and call
        # shutdown(wait=False) so the probe returns as soon as the
        # timeout fires; the orphaned worker thread completes (or fails)
        # in the background without blocking the caller.
        ok = False
        ex = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        try:
            fut = ex.submit(_do_echo)
            try:
                ok = fut.result(timeout=timeout_s)
            except concurrent.futures.TimeoutError:
                ok = False
        except Exception:
            ok = False
        finally:
            # Non-blocking shutdown — the worker thread either finished
            # (no-op) or is still in the underlying socket call; either
            # way we return immediately.
            ex.shutdown(wait=False)

        self._last_probe_result = ok

        # Truthful state synchronization. We do NOT silently leave the
        # offline flag stale, AND we do not flip back to online without
        # rebuilding the pyTigerGraph connection — a successful echo can
        # coexist with a stale auth-token state in `_tg_conn`, which
        # would cause every subsequent graph call to fail with
        # "Access Denied because input token is empty". The fix: trigger
        # the full `reconnect_if_offline` path (which calls
        # `_init_pyTigerGraph` → `getToken` → `_refresh_auth_headers`)
        # so subsequent calls use a freshly-authenticated connection.
        prev_offline = self._offline_mode
        if ok and prev_offline:
            logger.info(
                "probe_liveness: TG echo succeeded — rebuilding pyTigerGraph "
                "state to restore auth headers"
            )
            try:
                # Bypass the reconnect cooldown — we just confirmed TG
                # is reachable, no need to wait. reconnect_if_offline
                # flips `_offline_mode` to False on success.
                self.reconnect_if_offline(min_interval_s=0)
            except Exception as e:
                logger.warning(
                    "probe_liveness: post-recovery reconnect failed: %s — "
                    "remaining in offline mode (next probe will retry)",
                    e,
                )
                # Keep `_last_probe_result` honest: if reconnect failed,
                # the next env/status read should re-probe.
                self._last_probe_at = 0.0
        elif not ok and not prev_offline:
            logger.warning(
                "probe_liveness: TG echo failed (timeout=%.1fs) — engaging offline mode",
                timeout_s,
            )
            self._enable_offline_mode()

        return ok

    def _enable_offline_mode(self) -> None:
        """Enable offline fallback mode."""
        if not self._offline_mode:
            self._offline_mode = True
            if self.dataset and not self._offline_fallback._initialized:
                self._offline_fallback.init_from_dataset(self.dataset)
            # Loud, single-line operator banner. Engaging fallback silently
            # would let a demo run for minutes against local CSV without
            # the operator realizing TG is down — this prevents that.
            logger.warning(
                "════════════════════════════════════════════════════════════════"
            )
            logger.warning(
                "  TigerGraph unreachable — engaging OfflineFallback (local CSV)"
            )
            logger.warning(
                "  Investigations, benchmarks, and traversal will still run, "
                "but against the local dataset — NOT live TigerGraph. "
                "Health endpoint will report mode=OFFLINE."
            )
            logger.warning(
                "════════════════════════════════════════════════════════════════"
            )
        # Track the most-recent reconnect attempt so callers of
        # reconnect_if_offline() can rate-limit retries.
        import time as _t
        self._last_reconnect_attempt_at = _t.time()

    def reconnect_if_offline(self, *, min_interval_s: float = 5.0) -> bool:
        """
        Self-healing reconnect path. If the client is currently in
        offline-fallback mode, attempts a fresh TigerGraph connection
        (subject to a minimum interval between retries to avoid
        hammering the server). Returns True iff TG is reachable AFTER
        the call.

        This is the mechanism that lets a long-running orchestrator
        recover automatically when the TG workspace is unpaused without
        requiring a process restart.
        """
        import time as _t
        if not self._offline_mode:
            return True
        # Respect cooldown — don't retry more often than once per
        # min_interval_s. The probe itself can be slow (~3-10s) so the
        # cooldown keeps load reasonable.
        last = getattr(self, "_last_reconnect_attempt_at", 0.0)
        if (_t.time() - last) < min_interval_s:
            return False
        self._last_reconnect_attempt_at = _t.time()

        logger.info("attempting TigerGraph reconnect …")
        # Drop the previous connection object so _init_pyTigerGraph
        # builds a fresh one (token refresh is critical when the workspace
        # has been paused — the prior token is invalid).
        self._tg_conn = None
        # Optimistically clear the offline flag so _init_pyTigerGraph
        # can promote us out of offline if it succeeds.
        self._offline_mode = False
        try:
            self._init_pyTigerGraph()
        except Exception as e:
            logger.warning(f"reconnect attempt failed: {type(e).__name__}: {e}")
            self._enable_offline_mode()
            return False
        if self._offline_mode:
            logger.info("reconnect attempt did not restore TG connectivity")
            return False
        logger.info("TigerGraph reconnect succeeded — back online")
        return True

    def health_check(self) -> dict:
        """Comprehensive health check using pyTigerGraph."""
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
            result["message"] = "Using offline fallback"
            return result

        # Use pyTigerGraph connection
        start = time.time()
        try:
            vertex_types = self._tg_conn.getVertexTypes()
            result["latency_ms"] = (time.time() - start) * 1000
            result["restpp"] = True
            result["gsql"] = True
            result["graph"] = True
            result["auth"] = True
            result["healthy"] = True
            result["vertex_counts"] = {vt: "OK" for vt in vertex_types}
            result["message"] = f"Connected to {self.tg.graph} with {len(vertex_types)} vertex types"
        except Exception as e:
            result["latency_ms"] = (time.time() - start) * 1000
            result["message"] = f"Connection failed: {e}"
            result["details"] = {"error": str(e)}
            self._enable_offline_mode()
            result["offline_mode"] = True
            result["healthy"] = True
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
        for vtype in self.KNOWN_VERTEX_TYPES:
            try:
                counts[vtype] = self._tg_conn.getVertexCount(vtype)
            except Exception as e:
                counts[vtype] = str(e)
        return counts

    def get_vertex(self, vertex_type: str, vertex_id: str) -> Optional[dict]:
        """Get single vertex by type and ID using pyTigerGraph.

        Returns None for wrong-type / not-found errors (these are normal probes
        during entity-type disambiguation and must NOT trip offline fallback).
        Falls back to offline mode only on genuine connectivity failures.
        TTL-cached for the hot path.
        """
        if self._offline_mode:
            data = self._offline_fallback.get_vertex(vertex_id)
            return {"v_id": vertex_id, "type": vertex_type, "attributes": data or {}}

        cache_key = (vertex_type, vertex_id)
        cached = self._vertex_cache.get(cache_key)
        now = time.time()
        if cached and (now - cached[0]) < self._cache_ttl_s:
            self._cache_hits += 1
            return cached[1]
        self._cache_misses += 1

        try:
            result = self._tg_conn.getVerticesById(vertex_type, [vertex_id])
            v = result[0] if result else None
            self._vertex_cache[cache_key] = (now, v)
            return v
        except Exception as e:
            msg = str(e)
            if "is not a valid vertex id" in msg or "601" in msg or "404" in msg:
                logger.debug(f"get_vertex({vertex_type}/{vertex_id}): {msg}")
                self._vertex_cache[cache_key] = (now, None)
                return None
            logger.warning(f"get_vertex({vertex_type}/{vertex_id}) failed: {e}")
            self._enable_offline_mode()
            return self.get_vertex(vertex_type, vertex_id)

    def get_vertices(self, vertex_type: str, limit: int = 100, where: str = "") -> list[dict]:
        """Get vertices of a specific type using pyTigerGraph."""
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
            results = self._tg_conn.getVertices(vertex_type, limit=limit)
            return results
        except Exception as e:
            logger.error(f"get_vertices({vertex_type}) failed: {e}")
            self._enable_offline_mode()
            return self.get_vertices(vertex_type, limit, where)

    # ID prefix → canonical vertex type (used to infer vtype for getEdges).
    _ID_PREFIX_TO_VTYPE = {
        "P":    "Person",
        "C":    "Company",
        "A":    "Account",
        "ADDR": "Address",
        "D":    "Device",
        "TX":   "Transaction",
        "T":    "Transaction",
        "FR":   "FraudRing",
    }

    def _infer_vertex_type(self, entity_id: str) -> str:
        """Infer vertex type from ID prefix (P-001 → Person, etc.)."""
        if "-" not in entity_id:
            return ""
        prefix = entity_id.split("-", 1)[0]
        return self._ID_PREFIX_TO_VTYPE.get(prefix, "")

    def get_neighbors(self, entity_id: str, vertex_type: str = "", edge_type: str = "", limit: int = 50, depth: int = 1) -> dict:
        """
        Get neighbors of an entity. Uses pyTigerGraph's getEdges + a TTL cache
        to make the topology-rerank hot path fast.
        Returns {"results": [{"neighbors": [{v_id, type, edge_type}, ...]}]}.
        """
        if self._offline_mode:
            neighbors = self._offline_fallback.get_neighbors(entity_id, limit)
            return {"results": [{"neighbors": neighbors}]}

        vt = vertex_type or self._infer_vertex_type(entity_id)
        if not vt:
            return {"results": [{"neighbors": []}]}

        cache_key = (vt, str(entity_id), edge_type or "", limit)
        cached = self._neighbor_cache.get(cache_key)
        now = time.time()
        if cached and (now - cached[0]) < self._cache_ttl_s:
            self._cache_hits += 1
            return cached[1]
        self._cache_misses += 1

        try:
            if edge_type:
                edges = self._tg_conn.getEdges(vt, str(entity_id), edge_type)
            else:
                edges = self._tg_conn.getEdges(vt, str(entity_id))
        except Exception as e:
            logger.warning(f"getEdges({vt}/{entity_id}) failed: {e}")
            empty = {"results": [{"neighbors": []}]}
            self._neighbor_cache[cache_key] = (now, empty)
            return empty

        neighbors: list[dict] = []
        for e in edges[:limit]:
            from_id = e.get("from_id", "")
            to_id   = e.get("to_id",   "")
            e_type  = e.get("e_type",  e.get("edge_type", ""))
            if from_id == str(entity_id):
                target, target_type = to_id, e.get("to_type", "")
            else:
                target, target_type = from_id, e.get("from_type", "")
            neighbors.append({
                "v_id":      target,
                "type":      target_type,
                "edge_type": e_type,
                "attributes": e.get("attributes", {}),
            })
        result = {"results": [{"neighbors": neighbors}]}
        self._neighbor_cache[cache_key] = (now, result)
        return result

    def get_edges(self, from_id: str, from_type: str = "", edge_type: str = "", limit: int = 100) -> list[dict]:
        """Get edges from an entity using pyTigerGraph."""
        if self._offline_mode:
            edges = []
            for edge in self._offline_fallback._edge_index:
                if edge.get("from") == from_id:
                    edges.append({"from_id": from_id, "to_id": edge.get("to", ""), "edge_type": edge.get("type", "")})
                if len(edges) >= limit:
                    break
            return edges

        try:
            from_vtype = from_type or self._infer_vertex_type(from_id) or "Person"
            if edge_type:
                edges = self._tg_conn.getEdges(from_vtype, from_id, edge_type)
            else:
                edges = self._tg_conn.getEdges(from_vtype, from_id)
            return edges[:limit] if isinstance(edges, list) else []
        except Exception as e:
            logger.warning(f"get_edges({from_vtype}/{from_id}) failed: {e}")
            return []

    def upsert_vertex(self, vertex_type: str, attributes: dict) -> bool:
        """Upsert a single vertex via pyTigerGraph."""
        if self._offline_mode:
            return True

        v_id = attributes.get("v_id") or attributes.get("id")
        if not v_id:
            logger.error("upsert_vertex: missing vertex id")
            return False

        attrs = {k: v for k, v in attributes.items() if k not in ("v_id", "id")}
        try:
            result = self._tg_conn.upsertVertex(vertex_type, str(v_id), attrs)
            return result > 0
        except Exception as e:
            logger.error(f"upsert_vertex failed: {e}")
            return False

    def upsert_edge(self, edge_type: str, from_type: str, from_id: str, to_type: str, to_id: str, attributes: Optional[dict] = None) -> bool:
        """Upsert a single edge via pyTigerGraph."""
        if self._offline_mode:
            return True

        try:
            result = self._tg_conn.upsertEdge(from_type, str(from_id), edge_type, to_type, str(to_id), attributes or {})
            return result > 0
        except Exception as e:
            logger.error(f"upsert_edge failed: {e}")
            return False

    def upsert_batch_vertices(self, vertex_type: str, records: list[dict]) -> dict:
        """Upsert multiple vertices via pyTigerGraph batch."""
        if self._offline_mode or not records:
            return {"loadSuccess": len(records), "loadFailure": 0}

        vertices = []
        for rec in records:
            v_id = rec.get("v_id") or rec.get("id", "")
            if not v_id:
                continue
            attrs = {k: v for k, v in rec.items() if k not in ("v_id", "id")}
            vertices.append((str(v_id), attrs))

        try:
            result = self._tg_conn.upsertVertices(vertex_type, vertices)
            return {"loadSuccess": result, "loadFailure": len(records) - result}
        except Exception as e:
            logger.error(f"upsert_batch_vertices failed: {e}")
            return {"error": str(e)}

    def upsert_batch_edges(self, edge_type: str, records: list[dict]) -> dict:
        """Upsert multiple edges via pyTigerGraph batch."""
        if self._offline_mode or not records:
            return {"loadSuccess": len(records), "loadFailure": 0}

        # Group by (from_type, to_type) since upsertEdges requires consistent vertex types
        from collections import defaultdict
        groups: dict[tuple, list] = defaultdict(list)
        for rec in records:
            ft = rec.get("from_type", "Person")
            tt = rec.get("to_type", "FraudRing")
            attrs = {k: v for k, v in rec.items() if k not in ("from_id", "to_id", "from_type", "to_type")}
            groups[(ft, tt)].append((str(rec.get("from_id", "")), str(rec.get("to_id", "")), attrs))

        total_upserted = 0
        try:
            for (from_type, to_type), edges in groups.items():
                result = self._tg_conn.upsertEdges(from_type, edge_type, to_type, edges)
                total_upserted += result
            return {"loadSuccess": total_upserted, "loadFailure": len(records) - total_upserted}
        except Exception as e:
            logger.error(f"upsert_batch_edges failed: {e}")
            return {"error": str(e)}

    def run_gsql(self, query_string: str) -> dict:
        """Run inline GSQL query via pyTigerGraph."""
        if self._offline_mode:
            return {"error": "offline_mode", "message": "GSQL skipped in offline mode"}
        try:
            result = self._tg_conn.gsql(query_string)
            return {"results": result}
        except Exception as e:
            logger.error(f"run_gsql failed: {e}")
            return {"error": str(e)}

    def run_installed_query(self, name: str, params: Optional[dict] = None) -> dict:
        """Run an installed GSQL query using pyTigerGraph."""
        if self._offline_mode:
            return {"error": "offline_mode", "message": f"Query '{name}' skipped in offline mode"}

        try:
            result = self._tg_conn.runInstalledQuery(name, params=params or {})
            return {"results": result}
        except Exception as e:
            logger.warning(f"Installed query '{name}' failed: {e}")
            return {"error": str(e)}

    def install_queries(self, gsql_dir: str) -> dict:
        """Install GSQL queries from directory via pyTigerGraph."""
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
                result = self._tg_conn.gsql(gsql_content)
                results[name] = {"success": True, "message": str(result)[:200]}
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