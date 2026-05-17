"""
GraphRAG Engine — high-level orchestration of graph retrieval + summarization.
Replaces the fallback in 2_baseline_systems/pipelines/graph_rag.py
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class GraphRAGEngine:
    """
    High-level GraphRAG engine that orchestrates:
    1. Graph retrieval (entity + neighborhood + path + community + temporal)
    2. Compression (rule-based or LLM-based)
    3. Evidence chain building
    4. Context assembly for downstream LLM

    Interface compatible with 2_baseline_systems/pipelines/graph_rag.py:
        query: str, context: Optional[dict] = None, config: Optional[dict] = None
    Returns: dict with answer, contexts, entities, sources
    """

    def __init__(
        self,
        graph_client: "GraphClient",
        config: Optional["Config"] = None,
        compression: str = "rule_based",
        embedder=None,
    ):
        from configs.config import Config, get_config
        if config is None:
            config = get_config()
        elif not isinstance(config, Config):
            config = get_config(config if isinstance(config, str) else None)

        self.config = config
        self.compression = compression
        self.graph_client = graph_client
        self.embedder = embedder  # optional — enables semantic entity matching

        self._init_retrievers()
        self._init_summarizers()

    def _init_retrievers(self) -> None:
        from retrievers.entity_centric import EntityCentricRetriever
        from retrievers.neighborhood import NeighborhoodRetriever
        from retrievers.path_aware import PathAwareRetriever
        from retrievers.community import CommunityRetriever
        from retrievers.temporal import TemporalRetriever
        from retrievers.hybrid import HybridRetriever

        self.entity_retriever = EntityCentricRetriever(self.graph_client, embedder=self.embedder)
        self.neighborhood_retriever = NeighborhoodRetriever(self.graph_client)
        self.path_retriever = PathAwareRetriever(self.graph_client)
        self.community_retriever = CommunityRetriever(self.graph_client)
        self.temporal_retriever = TemporalRetriever(self.graph_client)
        self.hybrid_retriever = HybridRetriever(self.graph_client)

    def _init_summarizers(self) -> None:
        from summarization.rule_based import RuleBasedSummarizer
        from summarization.evidence_chain import EvidenceChainBuilder

        self.rule_summarizer = RuleBasedSummarizer(max_tokens=self.config.graphrag.max_context_tokens)
        self.evidence_builder = EvidenceChainBuilder()

        if self.compression == "llm":
            try:
                from summarization.llm_summarizer import LLMSummarizer
                self.llm_summarizer = LLMSummarizer(self.config)
            except Exception as e:
                logger.warning(f"LLM summarizer unavailable: {e}, using rule_based")
                self.llm_summarizer = None
        else:
            self.llm_summarizer = None

    def query(
        self,
        query: str,
        context: Optional[dict] = None,
        config: Optional[dict] = None,
    ) -> dict:
        """
        Main entry point. Executes graph retrieval + compression.

        Args:
            query: Natural language query
            context: Optional context from previous steps
            config: Optional override config {strategy, top_k, depth, compression}

        Returns:
            dict with keys: answer, contexts, entities, sources, metadata
        """
        cfg = config or {}
        strategy = cfg.get("strategy", "auto")
        top_k = cfg.get("top_k", self.config.graphrag.top_k)
        depth = cfg.get("depth", self.config.graphrag.traversal_depth)
        compression = cfg.get("compression", self.compression)

        retrieval_result = self._retrieve(query, strategy=strategy, top_k=top_k, depth=depth)

        compressed = self._compress(retrieval_result, query, compression)

        evidence_chain = self.evidence_builder.build_chain(retrieval_result, query)
        evidence_classified = self.evidence_builder.classify_chain(evidence_chain)

        entity_ids = [e.get("v_id", e.get("id", "")) for e in retrieval_result.get("entities", [])]
        entity_profiles = self._build_profiles(entity_ids[:5])

        return {
            "answer": compressed.get("summary", ""),
            "contexts": compressed,
            # Raw context list — typed graph-edge facts. Consumers (e.g. the
            # orchestrator's InvestigationReport) need this for bucketing.
            "context": retrieval_result.get("context", []),
            "entities": retrieval_result.get("entities", []),
            "paths": retrieval_result.get("paths", []),
            "communities": retrieval_result.get("communities", []),
            "sources": evidence_chain,
            "evidence_classified": evidence_classified,
            "entity_profiles": entity_profiles,
            "metadata": {
                "strategy": strategy,
                "compression": compression,
                "top_k": top_k,
                "depth": depth,
                "entity_count": len(retrieval_result.get("entities", [])),
                "neighbor_count": len(retrieval_result.get("context", [])),
                "evidence_count": len(evidence_chain),
            },
        }

    def _retrieve(
        self,
        query: str,
        strategy: str = "auto",
        top_k: int = 10,
        depth: int = 2,
    ) -> dict:
        """
        Execute graph retrieval based on strategy.

        Design note: the structural advantage of GraphRAG is multi-hop
        expansion, so the neighborhood retriever ALWAYS runs when seed
        entities exist — regardless of the requested strategy. Strategies
        gate which *additional* signals are computed (paths, communities),
        not whether context is populated.
        """
        if strategy == "auto":
            strategy = self._detect_strategy(query)

        result = {"strategy": strategy, "entities": [], "context": [], "paths": [], "communities": []}

        # ── Always: entity retrieval ──────────────────────────────────────
        entities = self.entity_retriever.retrieve(query, top_k=top_k)
        result["entities"] = [
            {"v_id": e.v_id, "type": e.vertex_type, "name": e.name, "score": e.score,
             "risk_score": e.risk_score, "attributes": e.attributes,
             # Topology features — visible proof of graph-native intelligence
             "propagated_risk":  getattr(e, "propagated_risk", None),
             "ring_touch_count": getattr(e, "ring_touch_count", 0),
             "fraud_degree":     getattr(e, "fraud_degree", 0),
             "rerank_reason":    getattr(e, "rerank_explanation", "")}
            for e in entities
        ]

        # ── Always: neighborhood expansion around the seeds ───────────────
        seed_ids = [e["v_id"] for e in result["entities"] if e.get("v_id")]
        if seed_ids:
            neighborhood = self.neighborhood_retriever.retrieve(
                seed_ids[:5], max_hops=depth,
            )
            ctx = [
                {"v_id": n.v_id, "type": n.vertex_type, "name": n.name,
                 "edge": n.edge_type, "depth": n.depth, "risk_score": n.risk_score,
                 "source": "neighborhood"}
                for n in neighborhood.get("nodes", [])
            ]

            # ── Hidden-relationship expansion ─────────────────────────────
            hidden = self._expand_hidden_relationships(seed_ids[:5])
            ctx.extend(hidden)

            # De-dup by (v_id, edge)
            seen = set()
            dedup = []
            for n in ctx:
                key = (n.get("v_id", ""), n.get("edge", ""))
                if key in seen:
                    continue
                seen.add(key)
                dedup.append(n)
            result["context"] = dedup

            # ── Ring-member entity promotion ──────────────────────────────
            # If any seed entity is a FraudRing, promote up to 4 of its
            # most-relevant members to the main entities list. This makes
            # ring investigations visibly populated (entities[] not stuck
            # at the single ring vertex) while being structurally truthful —
            # every promoted entity is a real ring member returned by the
            # reverse-traversal of the live graph.
            ring_seed = next(
                (e for e in result["entities"] if e.get("type") == "FraudRing"), None,
            )
            if ring_seed:
                self._promote_ring_members(ring_seed, hidden, result["entities"], top_k=top_k)

        # ── Strategy-gated extras ─────────────────────────────────────────
        if strategy in ("auto", "path", "full"):
            result["paths"] = self._find_relevant_paths(query, result["entities"])

        if strategy in ("auto", "community", "full"):
            result["communities"] = self.community_retriever.detect_high_risk_cluster(
                min_risk=0.7, limit=top_k,
            )

        return result

    # Edges that surface hidden coordination / fraud-ring membership.
    _HIDDEN_REL_EDGES: tuple[str, ...] = (
        "PERSON_MEMBER_OF_RING",
        "COMPANY_MEMBER_OF_RING",
        "ACCOUNT_MEMBER_OF_RING",
        "TRANSACTION_MEMBER_OF_RING",
        "SHARES_DEVICE_WITH",
        "SHARES_ADDRESS_WITH",
        "BENEFITS_FROM",
    )

    # Reverse-edge names — used to traverse FROM FraudRing into its members.
    # The live schema declares these via REVERSE_EDGE config on each ring edge.
    _RING_REVERSE_EDGES: tuple[str, ...] = (
        "reverse_person_member_of_ring",
        "reverse_company_member_of_ring",
        "reverse_account_member_of_ring",
        "reverse_transaction_member_of_ring",
        "reverse_device_connected_to_ring",
        "reverse_address_connected_to_ring",
    )

    @staticmethod
    def _promote_ring_members(
        ring_seed: dict, hidden_context: list[dict],
        entities_out: list[dict], top_k: int,
    ) -> None:
        """
        Insert top ring members from the hidden-expansion context into the
        main entity list, mutating `entities_out` in place. Caps total to
        `top_k`. Members are sorted by:
          - Person before Account before Transaction (key controllers first)
          - then by risk_score desc
        Each promoted entity is annotated as `via=<ring_id>` and source.
        """
        if not ring_seed or not hidden_context:
            return
        ring_id = ring_seed.get("v_id", "")
        type_priority = {"Person": 0, "Company": 1, "Account": 2, "Transaction": 3}

        candidates = [
            n for n in hidden_context
            if n.get("via") == ring_id
            and n.get("type") in type_priority
            and n.get("v_id")
        ]
        if not candidates:
            return

        existing_ids = {e.get("v_id") for e in entities_out}
        candidates.sort(
            key=lambda x: (
                type_priority.get(x.get("type", ""), 99),
                -(float(x.get("risk_score") or 0)),
            ),
        )
        # Number of slots we can fill without exceeding top_k.
        slots = max(0, top_k - len(entities_out))
        n_to_promote = min(slots, 4, len(candidates))
        for n in candidates[:n_to_promote]:
            v_id = n.get("v_id")
            if v_id in existing_ids:
                continue
            existing_ids.add(v_id)
            entities_out.append({
                "v_id":  v_id,
                "type":  n.get("type", ""),
                "name":  n.get("name") or v_id,
                "score": 0.6,  # legitimate ring-member surface score
                "risk_score": n.get("risk_score"),
                "attributes": {},
                "propagated_risk":  None,
                "ring_touch_count": 1,
                "fraud_degree":     1,
                "rerank_reason":    f"member of ring {ring_id}",
            })

    def _expand_hidden_relationships(self, seed_ids: list[str]) -> list[dict]:
        """
        For each seed, follow the high-signal coordination edges explicitly.
        For ring-membership edges, then take a 2nd hop into the ring to surface
        co-ring members (the canonical "hidden network" reveal).

        If the seed is a FraudRing, use reverse-edge traversal to walk DIRECTLY
        into the ring's members — this is the structural-intelligence superpower
        that VectorRAG fundamentally cannot match.
        """
        client = self.graph_client
        out: list[dict] = []

        # Helper: infer vertex type from ID prefix (mirrors GraphClient).
        infer = getattr(client, "_infer_vertex_type", lambda _: "")

        for sid in seed_ids:
            vt = infer(sid)
            if not vt:
                continue

            # ── Special path: FraudRing seed → reverse-traverse into members ──
            if vt == "FraudRing":
                out.extend(self._expand_ring_members(sid))
                continue

            ring_ids: list[str] = []
            for edge_type in self._HIDDEN_REL_EDGES:
                try:
                    nbrs = client.get_neighbors(sid, vertex_type=vt, edge_type=edge_type, limit=20)
                except Exception:
                    continue
                for block in nbrs.get("results", []):
                    if isinstance(block, dict) and "neighbors" in block:
                        for n in block["neighbors"]:
                            n_id   = n.get("v_id", "")
                            n_type = n.get("type", "")
                            out.append({
                                "v_id":  n_id,
                                "type":  n_type,
                                "name":  n.get("name") or n_id,
                                "edge":  edge_type,
                                "depth": 1,
                                "risk_score": n.get("risk_score"),
                                "source": "hidden_expansion",
                                "via":    sid,
                            })
                            # Remember ring vertices for 2nd-hop co-member expansion.
                            if n_type == "FraudRing":
                                ring_ids.append(n_id)

            # 2nd hop: from each touched ring, surface co-members.
            for ring_id in ring_ids[:3]:  # cap to avoid fan-out blow-up
                out.extend(self._expand_ring_members(ring_id, exclude_id=sid, depth=2))

        return out

    def _expand_ring_members(
        self, ring_id: str, exclude_id: str = "", depth: int = 1,
    ) -> list[dict]:
        """
        Reverse-traverse FROM a FraudRing into all its members.

        Fast path: if installed query `tg_ring_members` is available, use it
        for a single round-trip (vs 6 reverse-edge calls). This is graph-native
        retrieval at its purest — one GSQL invocation returns the full ring.
        Slow path: per-edge-type getEdges via the live `reverse_*_ring` edges.
        """
        # ── Fast path: installed GSQL query ───────────────────────────────
        try:
            qr = self.graph_client._tg_conn.runInstalledQuery(
                "tg_ring_members", {"ring": (ring_id,)},
            )
            return self._format_installed_ring_result(
                qr, ring_id, exclude_id, depth,
            )
        except Exception:
            # Fall through to slow path below.
            pass

        # ── Slow path: per-edge-type reverse traversal ────────────────────
        client = self.graph_client
        out: list[dict] = []
        for rev_edge in self._RING_REVERSE_EDGES:
            try:
                nbrs = client.get_neighbors(
                    ring_id, vertex_type="FraudRing", edge_type=rev_edge, limit=20,
                )
            except Exception:
                continue
            forward = rev_edge.replace("reverse_", "").upper()
            for block in nbrs.get("results", []):
                if isinstance(block, dict) and "neighbors" in block:
                    for n in block["neighbors"]:
                        n_id = n.get("v_id", "")
                        if not n_id or n_id == exclude_id:
                            continue
                        out.append({
                            "v_id":   n_id,
                            "type":   n.get("type", ""),
                            "name":   n.get("name") or n_id,
                            "edge":   forward,
                            "depth":  depth,
                            "risk_score": n.get("risk_score"),
                            "source": "ring_reverse" if depth == 1 else "co_ring",
                            "via":    ring_id,
                        })
        return out

    @staticmethod
    def _format_installed_ring_result(
        qr: list, ring_id: str, exclude_id: str, depth: int,
    ) -> list[dict]:
        """Format the response from tg_ring_members into the engine's context shape."""
        type_map = {
            "PersonMembers":      "PERSON_MEMBER_OF_RING",
            "CompanyMembers":     "COMPANY_MEMBER_OF_RING",
            "AccountMembers":     "ACCOUNT_MEMBER_OF_RING",
            "TransactionMembers": "TRANSACTION_MEMBER_OF_RING",
        }
        out: list[dict] = []
        for block in qr:
            if not isinstance(block, dict):
                continue
            for set_name, edge in type_map.items():
                members = block.get(set_name, [])
                if not isinstance(members, list):
                    continue
                for m in members:
                    n_id = m.get("v_id", "")
                    if not n_id or n_id == exclude_id:
                        continue
                    attrs = m.get("attributes", {}) or {}
                    out.append({
                        "v_id":   n_id,
                        "type":   m.get("v_type") or m.get("type", ""),
                        "name":   attrs.get("name") or n_id,
                        "edge":   edge,
                        "depth":  depth,
                        "risk_score": attrs.get("risk_score"),
                        "source": "tg_ring_members" if depth == 1 else "co_ring",
                        "via":    ring_id,
                    })
        return out

    def _detect_strategy(self, query: str) -> str:
        q = query.lower()
        if any(k in q for k in ["path", "route", "between", "connect", "link", "chain"]):
            return "path"
        if any(k in q for k in ["temporal", "spike", "burst", "when", "time", "date"]):
            return "temporal"
        if any(k in q for k in ["cluster", "community", "ring", "shell", "group"]):
            return "community"
        if any(k in q for k in ["neighbor", "around", "related", "connected"]):
            return "neighborhood"
        return "entity"

    def _find_relevant_paths(self, query: str, entities: list[dict]) -> list[dict]:
        """Surface real multi-hop paths between *distinct* surfaced entities.

        Iterates ordered pairs of the top suspects and asks the path retriever
        (fast path: installed tg_shortest_path; slow path: in-Python BFS) for
        a connection. Empty or self-pair results are skipped so the report's
        traversal_paths section only carries meaningful structural ties.
        """
        seeds = [e.get("v_id", "") for e in entities[:4] if e.get("v_id")]
        if len(seeds) < 2:
            return []
        paths: list[dict] = []
        seen_pairs: set[tuple[str, str]] = set()
        for i, from_id in enumerate(seeds):
            for to_id in seeds[i + 1:]:
                if from_id == to_id:
                    continue
                pair = (from_id, to_id) if from_id < to_id else (to_id, from_id)
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                try:
                    path = self.path_retriever.find_path(from_id, to_id, max_hops=3)
                except Exception:
                    path = None
                if path and path.path_length > 0:
                    paths.append({
                        "from":   from_id,
                        "to":     to_id,
                        "length": path.path_length,
                    })
                    if len(paths) >= 6:
                        return paths
        return paths

    def _compress(
        self,
        retrieval_result: dict,
        query: str,
        compression: str,
    ) -> dict:
        """Compress retrieval results using GraphAwareSummarizer (max 250 tokens)."""
        evidence_chain = self.evidence_builder.build_chain(retrieval_result, query)

        if compression == "llm" and self.llm_summarizer:
            summary = self.llm_summarizer.summarize(retrieval_result, query)
            return {"summary": summary, "type": "llm", "compression": compression, "evidence_count": len(evidence_chain)}
        else:
            compressed = self.rule_summarizer.compress_retrieval(retrieval_result, budget_tokens=250)
            compressed["type"] = "compressed"
            compressed["evidence_count"] = len(evidence_chain)
            return compressed

    def _build_profiles(self, entity_ids: list[str]) -> list[dict]:
        profiles = []
        for eid in entity_ids:
            profile = self.entity_retriever.get_entity_profile(eid)
            if profile.get("attributes"):
                profiles.append(profile)
        return profiles

    def prewarm(self, top_n: int = 30) -> dict:
        """
        Warm the GraphClient + topology caches with top-N highest-risk entities
        per type + all FraudRing vertices. Call BEFORE the first query to drive
        first-query latency from 15-25s down to <5s.

        Returns a dict of stats ({candidates, neighbors_warmed, topo_warmed, ms}).
        """
        import time as _t
        t0 = _t.perf_counter()
        client = self.graph_client
        if getattr(client, "_offline_mode", False):
            return {"warmed": 0, "reason": "offline_mode"}

        conn = client._tg_conn
        if conn is None:
            return {"warmed": 0, "reason": "no_conn"}

        candidates: list[tuple[str, str]] = []
        for vtype in ("Person", "Company", "Account"):
            try:
                vs = conn.getVertices(vtype, limit=top_n)
            except Exception:
                continue
            vs.sort(
                key=lambda v: float((v.get("attributes") or {}).get("risk_score") or 0),
                reverse=True,
            )
            for v in vs:
                if v.get("v_id"):
                    candidates.append((v["v_id"], vtype))
        try:
            for r in conn.getVertices("FraudRing", limit=50):
                if r.get("v_id"):
                    candidates.append((r["v_id"], "FraudRing"))
        except Exception:
            pass

        n_neighbors = 0
        for v_id, vtype in candidates:
            try:
                client.get_neighbors(v_id, vertex_type=vtype, limit=50)
                n_neighbors += 1
            except Exception:
                pass

        n_topo = 0
        for v_id, vtype in candidates:
            if vtype == "FraudRing":
                continue
            try:
                self.entity_retriever._compute_topology_features(v_id, vtype)
                n_topo += 1
            except Exception:
                pass

        return {
            "candidates":      len(candidates),
            "neighbors_warmed": n_neighbors,
            "topo_warmed":     n_topo,
            "ms":              round((_t.perf_counter() - t0) * 1000, 1),
        }

    def health_check(self) -> dict:
        """Check if engine is healthy."""
        health = {"client": False, "retrievers": False, "summarizers": False}

        try:
            health["client"] = self.graph_client.health_check().get("restpp", False)
        except Exception:
            pass

        health["retrievers"] = True
        health["summarizers"] = True

        health["healthy"] = health["client"] and health["retrievers"]
        return health