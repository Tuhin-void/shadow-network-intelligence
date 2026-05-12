"""
Central benchmark orchestrator.
"""
import logging
from typing import Optional, Callable, Iterator
from ..shared.data_loader import AdaptiveDataLoader
from ..shared.embedder import Embedder
from ..shared.llm_client import LLMClient
from ..shared.token_tracker import TokenTracker
from ..retrieval import VectorStore
from ..benchmarking import QueryLoader, DifficultyTierClassifier, BenchmarkRunner
from ..pipelines import PureLLMPipeline, VectorRAGPipeline, GraphRAGPipeline

logger = logging.getLogger(__name__)


class BenchmarkOrchestrator:
    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.profile = self.config.get("profile", "hackathon_default")
        self.data_loader = AdaptiveDataLoader(profile=self.profile)
        self.embedder = Embedder(
            provider=self.config.get("embedder_provider", "ollama"),
            model=self.config.get("embedder_model", "nomic-embed-text"),
            base_url=self.config.get("ollama_base_url", "http://localhost:11434"),
        )
        self.llm = LLMClient(
            provider=self.config.get("llm_provider", "ollama"),
            model=self.config.get("llm_model", "llama3.2"),
            base_url=self.config.get("ollama_base_url", "http://localhost:11434"),
            api_key=self.config.get("openai_api_key", ""),
        )
        self.tokens = TokenTracker(model=self.config.get("llm_model", "llama3.2"))
        self.vector_store = VectorStore(
            collection_name=f"shadow_network_{self.profile}",
            dimension=self.embedder.dimension,
        )
        self.query_loader = QueryLoader(self.data_loader)
        self.tier_classifier = DifficultyTierClassifier()
        self._pipelines: dict = {}
        self._warm = False

    def _init_pipelines(self) -> dict:
        if not self._pipelines:
            self._pipelines = {
                "pure_llm": PureLLMPipeline(self.llm, self.tokens, self.data_loader),
                "vector_rag": VectorRAGPipeline(
                    self.llm, self.tokens, self.data_loader,
                    self.vector_store, self.embedder,
                    top_k=self.config.get("top_k", 10),
                ),
                "graph_rag": GraphRAGPipeline(
                    self.llm, self.tokens, self.data_loader,
                    graph_retriever=None,
                    embedder=self.embedder,
                    traversal_depth=self.config.get("traversal_depth", 2),
                ),
            }
        return self._pipelines

    def warmup(self) -> None:
        if self._warm:
            return
        logger.info("Warming up pipelines...")
        self._init_pipelines()
        for name, pipeline in self._pipelines.items():
            try:
                pipeline.answer("What is the risk score of entity P-000001?")
                logger.info(f"  {name}: OK")
            except Exception as e:
                logger.warning(f"  {name}: warmup failed - {e}")
        self._warm = True

    def run_benchmark(
        self,
        tier: Optional[int] = None,
        approaches: Optional[list[str]] = None,
        output_dir: Optional[str] = None,
        parallel: bool = True,
        limit: int = 0,
    ):
        queries = self.query_loader.load_queries(tier=tier)

        if limit > 0:
            queries = queries[:limit]

        logger.info(f"Loaded {len(queries)} queries" + (f" (tier {tier})" if tier else ""))

        pipelines = self._init_pipelines()
        approaches = approaches or list(pipelines.keys())
        results_by_approach: dict = {a: [] for a in approaches}

        for i, query in enumerate(queries):
            logger.info(f"[{i+1}/{len(queries)}] {query.id} (tier {query.tier})")
            for approach in approaches:
                if approach not in pipelines:
                    continue
                try:
                    result = pipelines[approach].answer(query.question)
                    result.query_id = query.id
                    results_by_approach[approach].append(result)
                except Exception as e:
                    logger.error(f"  {approach} error: {e}")

        return self._build_run_result(results_by_approach, queries)

    def run_streaming(
        self,
        tier: Optional[int] = None,
        approaches: Optional[list[str]] = None,
    ) -> Iterator[dict]:
        queries = self.query_loader.load_queries(tier=tier)
        pipelines = self._init_pipelines()
        approaches = approaches or list(pipelines.keys())

        for i, query in enumerate(queries):
            query_results = {}
            for approach in approaches:
                if approach not in pipelines:
                    continue
                try:
                    result = pipelines[approach].answer(query.question)
                    query_results[approach] = result.to_dict()
                except Exception as e:
                    query_results[approach] = {"error": str(e)}
            yield {
                "query_index": i + 1,
                "query": query.to_dict(),
                "results": query_results,
            }

    def _build_run_result(self, results_by_approach: dict, queries: list) -> dict:
        summary = {}
        for approach, results in results_by_approach.items():
            if not results:
                continue
            tokens = [r.total_tokens for r in results]
            latencies = [r.latency_ms for r in results]
            costs = [r.cost_estimate for r in results]
            summary[approach] = {
                "count": len(results),
                "avg_tokens": sum(tokens) / len(tokens),
                "avg_latency_ms": sum(latencies) / len(latencies),
                "total_cost": sum(costs),
                "errors": sum(1 for r in results if r.error),
            }

        if "pure_llm" in summary and "vector_rag" in summary:
            pll_token = summary["pure_llm"]["avg_tokens"]
            vr_token = summary["vector_rag"]["avg_tokens"]
            if pll_token > 0:
                summary["vector_rag"]["token_reduction_pct"] = ((pll_token - vr_token) / pll_token) * 100

        if "vector_rag" in summary and "graphrag" in summary:
            vr_token = summary["vector_rag"]["avg_tokens"]
            gr_token = summary["graphrag"]["avg_tokens"]
            if vr_token > 0:
                summary["graphrag"]["token_reduction_pct"] = ((vr_token - gr_token) / vr_token) * 100

        return {
            "total_queries": len(queries),
            "profile": self.profile,
            "summary": summary,
        }