"""
Unified embedder: Ollama / OpenAI / Mock.
"""
import logging
import hashlib
from typing import Optional

logger = logging.getLogger(__name__)


class Embedder:
    def __init__(
        self,
        provider: str = "ollama",
        model: str = "nomic-embed-text",
        base_url: str = "http://localhost:11434",
        api_key: str = "",
        dimension: int = 768,
    ):
        self.provider = provider
        self.model = model
        self.base_url = base_url
        self.api_key = api_key
        self._dimension = dimension
        self._cache = {}

    @property
    def dimension(self) -> int:
        if self.model.startswith("text-embedding-3-large"):
            return 3072
        if self.model.startswith("text-embedding-3"):
            return 1536
        if "nomic" in self.model:
            return 768
        return self._dimension

    def embed(self, text: str) -> list[float]:
        cache_key = hashlib.md5(text.encode()).hexdigest()
        if cache_key in self._cache:
            return self._cache[cache_key]

        if self.provider == "ollama":
            result = self._ollama_embed(text)
        elif self.provider == "openai":
            result = self._openai_embed(text)
        elif self.provider == "mock":
            result = self._mock_embed(text)
        else:
            result = self._mock_embed(text)

        if result:
            self._cache[cache_key] = result
        return result

    def embed_batch(self, texts: list[str], batch_size: int = 64) -> list[list[float]]:
        results = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            if self.provider == "ollama":
                batch_results = self._ollama_embed_batch(batch)
            elif self.provider == "openai":
                batch_results = self._openai_embed_batch(batch)
            elif self.provider == "mock":
                batch_results = [self._mock_embed(t) for t in batch]
            else:
                batch_results = [self._mock_embed(t) for t in batch]
            results.extend(batch_results)
        return results

    def _ollama_embed(self, text: str) -> list[float]:
        try:
            import requests
            resp = requests.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("embedding", [])
        except Exception as e:
            logger.warning(f"Ollama embed failed: {e}, using mock")
            return self._mock_embed(text)

    def _ollama_embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self._ollama_embed(t) for t in texts]

    def _openai_embed(self, text: str) -> list[float]:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            resp = client.embeddings.create(model=self.model, input=text)
            return resp.data[0].embedding
        except Exception as e:
            logger.warning(f"OpenAI embed failed: {e}, using mock")
            return self._mock_embed(text)

    def _openai_embed_batch(self, texts: list[str]) -> list[list[float]]:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            resp = client.embeddings.create(model=self.model, input=texts)
            return [item.embedding for item in resp.data]
        except Exception as e:
            logger.warning(f"OpenAI batch embed failed: {e}, using mock")
            return [self._mock_embed(t) for t in texts]

    def _mock_embed(self, text: str) -> list[float]:
        import random
        random.seed(sum(ord(c) for c in text))
        dim = self.dimension
        vec = [random.uniform(-1, 1) for _ in range(dim)]
        norm = sum(x * x for x in vec) ** 0.5
        if norm > 0:
            vec = [x / norm for x in vec]
        random.seed(None)
        return vec

    def clear_cache(self) -> None:
        self._cache.clear()