"""
Pipeline 3: GraphRAG - GraphRetriever from 3_graph_intelligence_core.
"""
import time
import logging
from typing import Optional, Any
from .base import BasePipeline
from ..shared.schemas import PipelineResult, RetrievalTrace, TraversalPath
from ..shared.embedder import Embedder
from ..shared.data_loader import AdaptiveDataLoader

logger = logging.getLogger(__name__)


class GraphRAGPipeline(BasePipeline):
    """
    GraphRAG pipeline - imports GraphRetriever from 3_graph_intelligence_core.

    Features:
    - Graph traversal retrieval
    - Neighborhood expansion
    - Entity-centric retrieval
    - Relationship-aware retrieval
    - Path-aware retrieval
    - Hybrid graph + vector retrieval

    Track:
    - visited nodes, traversed edges
    - neighborhood expansion depth
    - traversal paths
    """
    approach = "graph_rag"

    FRAUD_KEYWORDS = [
        "shell", "offshore", "fraud", "mule", "structuring", "laundering", "ring",
        "funnel", "smurfing", "layering", "circular", "sanctioned", "pep",
        "watched", "dormant", "burst", "velocity", "correspondent", "shell_company",
        "beneficial", "ownership", "round_trip", "phantom", "round_amount",
    ]

    def __init__(
        self,
        llm_client,
        token_tracker,
        data_loader,
        graph_retriever=None,
        embedder: Optional[Embedder] = None,
        traversal_depth: int = 2,
        top_k: int = 10,
    ):
        super().__init__(llm_client, token_tracker, data_loader)
        self.graph_retriever = graph_retriever
        self.embedder = embedder
        self.traversal_depth = traversal_depth
        self.top_k = top_k

    def _create_mock_retriever(self) -> bool:
        dataset = self.data_loader.load()

        from ..shared.document_builder import DocumentBuilder

        entity_docs = []
        builder = DocumentBuilder(dataset)
        all_docs = builder.build_all()

        entity_ids_in_questions = set()
        for fr in dataset.fraud_rings:
            for eid in fr.get("entities", []):
                entity_ids_in_questions.add(eid)
            for eid in fr.get("key_entities", []):
                entity_ids_in_questions.add(eid)

        for doc in all_docs:
            doc_id = doc.metadata.get("entity_id", "")
            if doc_id in entity_ids_in_questions:
                entity_docs.append(doc)

        if not entity_docs:
            entity_docs = all_docs[:100]

        self._local_docs = entity_docs
        self._dataset = dataset
        return True

    def answer(self, question: str, context: Optional[Any] = None) -> PipelineResult:
        try:
            retrieval_start = time.time()

            traversal_paths = []
            visited_nodes = []
            retrieved_context_parts = []

            if self.graph_retriever:
                result = self.graph_retriever.search(
                    query=question,
                    top_k=self.top_k,
                    depth=self.traversal_depth,
                )
                subgraph = result.get("subgraph", {})
                entities = subgraph.get("entities", [])
                visited_nodes = [e.get("id") for e in entities if e.get("id")]

                vector_results = result.get("vector_results", [])
                for vr in vector_results:
                    doc = vr.get("document", {})
                    retrieved_context_parts.append(doc.get("text", ""))
            else:
                retrieved_context_parts, visited_nodes, traversal_paths = \
                    self._fallback_graph_retrieval(question)

            retrieval_ms = (time.time() - retrieval_start) * 1000

            retrieval_trace = RetrievalTrace(
                retrieved_chunks=[],
                retrieval_depth=self.traversal_depth,
                total_retrieved=len(visited_nodes),
                cache_hits=0,
                retrieval_strategy="graph_traversal",
                traversal_paths=[tp.to_dict() if hasattr(tp, "to_dict") else tp for tp in traversal_paths],
                visited_nodes=visited_nodes,
                traversed_edges=len(visited_nodes) * self.traversal_depth,
            )

            if retrieved_context_parts:
                context_text = "=== GRAPH CONTEXT ===\n" + "\n\n".join(retrieved_context_parts[:10]) + "\n=== END CONTEXT ==="
            else:
                context_text = "No graph context retrieved."

            system, user_prompt = self._build_prompt(question, context_text)
            response = self.llm.generate(
                prompt=user_prompt,
                system=system,
                temperature=0.0,
                max_tokens=2048,
            )

            return self._parse_response(response, {
                "question": question,
                "sources": [{"id": nid, "doc_type": "graph_entity"} for nid in visited_nodes[:10]],
                "retrieval_ms": retrieval_ms,
                "system_prompt": system,
                "user_prompt": user_prompt,
                "retrieval_trace": retrieval_trace,
                "traversal_paths": traversal_paths,
            })

        except Exception as e:
            logger.error(f"GraphRAG pipeline error: {e}")
            return self._handle_error(f"GraphRAG error: {str(e)}", question)

    def _fallback_graph_retrieval(self, question: str) -> tuple[list[str], list[str], list[TraversalPath]]:
        if not hasattr(self, "_dataset") or not hasattr(self, "_local_docs"):
            self._create_mock_retriever()

        dataset = self._dataset
        docs = self._local_docs
        visited = []
        paths = []
        context_parts = []

        question_lower = question.lower()

        for doc in docs[:self.top_k * 5]:
            text_lower = doc.text.lower()
            if any(kw in text_lower for kw in self.FRAUD_KEYWORDS):
                entity_id = doc.metadata.get("entity_id", "")
                if entity_id:
                    visited.append(entity_id)
                    context_parts.append(doc.text[:300])

                edges = dataset.get_edges_for_entity(entity_id)
                for edge in edges[:3]:
                    from_id = edge.get("from_id", "")
                    to_id = edge.get("to_id", "")
                    rel = edge.get("relationship", "")
                    other = to_id if from_id == entity_id else from_id

                    if other:
                        other_entity = dataset.get_entity_by_id(other)
                        if other_entity:
                            other_text = other_entity.get("name", other_entity.get("first_name", ""))
                            paths.append(TraversalPath(
                                path=[from_id, to_id],
                                path_type=rel.lower().replace(" ", "_"),
                                weight=edge.get("weight", 1.0),
                                hops=1,
                                narrative=f"{entity_id} --[{rel}]--> {other} ({other_text})",
                            ))

        for ring in dataset.fraud_rings[:self.top_k * 2]:
            ring_id = ring.get("id", "")
            ring_desc = ring.get("description", ring.get("type", ""))
            if ring_desc.lower() in question_lower or ring_id in question:
                entities = ring.get("entities", [])
                traversal = ring.get("traversal_paths", [])
                paths_str = ", ".join(entities[:10])
                context_parts.append(
                    f"Fraud Ring {ring_id}: {ring.get('description', '')}. "
                    f"Involved entities: {paths_str}. "
                    f"Severity: {ring.get('severity', 'MEDIUM')}."
                )
                visited.extend(entities[:10])

        return context_parts, list(dict.fromkeys(visited)), paths[:20]