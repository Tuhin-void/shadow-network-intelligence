"""
Thin wrapper around sentence-transformers for embeddings.

Lazy-loads the model on first call so that importing this module is cheap.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..config import EMBED_DEVICE, EMBED_MODEL

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


class Embedder:
    def __init__(self, model_name: str = EMBED_MODEL, device: str = EMBED_DEVICE):
        self.model_name = model_name
        self.device = device
        self._model: "SentenceTransformer | None" = None

    def _load(self) -> "SentenceTransformer":
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name, device=self.device)
        return self._model

    def embed(self, text: str) -> list[float]:
        return self._load().encode(text, convert_to_numpy=False).tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        vectors = self._load().encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return [v.tolist() for v in vectors]

    @property
    def dimension(self) -> int:
        return self._load().get_sentence_embedding_dimension()
