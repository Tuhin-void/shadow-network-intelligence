"""
3_graph_intelligence_core — Shadow Network Intelligence GraphRAG Engine.

Modules:
- configs/       Configuration management
- clients/      TigerGraph client (pyTigerGraph + RESTPP hybrid)
- validation/   Schema definition and validation
- ingestion/    Schema management and data loading
- gsql/         Installed GSQL queries
- retrievers/   Graph retrieval strategies (entity, neighborhood, path, community, temporal, hybrid)
- summarization/ Result compression (rule-based, evidence chain, LLM)
- graph_rag/    GraphRAG engine and graph retriever
- explainability/ Graph decision explanations
- metrics/     Retrieval metrics collection
- tracing/     Execution tracing
- caching/     Result caching
"""

try:
    # Works with -m (relative imports)
    from .configs.config import Config, load_config, get_config
    __all__ = ["Config", "load_config", "get_config"]
except ImportError:
    # Works with sys.path.insert(0, '3_graph_intelligence_core')
    from configs.config import Config, load_config, get_config
    __all__ = ["Config", "load_config", "get_config"]

__version__ = "1.0.0"
