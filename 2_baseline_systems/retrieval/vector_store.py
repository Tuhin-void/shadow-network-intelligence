"""
ChromaDB vector store with abstraction layer.
"""
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(
        self,
        provider: str = "chroma",
        persist_dir: Optional[Path] = None,
        collection_name: str = "shadow_network",
        dimension: int = 2048,
    ):
        self.provider = provider
        self.persist_dir = persist_dir or (Path(__file__).parent.parent / "outputs" / "chromadb")
        self.collection_name = collection_name
        self.dimension = dimension
        self._client = None
        self._collection = None
        self._initialized = False
        self._mock_docs: list[dict] = []
        self._mock_embeddings: list[list[float]] = []

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return

        if self.provider == "chroma":
            self._init_chroma()
        elif self.provider == "mock":
            self._initialized = True
            return
        else:
            logger.warning(f"Unknown provider {self.provider}, using ChromaDB default")
            self._init_chroma()

        self._initialized = True

    def _init_chroma(self) -> None:
        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError:
            logger.error("chromadb not installed")
            raise

        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(anonymized_telemetry=False),
        )
        try:
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"dimension": self.dimension},
            )
        except Exception as e:
            logger.warning(f"Collection error: {e}, recreating")
            try:
                self._client.delete_collection(self.collection_name)
            except Exception:
                pass
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"dimension": self.dimension},
            )
        logger.info(f"ChromaDB collection '{self.collection_name}' ready ({self._collection.count()} docs)")

    def index_documents(self, documents: list[dict], embedder=None, batch_size: int = 64) -> int:
        self._ensure_initialized()

        if not embedder:
            logger.warning("No embedder provided, cannot index documents")
            return 0

        if self.provider == "mock":
            for doc in documents:
                text = doc.get("text") or (doc.get("document", {}).get("text", "") if isinstance(doc.get("document"), dict) else "")
                doc_id = doc.get("id") or doc.get("document", {}).get("id", "") if isinstance(doc.get("document"), dict) else ""
                if text and doc_id:
                    emb = embedder.embed(text)
                    self._mock_docs.append({"id": doc_id, "text": text, "embedding": emb})
            logger.info(f"Mock indexed {len(self._mock_docs)} documents")
            return len(self._mock_docs)

        texts = []
        for doc in documents:
            text = doc.get("text") or (doc.get("document", {}).get("text", "") if isinstance(doc.get("document"), dict) else "")
            if not text:
                continue
            texts.append(text)

        if not texts:
            return 0

        logger.info(f"Embedding {len(texts)} texts")
        embeddings = embedder.embed_batch(texts, batch_size=batch_size)

        ids = []
        metas = []
        for doc in documents:
            doc_id = doc.get("id") or (doc.get("document", {}).get("id", "") if isinstance(doc.get("document"), dict) else "")
            if not doc_id:
                continue
            ids.append(doc_id)
            meta = {}
            if isinstance(doc, dict):
                if "metadata" in doc:
                    meta = doc["metadata"]
                elif isinstance(doc.get("document"), dict):
                    meta = doc["document"].get("metadata", {})
            metas.append(meta)

        existing = self._collection.count()
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i : i + batch_size]
            batch_embs = embeddings[i : i + batch_size]
            batch_metas = metas[i : i + batch_size]
            batch_texts = texts[i : i + batch_size]

            self._collection.upsert(
                ids=batch_ids,
                embeddings=batch_embs,
                metadatas=batch_metas,
                documents=batch_texts,
            )

        added = self._collection.count() - existing
        logger.info(f"Indexed {added} documents (total: {self._collection.count()})")
        return added

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        filter_metadata: Optional[dict] = None,
    ) -> list[dict]:
        self._ensure_initialized()

        if self.provider == "mock":
            import numpy as np
            if not self._mock_docs or not query_embedding:
                return []
            docs = self._mock_docs
            embs = np.array([d["embedding"] for d in docs])
            q = np.array(query_embedding)
            sims = np.dot(embs, q).tolist()
            sorted_idx = sorted(range(len(sims)), key=lambda i: sims[i], reverse=True)[:top_k]
            return [{
                "id": docs[i]["id"],
                "distance": 1.0 - sims[i],
                "score": sims[i],
                "document": {"text": docs[i]["text"], "metadata": {}},
            } for i in sorted_idx]

        try:
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter_metadata,
                include=["documents", "metadatas", "distances"],
            )

            output = []
            if results and "ids" in results and len(results["ids"]) > 0:
                for i in range(len(results["ids"][0])):
                    doc_id = results["ids"][0][i]
                    distance = results["distances"][0][i] if results.get("distances") else 0.0
                    doc_text = results["documents"][0][i] if results.get("documents") else ""
                    metadata = results["metadatas"][0][i] if results.get("metadatas") else {}

                    output.append({
                        "id": doc_id,
                        "distance": distance,
                        "score": 1.0 - distance,
                        "document": {"text": doc_text, "metadata": metadata},
                    })

            return output
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

    def search_hybrid(
        self,
        query: str,
        query_embedding: list[float],
        top_k: int = 10,
        alpha: float = 0.5,
    ) -> list[dict]:
        return self.search(query_embedding, top_k)

    def reset(self) -> None:
        if self.provider == "mock":
            self._mock_docs = []
            self._mock_embeddings = []
            logger.info(f"Mock collection '{self.collection_name}' reset")
            return
        self._ensure_initialized()
        try:
            self._client.delete_collection(self.collection_name)
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"dimension": self.dimension},
            )
            logger.info(f"Collection '{self.collection_name}' reset")
        except Exception as e:
            logger.error(f"Reset error: {e}")

    def get_stats(self) -> dict:
        self._ensure_initialized()
        if self.provider == "mock":
            return {
                "provider": "mock",
                "collection": self.collection_name,
                "total_documents": len(self._mock_docs),
                "dimension": self.dimension,
                "persist_dir": str(self.persist_dir),
            }
        return {
            "provider": self.provider,
            "collection": self.collection_name,
            "total_documents": self._collection.count(),
            "dimension": self.dimension,
            "persist_dir": str(self.persist_dir),
        }