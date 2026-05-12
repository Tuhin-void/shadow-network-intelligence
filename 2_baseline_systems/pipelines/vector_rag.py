"""
Pipeline 2: Vector RAG - Embed + ChromaDB search + LLM.
"""
import time
import logging
from typing import Optional, Any
from .base import BasePipeline
from ..shared.schemas import PipelineResult, RetrievalTrace
from ..shared.embedder import Embedder

logger = logging.getLogger(__name__)


class VectorRAGPipeline(BasePipeline):
    """
    Vector RAG pipeline - embed + semantic search + LLM.

    Support:
    - ChromaDB vector store
    - Top-k retrieval
    - Chunk size / overlap tuning
    - Metadata filtering
    - Reranking (optional)

    Track:
    - retrieved chunks with provenance
    - retrieval scores / distances
    - retrieval latency
    - embedding cost
    - token usage
    """
    approach = "vector_rag"

    def __init__(
        self,
        llm_client,
        token_tracker,
        data_loader,
        vector_store,
        embedder: Embedder,
        top_k: int = 10,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ):
        super().__init__(llm_client, token_tracker, data_loader)
        self.vector_store = vector_store
        self.embedder = embedder
        self.top_k = top_k
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._indexed = False

    def _ensure_indexed(self) -> None:
        if self._indexed:
            return

        from ..shared.document_builder import DocumentBuilder

        try:
            dataset = self.data_loader.load()
            builder = DocumentBuilder(dataset, self.chunk_size, self.chunk_overlap)
            docs = builder.build_all()

            logger.info(f"VectorRAG: indexing {len(docs)} documents")
            self.vector_store.index_documents([d.to_dict() for d in docs], self.embedder)
            self._indexed = True
            logger.info("VectorRAG: indexing complete")
        except Exception as e:
            logger.error(f"Failed to index documents: {e}")
            self._indexed = True

    def answer(self, question: str, context: Optional[Any] = None) -> PipelineResult:
        try:
            self._ensure_indexed()

            retrieval_start = time.time()
            query_embedding = self.embedder.embed(question)
            retrieval_results = self.vector_store.search(query_embedding, top_k=self.top_k)
            retrieval_ms = (time.time() - retrieval_start) * 1000

            sources = []
            for r in retrieval_results:
                doc = r.get("document", {})
                sources.append({
                    "id": r.get("id", doc.get("id", "unknown")),
                    "doc_type": doc.get("metadata", {}).get("doc_type", "unknown"),
                    "entity_id": doc.get("metadata", {}).get("entity_id"),
                    "distance": r.get("distance", r.get("score", 0)),
                    "text": doc.get("text", "")[:200],
                })

            retrieval_trace = RetrievalTrace(
                retrieved_chunks=[
                    {"id": s["id"], "distance": s["distance"], "doc_type": s["doc_type"]}
                    for s in sources
                ],
                retrieval_depth=1,
                total_retrieved=len(sources),
                cache_hits=0,
                retrieval_strategy="vector_search",
                traversal_paths=[],
                visited_nodes=[],
                traversed_edges=0,
            )

            retrieved_context = self._format_context([
                {"id": s["id"], "text": s["text"]}
                for s in sources if s.get("text")
            ])

            system, user_prompt = self._build_prompt(question, retrieved_context)
            response = self.llm.generate(
                prompt=user_prompt,
                system=system,
                temperature=0.0,
                max_tokens=2048,
            )

            return self._parse_response(response, {
                "question": question,
                "sources": sources,
                "retrieval_ms": retrieval_ms,
                "system_prompt": system,
                "user_prompt": user_prompt,
                "retrieval_trace": retrieval_trace,
            })

        except Exception as e:
            logger.error(f"VectorRAG pipeline error: {e}")
            return self._handle_error(f"VectorRAG error: {str(e)}", question)

    def search_raw(self, question: str, top_k: Optional[int] = None) -> list[dict]:
        self._ensure_indexed()
        k = top_k or self.top_k
        query_embedding = self.embedder.embed(question)
        return self.vector_store.search(query_embedding, top_k=k)