"""
Pipeline 1: Pure LLM - Zero retrieval baseline.
"""
import time
from typing import Optional, Any
from .base import BasePipeline
from ..shared.schemas import PipelineResult, RetrievalTrace


class PureLLMPipeline(BasePipeline):
    """
    Pure LLM baseline - no retrieval whatsoever.

    Purpose:
    - Establish worst-case baseline
    - Demonstrate token inefficiency
    - Demonstrate hallucination risk
    - Demonstrate poor contextual grounding

    Track:
    - prompt tokens, completion tokens, total tokens
    - latency, inference cost
    - hallucination rate (via evaluation)
    """
    approach = "pure_llm"

    def __init__(
        self,
        llm_client,
        token_tracker,
        data_loader,
        inject_graph_summary: bool = False,
    ):
        super().__init__(llm_client, token_tracker, data_loader)
        self.inject_graph_summary = inject_graph_summary

    def answer(self, question: str, context: Optional[Any] = None) -> PipelineResult:
        try:
            graph_summary = None
            if self.inject_graph_summary:
                try:
                    dataset = self.data_loader.load()
                    graph_summary = dataset.to_graph_summary()
                except Exception:
                    pass

            system, user_prompt = self._build_prompt(question, context, graph_summary)
            response = self.llm.generate(
                prompt=user_prompt,
                system=system,
                temperature=0.0,
                max_tokens=2048,
            )

            return self._parse_response(response, {
                "question": question,
                "sources": [],
                "retrieval_ms": 0.0,
                "system_prompt": system,
                "user_prompt": user_prompt,
                "retrieval_trace": RetrievalTrace(
                    retrieved_chunks=[],
                    retrieval_depth=0,
                    total_retrieved=0,
                    cache_hits=0,
                    retrieval_strategy="none",
                    traversal_paths=[],
                    visited_nodes=[],
                    traversed_edges=0,
                ),
            })

        except Exception as e:
            return self._handle_error(f"Pipeline error: {str(e)}", question)