"""Mock embedder for testing"""
import numpy as np
from typing import List

class MockEmbedder:
    """Mock embedding for testing without model download."""
    
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
    
    def embed(self, text: str) -> List[float]:
        """Generate mock embedding."""
        seed = hash(text) % (2**32)
        np.random.seed(seed)
        return np.random.randn(self.dimension).tolist()
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate batch embeddings."""
        return [self.embed(t) for t in texts]
