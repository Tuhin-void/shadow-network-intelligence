"""
Vector RAG baseline: embed query → retrieve top-k from ChromaDB →
inject context into the LLM prompt → generate.
"""
from __future__ import annotations

import time
from typing import Any

from ..config import TOP_K
from ..pure_llm.ollama_client import OllamaClient, OllamaError
from .chroma_store import ChromaStore


SYSTEM_PROMPT = (
    "You are a financial crime investigator. Answer the question using ONLY "
    "the provided context. If the context is insufficient, say so explicitly "
    "and describe what additional data you would need. Cite source IDs in your "
    "answer when relevant. Respond in 3-5 sentences."
)

PROMPT_TEMPLATE = """CONTEXT:
{context}

QUESTION:
{question}

ANSWER:"""


def _format_context(hits: list[dict[str, Any]]) -> str:
    if not hits:
        return "(no relevant context retrieved)"
    blocks = []
    for hit in hits:
        blocks.append(f"[{hit['id']}] {hit['text']}")
    return "\n\n".join(blocks)


class VectorRAGBaseline:
    name = "vector_rag"

    def __init__(
        self,
        store: ChromaStore | None = None,
        llm: OllamaClient | None = None,
        top_k: int = TOP_K,
    ):
        self.store = store or ChromaStore()
        self.llm = llm or OllamaClient()
        self.top_k = top_k

    def answer(self, question: str) -> dict[str, Any]:
        start = time.perf_counter()

        retrieval_start = time.perf_counter()
        hits = self.store.search(question, top_k=self.top_k)
        retrieval_ms = (time.perf_counter() - retrieval_start) * 1000

        context = _format_context(hits)
        prompt = PROMPT_TEMPLATE.format(context=context, question=question)

        try:
            response = self.llm.generate(prompt, system=SYSTEM_PROMPT)
            latency_ms = (time.perf_counter() - start) * 1000
            return {
                "approach": self.name,
                "question": question,
                "answer": response.text,
                "sources": [
                    {"id": h["id"], "doc_type": h["metadata"].get("doc_type"), "distance": h["distance"]}
                    for h in hits
                ],
                "latency_ms": latency_ms,
                "retrieval_ms": retrieval_ms,
                "prompt_tokens": response.prompt_tokens,
                "completion_tokens": response.completion_tokens,
                "model": response.model,
                "error": None,
            }
        except OllamaError as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            return {
                "approach": self.name,
                "question": question,
                "answer": None,
                "sources": [{"id": h["id"], "doc_type": h["metadata"].get("doc_type"), "distance": h["distance"]} for h in hits],
                "latency_ms": latency_ms,
                "retrieval_ms": retrieval_ms,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "model": self.llm.model,
                "error": str(exc),
            }
