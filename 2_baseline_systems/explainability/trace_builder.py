"""
Trace builder - structured reasoning traces per pipeline.
"""
from ..shared.schemas import PipelineResult, BenchmarkQuery, RetrievalTrace, TraversalPath


class TraceBuilder:
    def build_trace(self, result: PipelineResult, query: BenchmarkQuery) -> dict:
        trace = {
            "approach": result.approach,
            "query_id": query.id,
            "question": query.question,
            "answer_preview": (result.answer or "")[:200],
            "latency_ms": result.latency_ms,
            "retrieval_ms": result.retrieval_ms,
            "tokens": {
                "prompt": result.prompt_tokens,
                "completion": result.completion_tokens,
                "total": result.total_tokens,
            },
            "cost": result.cost_estimate,
            "error": result.error,
        }

        if result.approach == "pure_llm":
            trace["retrieval"] = {
                "strategy": "none",
                "chunks_retrieved": 0,
                "nodes_visited": 0,
                "edges_traversed": 0,
            }
            trace["explanation"] = self._explain_pure_llm(result, query)

        elif result.approach == "vector_rag":
            rt = result.retrieval_trace
            chunks = rt.retrieved_chunks if rt else []
            trace["retrieval"] = {
                "strategy": "vector_similarity",
                "chunks_retrieved": len(chunks),
                "top_sources": [
                    {"id": c.get("id"), "distance": c.get("distance", 0), "doc_type": c.get("doc_type")}
                    for c in chunks[:5]
                ],
                "avg_distance": sum(c.get("distance", 0) for c in chunks) / len(chunks) if chunks else 0,
            }
            trace["explanation"] = self._explain_vector_rag(result, query)

        elif result.approach == "graphrag":
            rt = result.retrieval_trace
            trace["retrieval"] = {
                "strategy": "graph_traversal",
                "nodes_visited": len(rt.visited_nodes) if rt else 0,
                "edges_traversed": rt.traversed_edges if rt else 0,
                "depth": rt.retrieval_depth if rt else 0,
                "traversal_paths": [
                    tp.to_dict() if hasattr(tp, "to_dict") else tp
                    for tp in (result.traversal_paths or [])
                ][:5],
            }
            trace["explanation"] = self._explain_graphrag(result, query)

        return trace

    def _explain_pure_llm(self, result: PipelineResult, query: BenchmarkQuery) -> str:
        return (
            f"Pure LLM answered using only internal knowledge. "
            f"Prompt tokens: {result.prompt_tokens}, completion tokens: {result.completion_tokens}. "
            f"No retrieval was performed, so the answer may lack specific entity details "
            f"from the dataset. Hallucination risk is highest with this approach."
        )

    def _explain_vector_rag(self, result: PipelineResult, query: BenchmarkQuery) -> str:
        rt = result.retrieval_trace
        chunks = rt.retrieved_chunks if rt else []
        n = len(chunks)
        if n == 0:
            return "No relevant chunks retrieved. Vector search failed to find matching context."
        avg_dist = sum(c.get("distance", 0) for c in chunks) / n
        doc_types = {}
        for c in chunks:
            dt = c.get("doc_type", "unknown")
            doc_types[dt] = doc_types.get(dt, 0) + 1
        return (
            f"Vector RAG retrieved {n} chunks (avg distance: {avg_dist:.3f}). "
            f"Document types: {doc_types}. "
            f"Top retrieval: {chunks[0].get('id', 'N/A')}. "
            f"Tokens used: {result.total_tokens}. "
            f"Vector search captures semantic similarity but misses graph topology."
        )

    def _explain_graphrag(self, result: PipelineResult, query: BenchmarkQuery) -> str:
        rt = result.retrieval_trace
        nodes = len(rt.visited_nodes) if rt else 0
        edges = rt.traversed_edges if rt else 0
        depth = rt.retrieval_depth if rt else 0
        paths = result.traversal_paths or []
        if not paths:
            return f"GraphRAG visited {nodes} nodes, traversed {edges} edges at depth {depth}. No explicit traversal paths found."
        return (
            f"GraphRAG traversed {nodes} nodes and {edges} edges at depth {depth}. "
            f"Discovered {len(paths)} traversal paths. "
            f"Key path: {paths[0].path if paths else 'N/A'} "
            f"({paths[0].path_type if paths else 'N/A'}, {paths[0].hops if paths else 0} hops). "
            f"Tokens: {result.total_tokens}. "
            f"Graph traversal captures entity relationships and topology that vector search misses."
        )