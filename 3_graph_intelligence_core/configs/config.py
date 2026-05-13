"""Configuration loader for 3_graph_intelligence_core."""
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TigerGraphConfig:
    host: str = "https://localhost"
    graph: str = "ShadowGraph"
    restpp_port: int = 443
    username: str = "tigergraph"
    password: str = "tigergraph"
    use_ssl: bool = True
    secret: str = ""

    @property
    def restpp_url(self) -> str:
        return f"{self.host}:{self.restpp_port}"


@dataclass
class NIMConfig:
    api_key: str = ""
    base_url: str = "https://integrate.api.nvidia.com/v1"
    llm_model: str = "nvidia/llama-3.1-nemotron-70b-instruct"
    embedding_model: str = "nvidia/llama-3.1-nemotron-70b-instruct"


@dataclass
class OllamaConfig:
    base_url: str = "http://localhost:11434"
    llm_model: str = "llama3.2"
    embedding_model: str = "nomic-embed-text"


@dataclass
class DataConfig:
    source_dir: str = "outputs"
    profiles: list[str] = field(default_factory=lambda: ["small", "hackathon_default"])


@dataclass
class IngestionConfig:
    batch_size: int = 5000
    parallel_batches: int = 4
    upsert_mode: bool = True
    validate_schema: bool = True


@dataclass
class GraphRAGConfig:
    traversal_depth: int = 3
    top_k: int = 10
    max_context_tokens: int = 8000
    compression: str = "rule_based"
    provider: str = "nim"


@dataclass
class CacheConfig:
    enabled: bool = True
    traversal_ttl_seconds: int = 300
    neighborhood_ttl_seconds: int = 600
    subgraph_ttl_seconds: int = 900


@dataclass
class LoggingConfig:
    level: str = "INFO"
    trace_retrieval: bool = True


@dataclass
class Config:
    tigergraph: TigerGraphConfig = field(default_factory=TigerGraphConfig)
    nim: NIMConfig = field(default_factory=NIMConfig)
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    data: DataConfig = field(default_factory=DataConfig)
    ingestion: IngestionConfig = field(default_factory=IngestionConfig)
    graphrag: GraphRAGConfig = field(default_factory=GraphRAGConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


_config: Optional[Config] = None


def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from YAML file."""
    global _config

    if _config is not None:
        return _config

    if config_path is None:
        base = Path(__file__).parent.parent
        config_path = base / "configs" / "config.yaml"

    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r") as f:
        raw = yaml.safe_load(f)

    tg_cfg = TigerGraphConfig(**raw.get("tigergraph", {}))
    nim_cfg = NIMConfig(**raw.get("nim", {}))
    ollama_cfg = OllamaConfig(**raw.get("ollama", {}))
    data_cfg = DataConfig(**raw.get("data", {}))
    ingest_cfg = IngestionConfig(**raw.get("ingestion", {}))
    grag_cfg = GraphRAGConfig(**raw.get("graphrag", {}))
    cache_cfg = CacheConfig(**raw.get("cache", {}))
    log_cfg = LoggingConfig(**raw.get("logging", {}))

    _config = Config(
        tigergraph=tg_cfg,
        nim=nim_cfg,
        ollama=ollama_cfg,
        data=data_cfg,
        ingestion=ingest_cfg,
        graphrag=grag_cfg,
        cache=cache_cfg,
        logging=log_cfg,
    )
    return _config


def get_config() -> Config:
    """Get cached config."""
    if _config is None:
        return load_config()
    return _config