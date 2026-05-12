"""
Central configuration for 2_baseline_systems.
Environment-driven with multi-provider support.
"""
import os
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


def _get_env(key: str, default: str) -> str:
    return os.environ.get(key, default)


def _get_int(key: str, default: int) -> int:
    val = os.environ.get(key)
    return int(val) if val else default


def _get_float(key: str, default: float) -> float:
    val = os.environ.get(key)
    return float(val) if val else default


def _get_bool(key: str, default: bool) -> bool:
    val = os.environ.get(key)
    if not val:
        return default
    return val.lower() in ("true", "1", "yes", "on")


BASE_DIR = Path(__file__).parent.parent
DATA_ENGINE_DIR = BASE_DIR.parent / "1_data_engine"
PROJECT_ROOT = BASE_DIR.parent

CHROMA_PERSIST = BASE_DIR / "outputs" / "chromadb"
OUTPUT_DIR = BASE_DIR / "outputs"


@dataclass
class Config:
    profile: str = field(default_factory=lambda: _get_env("DATA_PROFILE", "hackathon_default"))
    seed: int = field(default_factory=lambda: _get_int("DATA_SEED", 42))

    embedder_provider: str = field(default_factory=lambda: _get_env("EMBEDDER_PROVIDER", "ollama"))
    embedder_model: str = field(default_factory=lambda: _get_env("EMBEDDER_MODEL", "nomic-embed-text"))

    llm_provider: str = field(default_factory=lambda: _get_env("LLM_PROVIDER", "ollama"))
    llm_model: str = field(default_factory=lambda: _get_env("LLM_MODEL", "llama3.2"))

    ollama_base_url: str = field(default_factory=lambda: _get_env("OLLAMA_BASE_URL", "http://localhost:11434"))
    openai_api_key: str = field(default_factory=lambda: _get_env("OPENAI_API_KEY", ""))
    anthropic_api_key: str = field(default_factory=lambda: _get_env("ANTHROPIC_API_KEY", ""))

    chromadb_persist_dir: Path = field(default_factory=lambda: Path(_get_env("CHROMADB_PERSIST_DIR", str(CHROMA_PERSIST))))
    chromadb_collection: str = field(default_factory=lambda: _get_env("CHROMADB_COLLECTION", "shadow_network"))

    tigergraph_host: str = field(default_factory=lambda: _get_env("TIGERGRAPH_HOST", "localhost"))
    tigergraph_port: int = field(default_factory=lambda: _get_int("TIGERGRAPH_PORT", 14240))
    tigergraph_graphname: str = field(default_factory=lambda: _get_env("TIGERGRAPH_GRAPH", "FinancialGraph"))
    tigergraph_user: str = field(default_factory=lambda: _get_env("TIGERGRAPH_USER", "tigergraph"))
    tigergraph_password: str = field(default_factory=lambda: _get_env("TIGERGRAPH_PASSWORD", "tigergraph"))

    top_k: int = field(default_factory=lambda: _get_int("TOP_K", 10))
    chunk_size: int = field(default_factory=lambda: _get_int("CHUNK_SIZE", 500))
    chunk_overlap: int = field(default_factory=lambda: _get_int("CHUNK_OVERLAP", 50))
    chunk_strategy: str = field(default_factory=lambda: _get_env("CHUNK_STRATEGY", "recursive"))
    reranker_enabled: bool = field(default_factory=lambda: _get_bool("RERANKER_ENABLED", False))

    max_tokens: int = field(default_factory=lambda: _get_int("MAX_TOKENS", 2048))
    temperature: float = field(default_factory=lambda: _get_float("TEMPERATURE", 0.0))
    timeout_seconds: int = field(default_factory=lambda: _get_int("TIMEOUT_SECONDS", 120))

    retrieval_cache_size: int = field(default_factory=lambda: _get_int("RETRIEVAL_CACHE_SIZE", 1000))
    embedding_cache_size: int = field(default_factory=lambda: _get_int("EMBEDDING_CACHE_SIZE", 5000))
    enable_caching: bool = field(default_factory=lambda: _get_bool("ENABLE_CACHING", True))

    parallel_execution: bool = field(default_factory=lambda: _get_bool("PARALLEL_EXECUTION", True))
    benchmark_limit: int = field(default_factory=lambda: _get_int("BENCHMARK_LIMIT", 0))

    data_engine_dir: Path = field(default_factory=lambda: Path(_get_env("DATA_ENGINE_DIR", str(DATA_ENGINE_DIR))))
    output_dir: Path = field(default_factory=lambda: Path(_get_env("OUTPUT_DIR", str(OUTPUT_DIR))))

    @property
    def embedding_dimension(self) -> int:
        if self.embedder_model.startswith("text-embedding-3"):
            return 1536
        if "nomic" in self.embedder_model:
            return 768
        return 384

    def ensure_dirs(self) -> None:
        self.chromadb_persist_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "benchmark_results").mkdir(parents=True, exist_ok=True)

    def validate(self) -> bool:
        if self.llm_provider == "openai" and not self.openai_api_key:
            logger.warning("OPENAI_API_KEY not set; OpenAI LLM will not work")
        if self.llm_provider == "anthropic" and not self.anthropic_api_key:
            logger.warning("ANTHROPIC_API_KEY not set; Anthropic LLM will not work")
        return True

    def summary(self) -> dict:
        return {
            "profile": self.profile,
            "seed": self.seed,
            "embedder": f"{self.embedder_provider}/{self.embedder_model}",
            "llm": f"{self.llm_provider}/{self.llm_model}",
            "top_k": self.top_k,
            "chunk_size": self.chunk_size,
            "cache_size": self.retrieval_cache_size,
            "output_dir": str(self.output_dir),
        }


_config: Optional[Config] = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
        _config.ensure_dirs()
        _config.validate()
    return _config


def reload_config() -> Config:
    global _config
    _config = Config()
    _config.ensure_dirs()
    _config.validate()
    return _config