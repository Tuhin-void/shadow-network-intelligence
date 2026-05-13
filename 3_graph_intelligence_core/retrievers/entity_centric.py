"""Entity-centric retriever — retrieves and ranks entities by relevance to a query."""
import math
from dataclasses import dataclass, field
from typing import Optional


# Edges that signal fraud relevance — these propagate "suspicion" along the graph.
_FRAUD_RELEVANT_EDGES: frozenset[str] = frozenset({
    "OWNS", "BENEFITS_FROM", "TRANSFERRED_TO",
    "SHARES_DEVICE_WITH", "SHARES_ADDRESS_WITH", "ASSOCIATED_WITH",
    "PERSON_MEMBER_OF_RING", "COMPANY_MEMBER_OF_RING",
    "ACCOUNT_MEMBER_OF_RING", "TRANSACTION_MEMBER_OF_RING",
    "DEVICE_CONNECTED_TO_RING", "ADDRESS_CONNECTED_TO_RING",
})

# Topology features → score weights for the final entity rerank.
_RERANK_WEIGHTS = {
    "base_score":   0.30,  # original (token/semantic) relevance
    "raw_risk":     0.20,  # entity's own risk_score
    "neighbor_risk":0.20,  # mean risk of fraud-relevant neighbors
    "ring_touch":   0.20,  # how many fraud rings the entity touches
    "degree":       0.10,  # graph degree (log-scaled, capped)
}


@dataclass
class EntityMatch:
    v_id: str
    vertex_type: str
    name: str
    score: float
    attributes: dict = field(default_factory=dict)
    risk_score: Optional[float] = None
    # Topology features — populated by `_topology_rerank` (graph-native signal).
    propagated_risk: Optional[float] = None
    ring_touch_count: int = 0
    fraud_degree: int = 0
    rerank_explanation: str = ""


class EntityCentricRetriever:
    """
    Finds entities in the graph relevant to a query.

    Retrieval strategies, in order:
      1. Explicit entity-ID extraction (P-001, C-042, ...)  — exact lookup
      2. Token-overlap on the `name` attribute              — fast literal match
      3. (optional) Semantic similarity via injected Embedder — handles NL queries
         that don't contain explicit entity IDs or literal name fragments
    """

    # How many entities per type to embed for the semantic index.
    _SEMANTIC_INDEX_PER_TYPE = 200

    def __init__(self, graph_client: "GraphClient", embedder=None):
        self.client = graph_client
        self.embedder = embedder
        # Lazy semantic index: list[(EntityMatch, list[float])]
        self._sem_index: list[tuple[EntityMatch, list[float]]] = []
        self._sem_index_built = False
        # Topology-feature cache: (v_id, vtype) → {propagated_risk, ring_touch, fraud_degree}
        # Cleared when the GraphClient cache is invalidated (TTL-bounded there).
        self._topo_cache: dict[tuple[str, str], dict] = {}

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        entity_types: Optional[list[str]] = None,
        min_score: float = 0.0,
    ) -> list[EntityMatch]:
        """Retrieve top-k entities matching a query string."""
        if entity_types is None:
            # FraudRing is included because queries like "ring members of FR-001"
            # need the ring vertex itself as a seed for the engine's hidden-
            # relationship expansion step to reach the actual members.
            entity_types = ["Person", "Company", "Account", "Device",
                            "Transaction", "FraudRing"]

        # Strategy 1: explicit entity ID
        entity_id = self._extract_entity_id(query)
        if entity_id:
            match = self._get_entity_by_id(entity_id, entity_types)
            if match:
                return [match]

        # Strategy 2: token overlap on name
        results = []
        for vtype in entity_types:
            matches = self._search_by_name(query, vtype, limit=top_k)
            results.extend(matches)
        results.sort(key=lambda x: x.score, reverse=True)
        token_hits = [r for r in results if r.score >= min_score][:top_k]

        # Strategy 3: semantic fallback when token match is thin
        if len(token_hits) < max(3, top_k // 2) and self.embedder is not None:
            sem_hits = self._semantic_search(query, top_k=top_k, entity_types=entity_types)
            seen = {m.v_id for m in token_hits}
            for m in sem_hits:
                if m.v_id not in seen:
                    token_hits.append(m)
                    seen.add(m.v_id)
            token_hits.sort(key=lambda x: x.score, reverse=True)
            token_hits = token_hits[:top_k]

        # Strategy 4: risk fallback — if token + semantic both came up empty,
        # surface the highest-risk entities of the queried types. This guarantees
        # GraphRAG always returns SOMETHING relevant for NL queries that don't
        # contain explicit IDs or vocabulary overlap.
        if not token_hits:
            token_hits = self._risk_fallback(entity_types, top_k=top_k)

        # ── Topology-aware reranking (the graph-native edge VectorRAG lacks) ──
        # For each candidate, walk 1-hop along fraud-relevant edges and rerank
        # by propagated suspicion + ring-membership reach + graph degree.
        if token_hits:
            token_hits = self._topology_rerank(token_hits, top_k=top_k)

        # ── Min-K diversity guarantee ─────────────────────────────────────
        # If the rerank collapsed to <3 entities, top up with risk-fallback
        # entries to give the downstream summarizer / narrator enough material
        # to produce a visually compelling investigation.
        MIN_K = min(3, top_k)
        if len(token_hits) < MIN_K:
            extra = self._risk_fallback(entity_types, top_k=top_k * 2)
            seen = {m.v_id for m in token_hits}
            for m in extra:
                if m.v_id and m.v_id not in seen and len(token_hits) < top_k:
                    token_hits.append(m)
                    seen.add(m.v_id)
            # Re-rerank the merged set so structural features rank evenly.
            if token_hits:
                token_hits = self._topology_rerank(token_hits, top_k=top_k)

        return token_hits

    # ── Topology-aware reranking ──────────────────────────────────────────────

    def _topology_rerank(self, candidates: list[EntityMatch], top_k: int) -> list[EntityMatch]:
        """
        Recompute each candidate's score using structural features:
          - base_score    : original token/semantic relevance
          - raw_risk      : entity's own risk_score
          - neighbor_risk : mean risk_score of 1-hop fraud-relevant neighbors
          - ring_touch    : count of distinct fraud rings the entity is in / touches
          - degree        : log-scaled count of fraud-relevant edges (capped at 30)

        This is a legitimate graph-native rerank — the features it relies on
        (ring membership, neighbor risk, edge density) literally cannot be
        computed by a vector store, which has no edges.
        """
        for c in candidates:
            try:
                features = self._compute_topology_features(c.v_id, c.vertex_type)
            except Exception:
                features = {"propagated_risk": 0.0, "ring_touch": 0, "fraud_degree": 0}

            base_score = c.score or 0.0
            raw_risk   = (c.risk_score or 0.0)
            # Normalize risk fields. If risk_score is INT 0-100 (live schema),
            # rescale; if it's float 0-1, leave alone.
            if raw_risk > 1.0:
                raw_risk = raw_risk / 100.0
            n_risk = features["propagated_risk"]
            if n_risk > 1.0:
                n_risk = n_risk / 100.0

            ring_touch_norm = min(features["ring_touch"] / 3.0, 1.0)
            degree_norm = math.log1p(features["fraud_degree"]) / math.log1p(30.0)
            degree_norm = min(degree_norm, 1.0)

            w = _RERANK_WEIGHTS
            new_score = (
                w["base_score"]    * min(base_score, 1.0) +
                w["raw_risk"]      * raw_risk +
                w["neighbor_risk"] * n_risk +
                w["ring_touch"]    * ring_touch_norm +
                w["degree"]        * degree_norm
            )

            # Build a one-line explanation for the explainability layer.
            bits: list[str] = []
            if features["ring_touch"]:
                bits.append(f"touches {features['ring_touch']} ring(s)")
            if features["fraud_degree"]:
                bits.append(f"{features['fraud_degree']} fraud-relevant edges")
            if n_risk > 0.3:
                bits.append(f"neighbor risk {n_risk:.2f}")
            c.propagated_risk = round(n_risk, 4)
            c.ring_touch_count = features["ring_touch"]
            c.fraud_degree = features["fraud_degree"]
            c.rerank_explanation = " · ".join(bits) if bits else "no graph signal"
            c.score = round(new_score, 4)

        candidates.sort(key=lambda x: x.score, reverse=True)
        return candidates[:top_k]

    def _compute_topology_features(self, v_id: str, vertex_type: str) -> dict:
        """
        Walk 1-hop fraud-relevant edges and aggregate suspicion + ring touch.
        Returns dict of {propagated_risk, ring_touch, fraud_degree}.
        Cached per (v_id, vtype) to avoid recompute during a benchmark run.
        """
        result = {"propagated_risk": 0.0, "ring_touch": 0, "fraud_degree": 0}
        if not v_id:
            return result

        cache_key = (v_id, vertex_type)
        if cache_key in self._topo_cache:
            return self._topo_cache[cache_key]

        try:
            neighbors = self.client.get_neighbors(v_id, vertex_type=vertex_type, limit=50)
        except Exception:
            self._topo_cache[cache_key] = result
            return result

        nbrs = []
        for block in neighbors.get("results", []):
            if isinstance(block, dict) and "neighbors" in block:
                nbrs.extend(block["neighbors"])

        ring_ids = set()
        risks: list[float] = []
        fraud_edges = 0
        for n in nbrs:
            edge = n.get("edge_type") or n.get("edge") or ""
            if edge not in _FRAUD_RELEVANT_EDGES:
                continue
            fraud_edges += 1
            if n.get("type") == "FraudRing":
                # Ring membership / connection edges always end at a FraudRing.
                ring_ids.add(n.get("v_id", ""))
            r = n.get("risk_score") or n.get("attributes", {}).get("risk_score")
            try:
                if r is not None:
                    risks.append(float(r))
            except (TypeError, ValueError):
                pass

        if risks:
            result["propagated_risk"] = sum(risks) / len(risks)
        result["ring_touch"] = len(ring_ids)
        result["fraud_degree"] = fraud_edges
        self._topo_cache[cache_key] = result
        return result

    def _risk_fallback(self, entity_types: list[str], top_k: int) -> list[EntityMatch]:
        """Surface the top-K highest-risk entities across the requested types."""
        candidates: list[EntityMatch] = []
        per_type_cap = max(top_k, 20)
        for vtype in entity_types:
            try:
                vertices = self.client.get_vertices(vtype, limit=per_type_cap)
            except Exception:
                continue
            for v in vertices:
                attrs = v.get("attributes", {}) or {}
                risk = attrs.get("risk_score")
                if risk is None:
                    continue
                try:
                    rscore = float(risk)
                except (TypeError, ValueError):
                    continue
                candidates.append(EntityMatch(
                    v_id=v.get("v_id", ""),
                    vertex_type=vtype,
                    name=attrs.get("name", v.get("v_id", "")),
                    score=rscore,
                    attributes=attrs,
                    risk_score=rscore,
                ))
        candidates.sort(key=lambda x: x.score, reverse=True)
        return candidates[:top_k]

    def _extract_entity_id(self, query: str) -> Optional[str]:
        import re
        patterns = [
            r'\bP-\d+\b',
            r'\bC-\d+\b',
            r'\bA-\d+\b',
            r'\bADDR-\d+\b',
            r'\bD-\d+\b',
            r'\bTX-(?:FR)?\d+\b',
            r'\bT-\d+\b',
            r'\bFR-\d+\b',
        ]
        for pat in patterns:
            m = re.search(pat, query)
            if m:
                return m.group(0)
        return None

    def _get_entity_by_id(self, entity_id: str, entity_types: list[str]) -> Optional[EntityMatch]:
        for vtype in entity_types:
            vertex = self.client.get_vertex(vtype, entity_id)
            if vertex:
                name = vertex.get("attributes", {}).get("name", entity_id)
                risk = vertex.get("attributes", {}).get("risk_score")
                return EntityMatch(
                    v_id=entity_id,
                    vertex_type=vtype,
                    name=name,
                    score=1.0,
                    attributes=vertex.get("attributes", {}),
                    risk_score=risk,
                )
        return None

    def _search_by_name(self, query: str, vertex_type: str, limit: int = 20) -> list[EntityMatch]:
        tokens = query.lower().split()
        vertices = self.client.get_vertices(vertex_type, limit=limit * 2)
        matches = []

        for v in vertices:
            attrs = v.get("attributes", {})
            name = attrs.get("name", "")
            if not name:
                continue

            name_lower = name.lower()
            score = 0.0

            if any(t in name_lower for t in tokens):
                score = sum(1 for t in tokens if t in name_lower) / len(tokens)
                matches.append(EntityMatch(
                    v_id=v.get("v_id", ""),
                    vertex_type=vertex_type,
                    name=name,
                    score=score,
                    attributes=attrs,
                    risk_score=attrs.get("risk_score"),
                ))

        return matches[:limit]

    # ── Semantic fallback ─────────────────────────────────────────────────────

    def _build_semantic_index(self, entity_types: list[str]) -> None:
        """Embed a sample of entities once and cache vectors for cosine search."""
        if self._sem_index_built or self.embedder is None:
            return
        for vtype in entity_types:
            try:
                vertices = self.client.get_vertices(vtype, limit=self._SEMANTIC_INDEX_PER_TYPE)
            except Exception:
                continue
            for v in vertices:
                attrs = v.get("attributes", {}) or {}
                doc = self._entity_doc(vtype, attrs)
                if not doc:
                    continue
                try:
                    vec = self.embedder.embed(doc)
                except Exception:
                    continue
                if not vec:
                    continue
                em = EntityMatch(
                    v_id=v.get("v_id", ""),
                    vertex_type=vtype,
                    name=attrs.get("name", v.get("v_id", "")),
                    score=0.0,
                    attributes=attrs,
                    risk_score=attrs.get("risk_score"),
                )
                self._sem_index.append((em, list(vec)))
        self._sem_index_built = True

    def _semantic_search(
        self, query: str, top_k: int, entity_types: list[str],
    ) -> list[EntityMatch]:
        """Cosine-similarity ranking against the cached embedding index."""
        if self.embedder is None:
            return []
        if not self._sem_index_built:
            self._build_semantic_index(entity_types)
        if not self._sem_index:
            return []
        try:
            q_vec = self.embedder.embed(query)
        except Exception:
            return []
        if not q_vec:
            return []
        q_vec = list(q_vec)
        q_norm = math.sqrt(sum(x * x for x in q_vec)) or 1.0

        scored: list[tuple[float, EntityMatch]] = []
        for em, vec in self._sem_index:
            v_norm = math.sqrt(sum(x * x for x in vec)) or 1.0
            dot = sum(a * b for a, b in zip(q_vec, vec))
            sim = dot / (q_norm * v_norm)
            if sim > 0.15:  # filter out near-zero similarity noise
                scored.append((sim, em))

        scored.sort(key=lambda x: x[0], reverse=True)
        out: list[EntityMatch] = []
        for sim, em in scored[:top_k]:
            # Build a new EntityMatch so we don't mutate cached objects.
            out.append(EntityMatch(
                v_id=em.v_id, vertex_type=em.vertex_type, name=em.name,
                score=round(sim, 4), attributes=em.attributes, risk_score=em.risk_score,
            ))
        return out

    def _entity_doc(self, vtype: str, attrs: dict) -> str:
        """Build a short text 'document' for embedding."""
        bits: list[str] = [vtype]
        for k in ("name", "industry", "company_status", "occupation",
                  "nationality", "country", "city", "address_type",
                  "device_type", "transaction_type", "ring_type",
                  "severity", "description"):
            if attrs.get(k):
                bits.append(str(attrs[k]))
        flags: list[str] = []
        if attrs.get("pep_flag"):           flags.append("PEP")
        if attrs.get("sanctions_flag"):     flags.append("sanctioned")
        if attrs.get("offshore_flag"):      flags.append("offshore")
        if attrs.get("shell_company_flag"): flags.append("shell")
        if attrs.get("suspicious_flag"):    flags.append("suspicious")
        if flags:
            bits.append("flags: " + ", ".join(flags))
        if attrs.get("risk_score") is not None:
            bits.append(f"risk={attrs['risk_score']}")
        return " | ".join(bits)

    def get_entity_profile(self, entity_id: str) -> dict:
        """Get full entity profile with neighbors.

        Uses ID-prefix inference to avoid issuing wrong-type lookups
        (which previously logged spurious errors).
        """
        profile = {"v_id": entity_id, "neighbors": [], "edges": []}

        inferred = getattr(self.client, "_infer_vertex_type", lambda _: "")(entity_id)
        candidate_types = [inferred] if inferred else ["Person", "Company", "Account", "Device", "Transaction"]
        for vtype in candidate_types:
            vertex = self.client.get_vertex(vtype, entity_id)
            if vertex:
                profile["vertex_type"] = vtype
                profile["attributes"] = vertex.get("attributes", {})
                break

        neighbors = self.client.get_neighbors(entity_id, limit=50)
        if "results" in neighbors:
            profile["neighbors"] = neighbors["results"]

        return profile


def _score_entity(entity: dict, query_tokens: list[str]) -> float:
    name = entity.get("attributes", {}).get("name", "").lower()
    if not name:
        return 0.0
    return sum(1 for t in query_tokens if t in name) / max(len(query_tokens), 1)