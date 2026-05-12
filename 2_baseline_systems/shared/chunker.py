"""
Chunking wrapper - exposes shared/RecursiveChunker with 1_data_engine parity.
"""
from typing import List
from shared.chunkers.recursive import RecursiveChunker as _RecursiveChunker


_STRATEGIES = {}


def get_chunker(strategy: str = "recursive", chunk_size: int = 500, chunk_overlap: int = 50):
    key = (strategy, chunk_size, chunk_overlap)
    if key not in _STRATEGIES:
        if strategy == "recursive":
            _STRATEGIES[key] = _RecursiveChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        elif strategy == "semantic":
            _STRATEGIES[key] = _SemanticChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        elif strategy == "sentence":
            _STRATEGIES[key] = _SentenceChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        elif strategy == "graph_aware":
            _STRATEGIES[key] = _GraphAwareChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        else:
            _STRATEGIES[key] = _RecursiveChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return _STRATEGIES[key]


def chunk_text(text: str, strategy: str = "recursive", chunk_size: int = 500, chunk_overlap: int = 50) -> List[str]:
    chunker = get_chunker(strategy, chunk_size, chunk_overlap)
    return chunker.chunk(text)


class _SemanticChunker:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, text: str) -> List[str]:
        sentences = text.replace("! ", ".| ").replace("? ", ".| ").replace(". ", ".| ").split("| ")
        chunks, current = [], ""
        for sent in sentences:
            if len(current) + len(sent) <= self.chunk_size:
                current += (" " if current else "") + sent.strip()
            else:
                if current:
                    chunks.append(current.strip())
                if self.chunk_overlap > 0 and chunks:
                    overlap_text = chunks[-1][-self.chunk_overlap:]
                    current = overlap_text + " " + sent.strip()
                else:
                    current = sent.strip()
        if current:
            chunks.append(current.strip())
        return [c for c in chunks if c]


class _SentenceChunker:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, text: str) -> List[str]:
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks, current = [], ""
        for sent in sentences:
            if len(current) + len(sent) <= self.chunk_size:
                current += (" " if current else "") + sent
            else:
                if current:
                    chunks.append(current.strip())
                current = sent
        if current:
            chunks.append(current.strip())
        return [c for c in chunks if c]


class _GraphAwareChunker:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._base = _RecursiveChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    def chunk(self, text: str) -> List[str]:
        chunks = self._base.chunk(text)
        return chunks