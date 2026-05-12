"""
ChromaDB persistent vector store wrapper.

Owns a single collection. `index_documents` is idempotent — re-indexing the
same IDs upserts. `search` returns matches with distance and metadata.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..config import CHROMA_COLLECTION, CHROMA_DIR
from .embedder import Embedder

if TYPE_CHECKING:
    from chromadb import Collection


def _flatten_metadata(meta: dict[str, Any]) -> dict[str, str | int | float | bool]:
    """Chroma only accepts scalar metadata values; coerce everything else to str."""
    out: dict[str, str | int | float | bool] = {}
    for k, v in meta.items():
        if v is None:
            continue
        if isinstance(v, (str, int, float, bool)):
            out[k] = v
        else:
            out[k] = str(v)
    return out


class ChromaStore:
    def __init__(
        self,
        persist_dir: Path = CHROMA_DIR,
        collection_name: str = CHROMA_COLLECTION,
        embedder: Embedder | None = None,
    ):
        import chromadb

        persist_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(persist_dir))
        self.collection_name = collection_name
        self.embedder = embedder or Embedder()
        self._collection: "Collection | None" = None

    @property
    def collection(self) -> "Collection":
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def count(self) -> int:
        return self.collection.count()

    def index_documents(self, documents: list[dict[str, Any]], batch_size: int = 64) -> int:
        if not documents:
            return 0

        ids = [d["id"] for d in documents]
        texts = [d["text"] for d in documents]
        metadatas = [_flatten_metadata(d.get("metadata", {})) for d in documents]
        embeddings = self.embedder.embed_batch(texts)

        for i in range(0, len(ids), batch_size):
            self.collection.upsert(
                ids=ids[i : i + batch_size],
                documents=texts[i : i + batch_size],
                metadatas=metadatas[i : i + batch_size],
                embeddings=embeddings[i : i + batch_size],
            )
        return len(ids)

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        query_emb = self.embedder.embed(query)
        result = self.collection.query(
            query_embeddings=[query_emb],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        hits: list[dict[str, Any]] = []
        ids = (result.get("ids") or [[]])[0]
        docs = (result.get("documents") or [[]])[0]
        metas = (result.get("metadatas") or [[]])[0]
        dists = (result.get("distances") or [[]])[0]

        for i, doc_id in enumerate(ids):
            hits.append({
                "id": doc_id,
                "text": docs[i] if i < len(docs) else "",
                "metadata": metas[i] if i < len(metas) else {},
                "distance": dists[i] if i < len(dists) else None,
            })
        return hits

    def reset(self) -> None:
        try:
            self.client.delete_collection(self.collection_name)
        except Exception:
            pass
        self._collection = None
