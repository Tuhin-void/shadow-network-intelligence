"""
Pure LLM baseline: no retrieval. Just asks the LLM directly.

This is the lower-bound comparator for the benchmark — what does the model
know about fraud detection on its own, without any access to the actual
transaction data?
"""
from __future__ import annotations

import time
from typing import Any

from .ollama_client import OllamaClient, OllamaError


SYSTEM_PROMPT = (
    "You are a financial crime investigator. Answer fraud-detection questions "
    "concisely and explicitly state when you do not have data access. "
    "If the question references specific entity IDs (e.g., A-000001, C-000002), "
    "acknowledge that you cannot inspect them without retrieval. "
    "Respond in 3-5 sentences."
)


class PureLLMBaseline:
    name = "pure_llm"

    def __init__(self, client: OllamaClient | None = None):
        self.client = client or OllamaClient()

    def answer(self, question: str) -> dict[str, Any]:
        start = time.perf_counter()
        try:
            response = self.client.generate(question, system=SYSTEM_PROMPT)
            latency_ms = (time.perf_counter() - start) * 1000
            return {
                "approach": self.name,
                "question": question,
                "answer": response.text,
                "sources": [],
                "latency_ms": latency_ms,
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
                "sources": [],
                "latency_ms": latency_ms,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "model": self.client.model,
                "error": str(exc),
            }
