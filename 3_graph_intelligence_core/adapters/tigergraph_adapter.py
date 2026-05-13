"""Adapter that wires 3_graph_intelligence_core into 2_baseline_systems."""
import logging

logger = logging.getLogger(__name__)


class GraphRAGAdapter:
    """
    Bridges 2_baseline_systems GraphRAGPipeline with 3_graph_intelligence_core.

    2_baseline_systems/pipelines/graph_rag.py expects:
        result = graph_retriever.search(query=..., top_k=..., depth=...)

    Returns: {query, vector_results, subgraph, context}
        subgraph = {entities: [], edges: []}
        vector_results = []

    This adapter wraps GraphRAGEngine to match that interface.
    """

    def __init__(self, graph_client, config=None, embedder=None):
        from graph_rag.graphrag_engine import GraphRAGEngine

        if config is None:
            from configs.config import get_config
            config = get_config()

        self.engine = GraphRAGEngine(
            graph_client, config, compression="rule_based", embedder=embedder,
        )

    def search(self, query: str, top_k: int = 10, depth: int = 2) -> dict:
        """
        Match 2_baseline_systems GraphRAGPipeline interface.
        Calls GraphRAGEngine.query() and formats output.
        """
        result = self.engine.query(
            query=query,
            context=None,
            config={"strategy": "auto", "top_k": top_k, "depth": depth},
        )

        subgraph_entities = []
        for e in result.get("entities", []):
            subgraph_entities.append({
                "id": e.get("v_id", ""),
                "type": e.get("type", ""),
                "name": e.get("name", ""),
                "risk_score": e.get("risk_score"),
                "score": e.get("score"),
                "attributes": e.get("attributes", {}),
            })

        subgraph_edges = []
        for n in result.get("context", []):
            subgraph_edges.append({
                "from": result["metadata"].get("entity_id", ""),
                "to": n.get("v_id", ""),
                "type": n.get("edge", ""),
            })

        vector_results = []
        for e in result.get("entities", [])[:top_k]:
            vector_results.append({
                "id": e.get("v_id", ""),
                "document": {
                    "text": f"{e.get('type', 'Entity')}: {e.get('name', e.get('v_id', ''))}",
                    "entity_type": e.get("type", ""),
                    "risk_score": e.get("risk_score", 0),
                },
            })

        return {
            "query": query,
            "vector_results": vector_results,
            "subgraph": {
                "entities": subgraph_entities,
                "edges": subgraph_edges,
            },
            "context": result.get("answer", ""),
            "engine_result": result,
        }


def create_adapter(graph_client, config=None, embedder=None) -> GraphRAGAdapter:
    """Factory function for GraphRAGAdapter."""
    return GraphRAGAdapter(graph_client, config, embedder=embedder)


def create_pipeline(
    llm_client,
    token_tracker,
    data_loader,
    graph_client,
    config=None,
    **kwargs,
):
    """
    Create a GraphRAGPipeline from 2_baseline_systems wired to 3_graph_intelligence_core.

    Usage in 2_baseline_systems:
        from 3_graph_intelligence_core.adapters.tigergraph_adapter import create_pipeline
        pipeline = create_pipeline(llm, token_tracker, data_loader, graph_client)
        result = pipeline.answer("Show high risk accounts")
    """
    import importlib.util
    spec = importlib.util.find_module("pipelines.graph_rag", "2_baseline_systems")
    if spec is not None:
        graph_rag_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(graph_rag_module)
        GraphRAGPipeline = graph_rag_module.GraphRAGPipeline
    else:
        raise ImportError("2_baseline_systems.pipelines.graph_rag not found")

    adapter = create_adapter(graph_client, config)
    pipeline = GraphRAGPipeline(
        llm_client=llm_client,
        token_tracker=token_tracker,
        data_loader=data_loader,
        graph_retriever=adapter,
        **kwargs,
    )
    return pipeline