"""Recursive text chunker"""
from typing import List
import re

class RecursiveChunker:
    """Splits text into chunks using recursive character splitting."""
    
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separators: List[str] = None
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", " "]
    
    def chunk(self, text: str) -> List[str]:
        """Split text into chunks."""
        if not text:
            return []
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]
            
            if end < len(text):
                for sep in self.separators:
                    last_sep = chunk.rfind(sep)
                    if last_sep != -1:
                        chunk = chunk[:last_sep + len(sep)]
                        break
            
            if chunk.strip():
                chunks.append(chunk.strip())
            
            start = end - self.chunk_overlap
            if start <= 0:
                start = end
        
        return chunks
