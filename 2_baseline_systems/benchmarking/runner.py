"""
Benchmark runner - executes full benchmark across all 3 pipelines.
"""
import json
import time
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional
from ..shared.schemas import BenchmarkRun, PipelineResult
from ..shared.data_loader import AdaptiveDataLoader
from ..shared.embedder import Embedder
from ..shared.llm_client import LLMClient
from ..shared.token_tracker import TokenTracker
from ..shared.document_builder import DocumentBuilder
from ..retrieval import VectorStore, RetrievalCache
from .query_loader import QueryLoader
from .difficulty_tiers import DifficultyTierClassifier
from ..pipelines import PureLLMPipeline, VectorRAGPipeline, GraphRAGPipeline

logger = logging.getLogger(__name__)


class BenchmarkRunner:
    def __init__(
        self,
        profile: str = "hackathon_default",
        data_loader: Optional[AdaptiveDataLoader] = None,
        config: Optional[dict] = None,
    ):
        self.profile = profile
        self.config = config or {}
        self.data_loader = data_loader or AdaptiveDataLoader(profile=profile)
        self.output_dir = Path(__file__).parent.parent / "outputs" / "benchmark_results"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.embedder = Embedder(
            provider=self.config.get("embedder_provider", "mock"),
            model=self.config.get("embedder_model", "nomic-embed-text"),
            base_url=self.config.get("ollama_base_url", "http://localhost:11434"),
        )
        self.llm = LLMClient(
            provider=self.config.get("llm_provider", "mock"),
            model=self.config.get("llm_model", "llama3.2"),
            base_url=self.config.get("ollama_base_url", "http://localhost:11434"),
            api_key=self.config.get("openai_api_key", ""),
        )
        self.tokens = TokenTracker(model=self.config.get("llm_model", "llama3.2"))
        self.vector_store = VectorStore(
            provider=self.config.get("vector_provider", "mock"),
            collection_name=f"shadow_network_{profile}",
            dimension=self.embedder.dimension,
        )
        self.cache = RetrievalCache(max_size=self.config.get("retrieval_cache_size", 1000))
        self.query_loader = QueryLoader(self.data_loader)
        self.tier_classifier = DifficultyTierClassifier()

        self._pipelines: dict = {}

    def _init_pipelines(self) -> dict:
        if not self._pipelines:
            graph_provider = self.config.get("graph_provider", "mock")

            graph_retriever = None
            if graph_provider == "tigergraph":
                import sys as _sys
                _sys.path.insert(0, str(Path(__file__).parent.parent.parent / "3_graph_intelligence_core"))
                from configs.config import get_config
                from clients.graph_client import GraphClient
                from adapters.tigergraph_adapter import create_adapter

                config = get_config()
                loader = AdaptiveDataLoader(self.config.get("profile", "small"))
                dataset = loader.load()
                graph_client = GraphClient(config, dataset=dataset)
                graph_retriever = create_adapter(graph_client)

            self._pipelines = {
                "pure_llm": PureLLMPipeline(
                    self.llm, self.tokens, self.data_loader,
                ),
                "vector_rag": VectorRAGPipeline(
                    self.llm, self.tokens, self.data_loader,
                    self.vector_store, self.embedder,
                    top_k=self.config.get("top_k", 10),
                    chunk_size=self.config.get("chunk_size", 500),
                ),
                "graph_rag": GraphRAGPipeline(
                    self.llm, self.tokens, self.data_loader,
                    graph_retriever=graph_retriever,
                    embedder=self.embedder,
                    traversal_depth=2,
                    top_k=self.config.get("top_k", 10),
                ),
            }
        return self._pipelines

    def run(
        self,
        queries: list,
        approaches: list[str] = None,
        output_dir: Optional[Path] = None,
        run_id: Optional[str] = None,
        parallel: bool = True,
        max_workers: int = 3,
        limit: int = 0,
    ) -> BenchmarkRun:
        flat_approaches = []
        for a in (approaches or ["pure_llm", "vector_rag", "graph_rag"]):
            if "," in a:
                flat_approaches.extend(x.strip() for x in a.split(",") if x.strip())
            else:
                flat_approaches.append(a)
        approaches = flat_approaches
        pipelines = self._init_pipelines()
        out_dir = output_dir or self.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        run_id = run_id or self._generate_run_id()
        timestamp = datetime.now()

        dataset = self.data_loader.load()
        dataset_hash = self._compute_hash(dataset)

        queries_to_run = queries[:limit] if limit > 0 else queries
        logger.info(f"Running benchmark: run_id={run_id}, queries={len(queries_to_run)}, "
                    f"approaches={approaches}, parallel={parallel}")

        results_by_approach: dict = {a: [] for a in approaches}
        total_start = time.time()

        for i, query in enumerate(queries_to_run):
            logger.info(f"[{i+1}/{len(queries_to_run)}] Query: {query.id} (tier {query.tier})")

            if parallel:
                futures = {}
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    for approach in approaches:
                        if approach in pipelines:
                            fut = executor.submit(pipelines[approach].answer, query.question)
                            futures[fut] = (approach, query)
                    for fut in as_completed(futures):
                        approach, q = futures[fut]
                        try:
                            result = fut.result()
                            result.query_id = query.id
                            results_by_approach[approach].append(result)
                        except Exception as e:
                            logger.error(f"{approach} error on {query.id}: {e}")
            else:
                for approach in approaches:
                    if approach not in pipelines:
                        continue
                    try:
                        result = pipelines[approach].answer(query.question)
                        result.query_id = query.id
                        results_by_approach[approach].append(result)
                    except Exception as e:
                        logger.error(f"{approach} error on {query.id}: {e}")

        total_time = (time.time() - total_start) * 1000

        benchmark_run = BenchmarkRun(
            run_id=run_id,
            timestamp=timestamp,
            config=self._sanitize_config(),
            dataset_hash=dataset_hash,
            profile=self.profile,
            queries_loaded=len(queries),
            queries_run=len(queries_to_run),
            results={
                a: [r.to_dict() for r in results]
                for a, results in results_by_approach.items()
            },
        )

        output_file = out_dir / f"benchmark_{run_id}.json"
        with open(output_file, "w") as f:
            json.dump(benchmark_run.to_dict(), f, indent=2, default=str)
        logger.info(f"Results saved to {output_file}")

        self._print_summary(results_by_approach, total_time)

        return benchmark_run

    def run_cli(
        self,
        profile: str = "hackathon_default",
        tier: Optional[int] = None,
        approaches: Optional[list[str]] = None,
        limit: int = 0,
        output_dir: Optional[str] = None,
        regenerate: bool = False,
    ) -> BenchmarkRun:
        queries = self.query_loader.load_queries(tier=tier)
        return self.run(
            queries=queries,
            approaches=approaches,
            output_dir=Path(output_dir) if output_dir else None,
            limit=limit,
        )

    def _generate_run_id(self) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_hash = hashlib.md5(str(time.time()).encode()).hexdigest()[:6]
        return f"RUN_{ts}_{short_hash}"

    def _compute_hash(self, dataset) -> str:
        parts = [
            str(len(getattr(dataset, "persons", []))),
            str(len(getattr(dataset, "edges", []))),
            str(len(getattr(dataset, "fraud_rings", []))),
        ]
        combined = "|".join(parts)
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    def _sanitize_config(self) -> dict:
        safe = dict(self.config)
        for key in ("openai_api_key", "anthropic_api_key", "tigergraph_password"):
            if key in safe:
                safe[key] = "***"
        return safe

    def _print_summary(self, results_by_approach: dict, total_time: float) -> None:
        print("\n" + "=" * 70)
        print("BENCHMARK RESULTS SUMMARY")
        print("=" * 70)
        for approach, results in results_by_approach.items():
            if not results:
                continue
            total_tokens = sum(r.total_tokens for r in results)
            total_latency = sum(r.latency_ms for r in results)
            total_cost = sum(r.cost_estimate for r in results)
            errors = sum(1 for r in results if r.error)
            print(f"\n{approach.upper()}:")
            print(f"  Queries:    {len(results)}")
            print(f"  Avg Tokens: {total_tokens / len(results):.0f}")
            print(f"  Avg Latency: {total_latency / len(results):.0f}ms")
            print(f"  Total Cost: ${total_cost:.6f}")
            print(f"  Errors:     {errors}")
        print(f"\nTotal Time: {total_time:.0f}ms")
        print("=" * 70)