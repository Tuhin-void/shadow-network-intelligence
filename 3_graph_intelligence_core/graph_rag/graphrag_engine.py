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
    ):
        from configs.config import Config, get_config
        if config is None:
            config = get_config()
        elif not isinstance(config, Config):
            config = get_config(config if isinstance(config, str) else None)

        self.config = config
        self.compression = compression
        self.graph_client = graph_client

        self._init_retrievers()
        self._init_summarizers()

    def _init_retrievers(self) -> None:
        from retrievers.entity_centric import EntityCentricRetriever
        from retrievers.neighborhood import NeighborhoodRetriever
        from retrievers.path_aware import PathAwareRetriever
        from retrievers.community import CommunityRetriever
        from retrievers.temporal import TemporalRetriever
        from retrievers.hybrid import HybridRetriever

        self.entity_retriever = EntityCentricRetriever(self.graph_client)
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
        """Execute graph retrieval based on strategy."""
        if strategy == "auto":
            strategy = self._detect_strategy(query)

        result = {"strategy": strategy, "entities": [], "context": [], "paths": [], "communities": []}

        if strategy in ("auto", "entity"):
            entities = self.entity_retriever.retrieve(query, top_k=top_k)
            result["entities"] = [
                {"v_id": e.v_id, "type": e.vertex_type, "name": e.name, "score": e.score, "risk_score": e.risk_score, "attributes": e.attributes}
                for e in entities
            ]

        if strategy in ("auto", "neighborhood", "full"):
            seed_ids = [e["v_id"] for e in result.get("entities", [])]
            if seed_ids:
                neighborhood = self.neighborhood_retriever.retrieve(seed_ids, max_hops=depth)
                result["context"] = [
                    {"v_id": n.v_id, "type": n.vertex_type, "name": n.name, "edge": n.edge_type, "depth": n.depth, "risk_score": n.risk_score}
                    for n in neighborhood.get("nodes", [])
                ]

        if strategy in ("auto", "path", "full"):
            path_result = self._find_relevant_paths(query, result.get("entities", []))
            result["paths"] = path_result

        if strategy in ("auto", "community", "full"):
            high_risk = self.community_retriever.detect_high_risk_cluster(min_risk=0.7, limit=top_k)
            result["communities"] = high_risk

        return result

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
        paths = []
        for e in entities[:3]:
            vid = e.get("v_id", "")
            if vid:
                path = self.path_retriever.find_path(vid, vid, max_hops=3)
                if path:
                    paths.append({"from": vid, "to": vid, "length": path.path_length})
        return paths

    def _compress(
        self,
        retrieval_result: dict,
        query: str,
        compression: str,
    ) -> dict:
        """Compress retrieval results."""
        if compression == "llm" and self.llm_summarizer:
            summary = self.llm_summarizer.summarize(retrieval_result, query)
            return {"summary": summary, "type": "llm", "compression": compression}
        else:
            return self.rule_summarizer.compress_retrieval(retrieval_result, budget_tokens=2000)

    def _build_profiles(self, entity_ids: list[str]) -> list[dict]:
        profiles = []
        for eid in entity_ids:
            profile = self.entity_retriever.get_entity_profile(eid)
            if profile.get("attributes"):
                profiles.append(profile)
        return profiles

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